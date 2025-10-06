import sqlite3

DB_PATH = "/media/fat/retrospin/games.db"

def load_game_titles():
    """Load game serial to title mappings from SQLite database, allowing multiple matches."""
    game_titles = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT serial, title, system FROM games")
        rows = cursor.fetchall()
        for row in rows:
            serial, title, system = row
            serial = serial.strip().replace("_", "").upper()  # Normalize serial, preserve hyphens
            system = system.strip().lower()  # Normalize system (PSX → psx, MCD → mcd)
            # Store as list to handle multiple matches
            if (serial, system) not in game_titles:
                game_titles[(serial, system)] = []
            game_titles[(serial, system)].append((serial, title.strip()))
        print(f"Successfully loaded {sum(len(titles) for titles in game_titles.values())} game titles from {DB_PATH}")
        conn.close()
    except Exception as e:
        print(f"Error loading game titles from database: {e}")
    return game_titles