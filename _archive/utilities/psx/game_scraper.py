import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import re

# Base URLs for each region
BASE_URLS = {
    "NTSC-U": "https://psxdatacenter.com/ulist.html",
    "NTSC-J": "https://psxdatacenter.com/jlist.html",
    "PAL": "https://psxdatacenter.com/plist.html"
}

# Headers to mimic a browser
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://psxdatacenter.com/"
}

# Database path (local, move to /media/fat/retrospin/games.db on MiSTer)
DB_PATH = "games.db"

def create_database():
    """Create SQLite3 database and table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

def scrape_region(region, url):
    """Scrape game data, excluding <span> and [ ] content from titles."""
    print(f"Scraping {region} games from {url}...")
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        tables = soup.find_all("table", class_="sectiontable")
        if not tables:
            print("No tables with class 'sectiontable' found.")
            return []
        
        print(f"Found {len(tables)} sectiontable elements")
        games = []
        
        for table in tables:
            rows = table.find_all("tr")[1:]  # Skip header
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 4:  # Ensure col2 (ID), col3 (title), col4 (language)
                    # Extract game IDs from col2, handling <br> tags
                    col2 = cols[1]
                    game_ids = []
                    contents = col2.contents
                    current_id = ""
                    for content in contents:
                        if isinstance(content, str) and content.strip():
                            current_id += content.strip()
                        elif content.name == "br" and current_id:
                            game_ids.append(current_id)
                            current_id = ""
                    if current_id:
                        game_ids.append(current_id)
                    if not game_ids:
                        game_ids = col2.text.strip().split()
                    
                    # Get title from col3, excluding <span> content
                    col3 = cols[2]
                    base_title = ""
                    for content in col3.contents:
                        if isinstance(content, str):
                            base_title += content.strip()
                        elif content.name in ["span", "br"]:
                            break
                    base_title = re.sub(r'\s*\[.*?\]', '', base_title).strip()
                    
                    # Get language from col4, remove brackets, join with commas
                    language_raw = cols[3].text.strip()
                    languages = [lang.strip("[]") for lang in language_raw.split("][")]
                    language = ", ".join(languages) if languages else "Unknown"
                    
                    # Handle single or multi-disc games
                    for i, game_id in enumerate(game_ids, 1):
                        disc_title = f"{base_title} (Disc {i})" if len(game_ids) > 1 else base_title
                        games.append((game_id, disc_title, region, "PSX", language, None))
        
        print(f"Found {len(games)} game entries in {region}")
        return games
    
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []
    except Exception as e:
        print(f"Error parsing {url}: {e}")
        return []

def populate_database():
    """Scrape all regions and populate the database."""
    create_database()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for region, url in BASE_URLS.items():
        games = scrape_region(region, url)
        if games:
            cursor.executemany('''
                INSERT OR REPLACE INTO games (game_id, title, region, system, language, updated_from_redump)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', games)
            conn.commit()
            print(f"Added {len(games)} games for {region}")
        time.sleep(2)  # Be polite to the server
    
    conn.close()
    print("Database population complete.")

def main():
    print("Starting PSX game data scrape for all regions...")
    populate_database()
    # Verify database contents
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM games WHERE system = 'PSX'")
    count = cursor.fetchone()[0]
    print(f"Total PSX games in database: {count}")
    # Test specific entries
    test_ids = ["SLUS-00515", "SLUS-01026", "SLUS-01183", "SLUS-00955", "SLUS-01224", "SLPS-01330"]
    for test_id in test_ids:
        cursor.execute("SELECT title, region, system, language FROM games WHERE game_id = ? AND system = 'PSX'", (test_id,))
        result = cursor.fetchone()
        if result:
            print(f"Test: {test_id} = {result[0]} ({result[1]}, {result[2]}, Language: {result[3]})")
        else:
            print(f"Test: {test_id} not found")
    conn.close()

if __name__ == "__main__":
    main()