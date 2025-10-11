import sqlite3
import os

DATA_DIR = "data"
DAT_DIR = os.path.join(DATA_DIR, "dat")
DB_PATH = os.path.join(DATA_DIR, "games.db")

def connect_to_database():
    """Connect to games.db and return connection and cursor."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    return conn, cursor

def get_db_path():
    """Get the absolute path to the games.db file relative to the script's location."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "../../data/games.db")
    print(f"Script directory: {script_dir}")
    print(f"Computed DB path: {db_path}")
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
    return db_path

def create_table_schema(cursor):
    """Ensure tables exist with correct schema."""
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
            timestamp TEXT,
            PRIMARY KEY (title, system)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS systems (
            system TEXT,
            core TEXT,
            name TEXT,            
            PRIMARY KEY (system)
        )
    ''')

def load_game_titles():
    """Load game serial to title mappings from SQLite database, allowing multiple matches."""
    game_titles = {}
    db_path = get_db_path()
    try:
        print(f"Using {db_path} for database file")
        if not os.path.exists(db_path):
            print(f"Database file not found at {db_path}")
            return game_titles
        conn = sqlite3.connect(db_path)
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
        print(f"Successfully loaded {sum(len(titles) for titles in game_titles.values())} game titles from {db_path}")
        conn.close()
    except Exception as e:
        print(f"Error loading game titles from database: {e}")
    return game_titles