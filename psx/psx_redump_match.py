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
import tempfile
import glob

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
    """Download the latest PSX Redump DAT file and return its local path."""
    try:
        print(f"Fetching Redump DAT file from {REDUMP_URL}...")
        response = requests.get(REDUMP_URL, timeout=10)
        response.raise_for_status()
        
        # Extract filename from Content-Disposition or URL
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
        print(f"Saved Redump DAT file to {zip_path}")
        
        # Extract the zip file
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                print(f"Extracted zip file to temporary directory: {temp_dir}")
            
            # Find the XML file
            xml_files = glob.glob(os.path.join(temp_dir, "*.xml"))
            if not xml_files:
                raise ValueError("No XML file found in the downloaded zip")
            if len(xml_files) > 1:
                print(f"Warning: Multiple XML files found, using the first: {xml_files[0]}")
            xml_path = xml_files[0]
            
            # Read the XML content
            with open(xml_path, 'rb') as f:
                xml_content = f.read()
            
            # Save XML content to a local file for parsing
            xml_filename = os.path.basename(xml_path)
            local_xml_path = xml_filename
            with open(local_xml_path, 'wb') as f:
                f.write(xml_content)
            print(f"Saved extracted XML to {local_xml_path}")
            
            return local_xml_path
    
    except requests.RequestException as e:
        print(f"Error downloading Redump DAT file: {e}")
        return None
    except zipfile.BadZipFile:
        print(f"Error: Downloaded file is not a valid zip")
        return None
    except Exception as e:
        print(f"Error extracting zip file: {e}")
        return None

def connect_to_database():
    """Connect to games.db and return connection and cursor."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    return conn, cursor

def ensure_table_schema(cursor):
    """Ensure games table exists with correct schema."""
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
    """Parse Redump XML and return list of (game_id, title, region, language, full_title)."""
    redump_data = []
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        for game in root.findall("game"):
            full_title = game.get("name")
            serial_elem = game.find("serial")
            game_id = serial_elem.text.strip() if serial_elem is not None else None
            if game_id:
                game_id = game_id.replace(",", ", ")
            title, region, language, redump_full_title = extract_region_and_language(full_title)
            redump_data.append((game_id, title, region, language, redump_full_title))
        
        return redump_data
    
    except Exception as e:
        print(f"Error parsing Redump XML: {e}")
        return []

def fuzzy_match_titles(redump_title, redump_region, redump_language, db_titles):
    """Find matches for a Redump title, returning list of (db_id, db_title, score)."""
    matches = []
    for (db_id, db_system), db_title in db_titles.items():
        if db_system != "PSX":
            continue
        db_clean_title = re.sub(r'\s*\((?!Disc\s*\d+\b)[^)]+\)', '', db_title).strip()
        score = fuzz.token_sort_ratio(redump_title, db_clean_title)
        if score >= PROMPT_MATCH_THRESHOLD:
            matches.append((db_id, db_title, score))
    matches.sort(key=lambda x: x[2], reverse=True)
    return matches

def prompt_user_for_match(redump_title, matches):
    """Show GUI dialog to select the correct match or 'No Match'."""
    root = tk.Tk()
    root.title("Select Game Match")
    root.geometry("600x400")
    
    tk.Label(root, text=f"Select the best match for Redump title: '{redump_title}'", wraplength=550).pack(pady=10)
    
    selected_match = tk.StringVar(value="No Match")
    
    frame = ttk.Frame(root)
    frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    tk.Radiobutton(frame, text="No Match", variable=selected_match, value="No Match").pack(anchor="w")
    for i, (db_id, db_title, score) in enumerate(matches):
        tk.Radiobutton(frame, text=f"{db_title} (ID: {db_id}, Score: {score:.1f})", variable=selected_match, value=str(i)).pack(anchor="w")
    
    def submit():
        root.quit()
    
    ttk.Button(root, text="Submit", command=submit).pack(pady=10)
    
    root.mainloop()
    choice = selected_match.get()
    root.destroy()
    
    if choice == "No Match":
        return None
    return matches[int(choice)]

def update_database_with_redump():
    """Download Redump DAT and update games.db, auto-matching >=85%, prompting for 50-85%."""
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
    
    cursor.execute("SELECT game_id, title, system FROM games WHERE system = 'PSX'")
    db_titles = {(row[0], row[2]): row[1] for row in cursor.fetchall()}
    
    auto_updated = 0
    user_updated = 0
    no_match = 0
    
    for game_id, clean_title, region, language, full_title in redump_data:
        if not game_id:
            print(f"Skipping Redump entry with no ID: {full_title}")
            continue
        
        existing_title = db_titles.get((game_id, "PSX"))
        if existing_title == full_title:
            print(f"Skipping unchanged entry: {game_id} = {full_title}")
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
            print(f"Prompting for Redump title: {full_title} (ID: {game_id})")
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
                print(f"No match selected for {full_title} (ID: {game_id})")
        else:
            no_match += 1
            print(f"No suitable match for {full_title} (ID: {game_id}, Best Score: {matches[0][2] if matches else 0:.1f})")
    
    conn.commit()
    print(f"\nAuto-updated {auto_updated} games.")
    print(f"User-updated {user_updated} games.")
    print(f"No match for {no_match} games.")
    
    test_ids = ["SLUS-00515"]
    for test_id in test_ids:
        cursor.execute("SELECT title, region, system, language, updated_from_redump FROM games WHERE game_id = ? AND system = 'PSX'", (test_id,))
        result = cursor.fetchone()
        if result:
            print(f"Test: {test_id} = {result[0]} ({result[1]}, {result[2]}, Language: {result[3]}, Updated: {result[4]})")
    
    conn.close()

def main():
    print("Updating games.db with Redump PSX data...")
    update_database_with_redump()

if __name__ == "__main__":
    main()