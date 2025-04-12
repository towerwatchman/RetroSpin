import xml.etree.ElementTree as ET
import sqlite3
import re
from fuzzywuzzy import fuzz
import tkinter as tk
from tkinter import ttk, messagebox
import requests
import os
from datetime import datetime
import zipfile
import glob
import tempfile

# URL for PSX Redump DAT file
REDUMP_URL = "http://redump.org/datfile/psx/"
DB_PATH = "games.db"  # Local, move to /media/fat/retrospin/games.db on MiSTer
AUTO_MATCH_THRESHOLD = 85  # Auto-update if >= 85% similarity
PROMPT_MATCH_THRESHOLD = 50  # Prompt user if >= 50% but < 85%

# Region mappings
REGION_MAP = {
    "(USA)": "NTSC-U",
    "(Europe)": "PAL",
    "(Japan)": "NTSC-J",
    "(Asia)": "NTSC-J",
    "(Australia)": "PAL",
    "(Brazil)": "NTSC-U",
    "(Canada)": "NTSC-U",
    "(China)": "NTSC-J",
    "(France)": "PAL",
    "(Germany)": "PAL",
    "(Italy)": "PAL",
    "(Korea)": "NTSC-J",
    "(Netherlands)": "PAL",
    "(Spain)": "PAL",
    "(Sweden)": "PAL",
    "(Taiwan)": "NTSC-J",
    "(UK)": "PAL"
}

# Language mappings
LANGUAGE_MAP = {
    "En": "English",
    "Ja": "Japanese",
    "Fr": "French",
    "De": "German",
    "Es": "Spanish",
    "It": "Italian",
    "Nl": "Dutch",
    "Pt": "Portuguese",
    "Sv": "Swedish",
    "No": "Norwegian",
    "Da": "Danish",
    "Fi": "Finnish",
    "Zh": "Chinese",
    "Ko": "Korean",
    "Pl": "Polish"
}

def download_redump_dat():
    """Download the latest PSX Redump DAT zip file, extract the .dat, and return its path."""
    try:
        print(f"Fetching Redump DAT file from {REDUMP_URL}...")
        response = requests.get(REDUMP_URL, timeout=10)
        response.raise_for_status()
        
        # Extract filename from Content-Disposition or use default
        filename = None
        if 'Content-Disposition' in response.headers:
            disposition = response.headers['Content-Disposition']
            match = re.search(r'filename="(.+)"', disposition)
            if match:
                filename = match.group(1)
        if not filename:
            filename = f"psx_redump_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.zip"
        
        # Save the zip file locally
        zip_path = filename
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        print(f"Saved Redump zip file to {zip_path}")
        
        # Extract the .dat file
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                print(f"Extracted zip file to temporary directory: {temp_dir}")
            
            # Find the .dat file
            dat_files = glob.glob(os.path.join(temp_dir, "*.dat"))
            if not dat_files:
                raise ValueError("No .dat file found in the downloaded zip")
            if len(dat_files) > 1:
                print(f"Warning: Multiple .dat files found, using the first: {dat_files[0]}")
            dat_path = dat_files[0]
            
            # Read the .dat content
            with open(dat_path, 'rb') as f:
                dat_content = f.read()
            
            # Save .dat content to a local file for parsing
            dat_filename = os.path.basename(dat_path)
            local_dat_path = dat_filename
            with open(local_dat_path, 'wb') as f:
                f.write(dat_content)
            print(f"Saved extracted DAT file to {local_dat_path}")
            
            return local_dat_path
    
    except requests.RequestException as e:
        print(f"Error downloading Redump DAT file: {e}")
        return None
    except zipfile.BadZipFile:
        print(f"Error: Downloaded file is not a valid zip")
        return None
    except Exception as e:
        print(f"Error extracting DAT file: {e}")
        return None

