import requests
import os
import zipfile
import glob
import xml.etree.ElementTree as ET
import sqlite3
import re
from datetime import datetime
import tempfile

# URL template for Redump DAT files
REDUMP_URL_TEMPLATE = "http://redump.org/datfile/{}/serial,version"
DATA_DIR = "DATA"
DB_PATH = "games.db"

# List of systems to scrape
SYSTEMS = ["psx", "ajcd", "acd", "cd32", "cdtv", "pce", "ngcd", "3do", "cdi", "mcd", "ss"]

# Region mappings
REGION_MAP = {
    "USA": "NTSC-U",
    "Europe": "PAL",
    "Japan": "NTSC-J",
    "Asia": "NTSC-J",
    "Australia": "PAL",
    "Brazil": "NTSC-U",
    "Canada": "NTSC-U",
    "China": "NTSC-J",
    "France": "PAL",
    "Germany": "PAL",
    "Italy": "PAL",
    "Korea": "NTSC-J",
    "Netherlands": "PAL",
    "Spain": "PAL",
    "Sweden": "PAL",
    "Taiwan": "NTSC-J",
    "UK": "PAL",
    "Russia": "PAL",
    "Scandinavia": "PAL",
    "Greece": "PAL",
    "Finland": "PAL",
    "Norway": "PAL",
    "Ireland": "PAL",
    "Portugal": "PAL",
    "Austria": "PAL",
    "Israel": "PAL",
    "Poland": "PAL",
    "Denmark": "PAL",
    "Belgium": "PAL",
    "India": "PAL",
    "Latin America": "PAL",
    "Croatia": "PAL",
    "World": "NTSC-U",
    "Switzerland": "PAL",
    "South Africa": "PAL"
}

# Language mappings for explicit tags
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
    "Pl": "Polish",
    "Ru": "Russian",
    "El": "Greek",
    "He": "Hebrew"
}

# Region-to-language mapping for all regions
REGION_LANGUAGE_MAP = {
    "USA": "English",
    "Europe": "English",
    "Japan": "Japanese",
    "Asia": "English",
    "Australia": "English",
    "Brazil": "Portuguese",
    "Canada": "English",
    "China": "Chinese",
    "France": "French",
    "Germany": "German",
    "Italy": "Italian",
    "Korea": "Korean",
    "Netherlands": "Dutch",
    "Spain": "Spanish",
    "Sweden": "Swedish",
    "Taiwan": "Chinese",
    "UK": "English",
    "Russia": "Russian",
    "Scandinavia": "English",
    "Greece": "Greek",
    "Finland": "Finnish",
    "Norway": "Norwegian",
    "Ireland": "English",
    "Portugal": "Portuguese",
    "Austria": "German",
    "Israel": "Hebrew",
    "Poland": "Polish",
    "Denmark": "Danish",
    "Belgium": "Dutch",
    "India": "English",
    "Latin America": "Spanish",
    "Croatia": "Croatian",
    "World": "English",
    "Switzerland": "German",
    "South Africa": "English"
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
            serial TEXT,
            title TEXT,
            category TEXT,
            region TEXT,
            system TEXT,
            language TEXT,
            PRIMARY KEY (serial, system)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS unknown (
            serial TEXT,
            title TEXT,
            category TEXT,
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
    
    # Check for regions in parentheses (e.g., "Japan", "USA", "Japan, Asia")
    region_match = re.findall(r'\(([^)]+)\)', game_name)
    matched_regions = []
    if region_match:
        for regions in region_match:
            # Split multiple regions (e.g., "Japan, Asia" → ["Japan", "Asia"])
            region_list = [r.strip() for r in regions.split(",")]
            for r in region_list:
                # Check if the region (or part of it) is in REGION_MAP
                for map_region, db_region in REGION_MAP.items():
                    if map_region.lower() in r.lower():
                        region = db_region
                        matched_regions.append(map_region)
                        break
                if region != "Unknown":
                    break
            if region != "Unknown":
                break
    
    # Check for language map
    lang_match = re.search(r'\((En?,(?:[A-Z][a-z]?,)*[A-Z][a-z]?)\)', game_name)
    if lang_match:
        redump_langs = lang_match.group(1).split(",")
        db_langs = [LANGUAGE_MAP.get(lang.strip(), lang.strip()) for lang in redump_langs]
        language = ", ".join(db_langs)
    else:
        # Region-based language mapping
        for matched_region in matched_regions:
            if matched_region in REGION_LANGUAGE_MAP:
                language = REGION_LANGUAGE_MAP[matched_region]
                break
    
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
    unknown_games = []
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        for game in root.findall("game"):
            title = game.get("name")
            category_elem = game.find("category")
            serial_elem = game.find("serial")
            
            category = category_elem.text.strip() if category_elem is not None else "Unknown"
            serial = serial_elem.text.strip() if serial_elem is not None else None
            region, language = extract_region_and_language(title)
            
            if not serial or serial == "":
                # Add to unknown_games if no serial
                unknown_games.append({
                    "title": title,
                    "category": category,
                    "serial": "Unknown",
                    "region": region,
                    "system": system.upper(),
                    "language": language,
                    "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            else:
                # Split multiple serials and create a row for each
                serials = [s.strip() for s in serial.split(",") if s.strip()]
                for serial in serials:
                    games.append({
                        "title": title,
                        "category": category,
                        "serial": serial,
                        "region": region,
                        "system": system.upper(),
                        "language": language
                    })
        
        return games, unknown_games
    
    except Exception as e:
        print(f"Error parsing Redump XML for {system}: {e}")
        return [], []

def populate_database():
    """Scrape Redump DAT files for all systems and populate games and unknown tables."""
    ensure_data_dir()
    conn, cursor = connect_to_database()
    ensure_table_schema(cursor)
    
    for system in SYSTEMS:
        dat_path = download_and_extract_dat(system)
        if not dat_path:
            continue
        
        games, unknown_games = parse_redump_xml(dat_path, system)
        
        # Insert into games table
        for game in games:
            cursor.execute('''
                INSERT OR REPLACE INTO games (serial, title, category, region, system, language)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                game["serial"],
                game["title"],
                game["category"],
                game["region"],
                game["system"],
                game["language"]
            ))
        
        # Insert into unknown table
        for game in unknown_games:
            cursor.execute('''
                INSERT INTO unknown (serial, title, category, region, system, language, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                game["serial"],
                game["title"],
                game["category"],
                game["region"],
                game["system"],
                game["language"],
                game["timestamp"]
            ))
        
        conn.commit()
        print(f"Added {len(games)} games and {len(unknown_games)} unknown entries for {system}")
    
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
    conn.close()

if __name__ == "__main__":
    main()