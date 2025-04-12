import requests
from bs4 import BeautifulSoup
import sqlite3

URL = "https://elephantflea.pw/2024/07/sega-saturn-game-ids"
DB_PATH = "games.db"  # Local initially, move to /media/fat/retrospin/games.db on MiSTer

# Initialize SQLite database
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

# Scrape the website
response = requests.get(URL)
soup = BeautifulSoup(response.content, "html.parser")
table = soup.find("table")
rows = table.find_all("tr")[1:]  # Skip header

# Insert entries into database
for row in rows:
    cols = row.find_all("td")
    if len(cols) >= 2:
        title = cols[0].text.strip()  # e.g., "Tokimeki Memorial Drama Series Vol. 1 - Nijiiro no Seishun (Japan) (Demo)"
        full_id = cols[1].text.strip()  # e.g., "6106663   V1.000"
        game_id = full_id.split()[0]    # Take first part, e.g., "6106663"
        system = "SATURN"
        
        # Determine region from title
        if "(Japan)" in title:
            region = "NTSC-J"
        elif "(USA)" in title:
            region = "NTSC-U"
        elif "(Europe)" in title:
            region = "PAL"
        else:
            region = "Unknown"
        
        # Insert or update entry
        cursor.execute('''
            INSERT OR REPLACE INTO games (game_id, title, region, system)
            VALUES (?, ?, ?, ?)
        ''', (game_id, title, region, system))
        print(f"Added: {game_id}, {title}, {region}, {system}")

conn.commit()
conn.close()
print("Scraping complete")