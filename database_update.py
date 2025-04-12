import requests
import os
import zipfile
import glob
import xml.etree.ElementTree as ET
import sqlite3
import re
from datetime import datetime
import tempfile  # Added missing import

# URL template for Redump DAT files
REDUMP_URL_TEMPLATE = "http://redump.org/datfile/{}/serial,version"
DATA_DIR = "DATA"
DB_PATH = "games.db"

# List of systems to scrape
SYSTEMS = ["psx", "ss", "ps2"]  # Adjusted 'saturn' to 'ss' per output

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

def ensure_data_dir():
    """Create DATA directory if it doesn't exist."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def connect_to_database():
    """Connect to games.db and return connection and cursor."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    return conn, cursor

def ensure_table_schema(cursor):
    """Ensure games and unknown tables exist with correct schema."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            title TEXT,
            category TEXT,
            serial TEXT,
            region TEXT,
            system TEXT,
            language TEXT,
            PRIMARY KEY (serial, system)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS unknown (
            title TEXT,
            category TEXT,
            serial TEXT,
            region TEXT,
            system TEXT,
            language TEXT,
            timestamp TEXT
        )
    ''')

def extract_region_and_language(game_name):
    """Extract region and language from game name."""
    region = "Unknown"
    language = "Unknown"
    
    for redump_region, db_region in REGION_MAP.items():
        if redump_region in game_name:
            region = db_region
            break
    
    lang_match = re.search(r'\((En?,(?:[A-Z][a-z]?,)*[A-Z][a-z]?)\)', game_name)
    if lang_match:
        redump_langs = lang_match.group(1).split(",")
        db_langs = [LANGUAGE_MAP.get(lang.strip(), lang.strip()) for lang in redump_langs]
        language = ", ".join(db_langs)
    elif "(USA)" in game_name or "(Canada)" in game_name:
        language = "English"
    
    return region, language

def download_and_extract_dat(system):
    """Download Redump DAT zip for a system, extract .dat, and return its path."""
    url = REDUMP_URL_TEMPLATE.format(system)
    try:
        print(f"Fetching DAT file for {system} from {url}...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Extract filename or use default
        filename = None
        if 'Content-Disposition' in response.headers:
            disposition = response.headers['Content-Disposition']
            match = re.search(r'filename="(.+)"', disposition)
            if match:
                filename = match.group(1)
        if not filename:
            filename = f"{system}_redump_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.zip"
        
        zip_path = os.path.join(DATA_DIR, filename)
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        print(f"Saved zip file to {zip_path}")
        
        # Extract the .dat file
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
                print(f"Extracted zip file to temporary directory: {temp_dir}")
            
            dat_files = glob.glob(os.path.join(temp_dir, "*.dat"))
            if not dat_files:
                raise ValueError(f"No .dat file found in the zip for {system}")
            if len(dat_files) > 1:
                print(f"Warning: Multiple .dat files found for {system}, using the first: {dat_files[0]}")
            dat_path = dat_files[0]
            
            # Move .dat to DATA directory
            dat_filename = os.path.basename(dat_path)
            final_dat_path = os.path.join(DATA_DIR, dat_filename)
            with open(dat_path, 'rb') as src, open(final_dat_path, 'wb') as dst:
                dst.write(src.read())
            print(f"Saved DAT file to {final_dat_path}")
            
            # Delete the zip file
            os.remove(zip_path)
            print(f"Deleted zip file: {zip_path}")
            
            return final_dat_path
    
    except requests.RequestException as e:
        print(f"Error downloading DAT file for {system}: {e}")
        return None
    except zipfile.BadZipFile:
        print(f"Error: Downloaded file for {system} is not a valid zip")
        return None
    except Exception as e:
        print(f"Error processing DAT file for {system}: {e}")
        return None

def parse_redump_xml(file_path, system):
    """Parse Redump DAT (XML) and return list of game data."""
    games = []
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        for game in root.findall("game"):
            title = game.get("name")
            category_elem = game.find("category")
            serial_elem = game.find("serial")
            
            category = category_elem.text.strip() if category_elem is not None else "Unknown"
            serial = serial_elem.text.strip() if serial_elem is not None else "Unknown"
            region, language = extract_region_and_language(title)
            
            games.append({
                "title": title,
                "category": category,
                "serial": serial,
                "region": region,
                "system": system.upper(),
                "language": language
            })
        
        return games
    
    except Exception as e:
        print(f"Error parsing Redump XML for {system}: {e}")
        return []

def populate_database():
    """Scrape Redump DAT files for all systems and populate games table."""
    ensure_data_dir()
    conn, cursor = connect_to_database()
    ensure_table_schema(cursor)
    
    for system in SYSTEMS:
        dat_path = download_and_extract_dat(system)
        if not dat_path:
            continue
        
        games = parse_redump_xml(dat_path, system)
        if not games:
            continue
        
        for game in games:
            cursor.execute('''
                INSERT OR REPLACE INTO games (title, category, serial, region, system, language)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                game["title"],
                game["category"],
                game["serial"],
                game["region"],
                game["system"],
                game["language"]
            ))
        
        conn.commit()
        print(f"Added {len(games)} games for {system}")
    
    conn.close()
    print("Database population complete.")

def main():
    print("Scraping Redump DAT files and populating games database...")
    populate_database()
    # Verify database contents
    conn, cursor = connect_to_database()
    cursor.execute("SELECT COUNT(*) FROM games")
    game_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM unknown")
    unknown_count = cursor.fetchone()[0]
    print(f"Total games in database: {game_count}")
    print(f"Total unknown entries: {unknown_count}")
    # Test specific entries
    test_titles = ["Ace Combat 3 - Electrosphere (Europe) (En,Fr,De,Es,It)", "Bio Hazard (Japan) (Rev 1)"]
    for title in test_titles:
        cursor.execute("SELECT title, category, serial, region, system, language FROM games WHERE title = ?", (title,))
        result = cursor.fetchone()
        if result:
            print(f"Test: {result[0]} (Category: {result[1]}, Serial: {result[2]}, Region: {result[3]}, System: {result[4]}, Language: {result[5]})")
    conn.close()

if __name__ == "__main__":
    main()