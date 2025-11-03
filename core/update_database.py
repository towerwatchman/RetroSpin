import requests
import os
import zipfile
import glob
import xml.etree.ElementTree as ET
import sqlite3
import re
from datetime import datetime
from core.utilities.database import create_table_schema, connect_to_database
import tempfile
import subprocess
import sys
import time

# URL template for Redump DAT files
REDUMP_URL_TEMPLATE = "http://redump.org/datfile/{}/serial,version"
DATA_DIR = "data"
DAT_DIR = os.path.join(DATA_DIR, "dat")
DB_PATH = os.path.join(DATA_DIR, "games.db")

# List of systems to scrape
SYSTEMS = ["psx", "ajcd", "acd", "cd32", "cdtv", "pce", "ngcd", "3do", "cdi", "mcd", "ss"]
SYSTEM_NAMES = ["Sony Playstation", "Atari Jaguar CD", "Amiga CD", "Amiga CD32", "Amiga CDTV", "NEC PC Engine", "Neo Geo CD", "Panasonic 3DO", "Philips CDI", "Sega CD", "Sega Saturn"]

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

# Browser-like headers for requests
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "http://redump.org/downloads/"
}

def ensure_data_dir():
    """Create data and dat directories if they don't exist."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(DAT_DIR):
        os.makedirs(DAT_DIR)

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

def download_and_extract_dat(i, system, system_name, gauge_process, base_percent, system_share):
    """Download Redump DAT zip for a system, extract .dat, and return its path."""
    url = REDUMP_URL_TEMPLATE.format(system)
    zip_path = None
    for attempt in range(2):
        try:
            if attempt == 0:
                update_gauge(gauge_process, f"Fetching DAT file for {system_name}...")
            else:
                update_gauge(gauge_process, f"Retrying fetch for {system_name}...")
            response = requests.get(url, stream=True, timeout=10, headers=REQUEST_HEADERS)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
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
            
            downloaded = 0
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            sub_percent = (downloaded / total_size) * 100
                            overall_percent = int(base_percent + (sub_percent / 100) * (system_share / 2))  # Download is half of system share
                            update_gauge(gauge_process, f"Downloading DAT file for {system_name}: {int(sub_percent)}%", overall_percent)
            
            if total_size > 0:
                update_gauge(gauge_process, f"Downloaded DAT file for {system_name}", int(base_percent + (system_share / 2)))
            else:
                update_gauge(gauge_process, f"Saved zip file for {system_name}", int(base_percent + (system_share / 2)))
            
            # If successful, break the retry loop
            break
        
        except requests.RequestException as e:
            update_gauge(gauge_process, f"Error downloading for {system_name}: {e}")
            if attempt == 0:
                update_gauge(gauge_process, "Retrying in 1 second...")
                time.sleep(1)
            else:
                return None
    
    if zip_path is None:
        return None
    
    # Now attempt extraction
    try:
        update_gauge(gauge_process, f"Extracting zip for {system_name}...", int(base_percent + (system_share / 2)))
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            dat_files = glob.glob(os.path.join(temp_dir, "*.dat"))
            if not dat_files:
                raise ValueError(f"No .dat file found in the zip for {system_name}")
            if len(dat_files) > 1:
                update_gauge(gauge_process, f"Warning: Multiple .dat files for {system_name}, using first")
            dat_path = dat_files[0]
            
            # Move .dat to dat directory
            dat_filename = os.path.basename(dat_path)
            final_dat_path = os.path.join(DAT_DIR, dat_filename)
            with open(dat_path, 'rb') as src, open(final_dat_path, 'wb') as dst:
                dst.write(src.read())
        update_gauge(gauge_process, f"Saved DAT file for {system_name}", int(base_percent + (system_share * 0.6)))
        
        # Delete the zip file
        os.remove(zip_path)
        update_gauge(gauge_process, f"Deleted zip file for {system_name}", int(base_percent + (system_share * 0.6)))
        
        return final_dat_path
    
    except zipfile.BadZipFile as e:
        update_gauge(gauge_process, f"Error: Invalid zip for {system_name}")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        return None
    except Exception as e:
        update_gauge(gauge_process, f"Error processing for {system_name}: {e}")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        return None

def parse_redump_xml(file_path, system, system_name, gauge_process, base_percent, system_share):
    """Parse Redump DAT (XML) and return list of game data."""
    games = []
    unknown_games = []
    try:
        update_gauge(gauge_process, f"Parsing XML for {system_name}...", int(base_percent + (system_share * 0.6)))
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
        
        update_gauge(gauge_process, f"Parsed {len(games)} games and {len(unknown_games)} unknown for {system_name}", int(base_percent + (system_share * 0.8)))
        return games, unknown_games
    
    except Exception as e:
        update_gauge(gauge_process, f"Error parsing XML for {system_name}: {e}")
        return [], []

def update_gauge(gauge_process, message, percent=None):
    """Update the dialog gauge with new message and optional percent."""
    if percent is not None:
        input_str = f"XXX\n{percent}\n{message}\nXXX\n"
    else:
        input_str = f"XXX\n{message}\nXXX\n"
    gauge_process.stdin.write(input_str.encode())
    gauge_process.stdin.flush()

def populate_database(gauge_process):
    """Scrape Redump DAT files for all systems and populate games and unknown tables."""
    ensure_data_dir()
    conn, cursor = connect_to_database()
    create_table_schema(cursor)
    
    num_systems = len(SYSTEMS)
    system_share = 100 / num_systems
    
    failed_systems = []
    
    for i in range(num_systems):
        system = SYSTEMS[i]
        system_name = SYSTEM_NAMES[i]
        base_percent = i * system_share
        
        dat_path = download_and_extract_dat(i, system, system_name, gauge_process, base_percent, system_share)
        if not dat_path:
            failed_systems.append(system_name)
            update_gauge(gauge_process, f"Failed to process {system_name}", int(base_percent + system_share))
            continue
        
        games, unknown_games = parse_redump_xml(dat_path, system, system_name, gauge_process, base_percent, system_share)
        
        update_gauge(gauge_process, f"Inserting data for {system_name} into database...", int(base_percent + (system_share * 0.8)))
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
                INSERT OR REPLACE INTO unknown (serial, title, category, region, system, language, timestamp)
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
        update_gauge(gauge_process, f"Inserted data for {system_name}", int(base_percent + system_share))
    
    # Close the gauge
    gauge_process.stdin.close()
    gauge_process.wait()
    
    # Get counts for final message
    cursor.execute("SELECT COUNT(*) FROM games")
    game_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM unknown")
    unknown_count = cursor.fetchone()[0]
    
    conn.close()
    
    # Show completion message
    message = f"Database update complete.\nTotal games: {game_count}\nTotal unknown entries: {unknown_count}"
    if failed_systems:
        message += f"\nFailed to update: {', '.join(failed_systems)}"
    cmd = ['dialog', '--backtitle', 'RetroSpin Disc Manager', '--msgbox', message, '10', '50']
    cmd_str = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in cmd]) + ' >/dev/tty'
    try:
        subprocess.run(cmd_str, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - update_database.py: Failed to display msgbox: {e}\n")