def connect_to_database():
    """Connect to games.db and return connection and cursor."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    return conn, cursor

def ensure_table_schema(cursor):
    """Ensure games and missing_games tables exist with correct schema."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT,
            title TEXT,
            region TEXT,
            system TEXT,
            language TEXT,
            updated_from_redump TEXT,
            PRIMARY KEY (game_id, system)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS missing_games (
            title TEXT,
            region TEXT,
            language TEXT,
            redump_full_title TEXT,
            timestamp TEXT
        )
    ''')

def extract_region_and_language(redump_title):
    """Extract region, language, and clean title from Redump title."""
    region = "Unknown"
    language = "Unknown"
    
    for redump_region, db_region in REGION_MAP.items():
        if redump_region in redump_title:
            region = db_region
            break
    
    lang_match = re.search(r'\((En?,(?:[A-Z][a-z]?,)*[A-Z][a-z]?)\)', redump_title)
    if lang_match:
        redump_langs = lang_match.group(1).split(",")
        db_langs = [LANGUAGE_MAP.get(lang.strip(), lang.strip()) for lang in redump_langs]
        language = ", ".join(db_langs)
    elif "(USA)" in redump_title or "(Canada)" in redump_title:
        language = "English"
    
    title = re.sub(r'\s*\((?!Disc\s*\d+\b)[^)]+\)', '', redump_title).strip()
    return title, region, language, redump_title

def parse_redump_xml(file_path):
    """Parse Redump DAT (XML) and return list of (title, region, language, full_title)."""
    redump_data = []
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        for game in root.findall("game"):
            full_title = game.get("name")
            title, region, language, redump_full_title = extract_region_and_language(full_title)
            redump_data.append((title, region, language, redump_full_title))
        
        return redump_data
    
    except Exception as e:
        print(f"Error parsing Redump XML: {e}")
        return []

def fuzzy_match_titles(redump_title, redump_region, redump_language, db_titles):
    """Find matches for a Redump title, considering region and language."""
    matches = []
    for (db_id, db_system), (db_title, db_region, db_language) in db_titles.items():
        if db_system != "PSX":
            continue
        db_clean_title = re.sub(r'\s*\((?!Disc\s*\d+\b)[^)]+\)', '', db_title).strip()
        title_score = fuzz.token_sort_ratio(redump_title, db_clean_title)
        
        # Region score: 10 points if exact match, 0 otherwise
        region_score = 10 if redump_region == db_region and redump_region != "Unknown" else 0
        
        # Language score: proportional to overlap (max 10 points)
        redump_langs = set(redump_language.split(", ")) if redump_language != "Unknown" else set()
        db_langs = set(db_language.split(", ")) if db_language != "Unknown" else set()
        lang_overlap = len(redump_langs.intersection(db_langs))
        lang_total = max(len(redump_langs), len(db_langs), 1)
        language_score = (lang_overlap / lang_total) * 10
        
        # Combined score: title (80%) + region (10%) + language (10%)
        total_score = title_score * 0.8 + region_score + language_score
        
        if total_score >= PROMPT_MATCH_THRESHOLD:
            matches.append((db_id, db_title, total_score))
    
    matches.sort(key=lambda x: x[2], reverse=True)
    return matches

def prompt_user_for_match(redump_title, matches):
    """Show GUI dialog with scrollable list to select the correct match or 'No Match'."""
    root = tk.Tk()
    root.title("Select Game Match")
    root.geometry("600x400")
    
    tk.Label(root, text=f"Select the best match for Redump title: '{redump_title}'", wraplength=550).pack(pady=10)
    
    # Create scrollable frame
    canvas = tk.Canvas(root)
    scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.configure(yscrollcommand=scrollbar.set)
    
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    
    selected_match = tk.StringVar(value="No Match")
    
    tk.Radiobutton(scrollable_frame, text="No Match", variable=selected_match, value="No Match").pack(anchor="w")
    for i, (db_id, db_title, score) in enumerate(matches):
        tk.Radiobutton(scrollable_frame, text=f"{db_title} (ID: {db_id}, Score: {score:.1f})", variable=selected_match, value=str(i)).pack(anchor="w")
    
    def submit():
        root.quit()
    
    ttk.Button(root, text="Submit", command=submit).pack(pady=10)
    
    # Enable mouse wheel scrolling
    def on_mouse_wheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    canvas.bind_all("<MouseWheel>", on_mouse_wheel)
    
    root.mainloop()
    choice = selected_match.get()
    root.destroy()
    
    if choice == "No Match":
        return None
    return matches[int(choice)]

def update_database_with_redump():
    """Download Redump DAT zip, extract .dat, and update games.db."""
    redump_file = download_redump_dat()
    if not redump_file:
        print("Failed to download or extract Redump DAT file. Exiting.")
        return
    
    redump_data = parse_redump_xml(redump_file)
    if not redump_data:
        print("No titles parsed from Redump file. Exiting.")
        return
    
    conn, cursor = connect_to_database()
    ensure_table_schema(cursor)
    
    cursor.execute("SELECT game_id, title, region, language, system FROM games WHERE system = 'PSX'")
    db_titles = {(row[0], row[4]): (row[1], row[2], row[3]) for row in cursor.fetchall()}
    
    auto_updated = 0
    user_updated = 0
    no_match = 0
    
    for clean_title, region, language, full_title in redump_data:
        existing_titles = [db_title for (db_id, db_system), (db_title, _, _) in db_titles.items() if db_system == "PSX"]
        if full_title in existing_titles:
            print(f"Skipping unchanged entry: {full_title}")
            continue
        
        matches = fuzzy_match_titles(clean_title, region, language, db_titles)
        if matches and matches[0][2] >= AUTO_MATCH_THRESHOLD:
            db_id, db_title, score = matches[0]
            cursor.execute('''
                UPDATE games 
                SET title = ?, region = ?, language = ?, updated_from_redump = '1'
                WHERE game_id = ? AND system = 'PSX'
            ''', (full_title, region, language, db_id))
            auto_updated += 1
            print(f"Auto-updated {db_id}: '{db_title}' -> '{full_title}' (Region: {region}, Score: {score:.1f})")
        elif matches and matches[0][2] >= PROMPT_MATCH_THRESHOLD:
            print(f"Prompting for Redump title: {full_title}")
            match = prompt_user_for_match(full_title, matches)
            if match:
                db_id, db_title, score = match
                cursor.execute('''
                    UPDATE games 
                    SET title = ?, region = ?, language = ?, updated_from_redump = '1'
                    WHERE game_id = ? AND system = 'PSX'
                ''', (full_title, region, language, db_id))
                user_updated += 1
                print(f"User-updated {db_id}: '{db_title}' -> '{full_title}' (Region: {region}, Score: {score:.1f})")
            else:
                no_match += 1
                print(f"No match selected for {full_title}")
                cursor.execute('''
                    INSERT INTO missing_games (title, region, language, redump_full_title, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (clean_title, region, language, full_title, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                print(f"Added to missing_games: {full_title}")
        else:
            no_match += 1
            print(f"No suitable match for {full_title} (Best Score: {matches[0][2] if matches else 0:.1f})")
            cursor.execute('''
                INSERT INTO missing_games (title, region, language, redump_full_title, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (clean_title, region, language, full_title, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            print(f"Added to missing_games: {full_title}")
    
    conn.commit()
    print(f"\nAuto-updated {auto_updated} games.")
    print(f"User-updated {user_updated} games.")
    print(f"No match for {no_match} games (added to missing_games).")
    
    test_titles = ["Codemasters Demo Disk (Europe)"]
    for test_title in test_titles:
        cursor.execute("SELECT game_id, title, region, system, language, updated_from_redump FROM games WHERE title = ? AND system = 'PSX'", (test_title,))
        result = cursor.fetchone()
        if result:
            print(f"Test (games): {result[0]} = {result[1]} ({result[2]}, {result[3]}, Language: {result[4]}, Updated: {result[5]})")
        cursor.execute("SELECT title, region, language, redump_full_title FROM missing_games WHERE redump_full_title = ?", (test_title,))
        result = cursor.fetchone()
        if result:
            print(f"Test (missing_games): {result[3]} (Region: {result[1]}, Language: {result[2]})")
    
    conn.close()

def main():
    print("Updating games.db with Redump PSX data...")
    update_database_with_redump()

if __name__ == "__main__":
    main()