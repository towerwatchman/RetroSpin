import os
import time
import re
import subprocess
import sqlite3

# MiSTer-specific paths
MISTER_CMD = "/dev/MiSTer_cmd"
MISTER_CORE_DIR = "/media/fat/_Console/"
PSX_GAME_PATHS = [
    "/media/fat/games/PSX/",
    "/media/usb0/games/PSX/"
]
SATURN_GAME_PATHS = [
    "/media/fat/games/Saturn/",
    "/media/usb0/games/Saturn/"
]
DB_PATH = "/media/fat/retrospin/games.db"
TMP_MGL_PATH = "/tmp/game.mgl"
SAVE_SCRIPT = "/media/fat/retrospin/save_disc.sh"
RIPDISC_PATH = "/media/fat/retrospin/cdrdao"

def find_core(system):
    """Find the latest core .rbf file for the given system in /media/fat/_Console/."""
    prefix = "PSX_" if system == "PSX" else "Saturn_"
    try:
        rbf_files = [f for f in os.listdir(MISTER_CORE_DIR) if f.startswith(prefix) and f.endswith(".rbf")]
        if not rbf_files:
            print(f"No {system} core found in {MISTER_CORE_DIR}. Please place a {prefix}*.rbf file there.")
            return None
        rbf_files.sort(reverse=True)
        latest_core = os.path.join(MISTER_CORE_DIR, rbf_files[0])
        print(f"Found {system} core: {latest_core}")
        if os.path.exists(latest_core):
            print(f"Verified {latest_core} exists and is readable")
        else:
            print(f"Error: {latest_core} reported but not accessible")
            return None
        return latest_core
    except Exception as e:
        print(f"Error finding {system} core: {e}")
        return None

def load_game_titles():
    """Load game serial to title and system mapping from SQLite database."""
    game_titles = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT serial, title, system FROM games")
        rows = cursor.fetchall()
        for row in rows:
            serial, title, system = row
            game_titles[(serial.strip(), system.strip())] = title.strip()
            print(f"Loaded entry: {serial} -> {title} ({system})")
        print(f"Successfully loaded {len(game_titles)} game titles from {DB_PATH}")
        conn.close()
    except Exception as e:
        print(f"Error loading game titles from database: {e}")
    return game_titles

def get_optical_drive():
    """Detect an optical drive on MiSTer using lsblk."""
    try:
        result = subprocess.run(['lsblk', '-d', '-o', 'NAME,TYPE'], capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "rom":
                dev_path = f"/dev/{parts[0]}"
                print(f"Detected optical drive: {dev_path}")
                return dev_path
        print("No optical drive detected.")
        return None
    except Exception as e:
        print(f"Error detecting drive: {e}")
        return None

def read_psx_game_id(drive_path):
    """Read PSX game serial from system.cnf, minimizing drive activity."""
    try:
        mount_point = "/mnt/cdrom"
        if not os.path.exists(mount_point):
            os.makedirs(mount_point)
        
        mount_cmd = f"mount {drive_path} {mount_point} -t iso9660 -o ro"
        mount_result = os.system(mount_cmd)
        if mount_result != 0:
            print(f"PSX iso9660 mount failed. Trying udf...")
            mount_cmd = f"mount {drive_path} {mount_point} -t udf -o ro"
            mount_result = os.system(mount_cmd)
            if mount_result != 0:
                print(f"Failed to mount {drive_path} with iso9660 or udf. Return code: {mount_result}")
                return None
            else:
                print(f"Successfully mounted {drive_path} with udf")
        else:
            print(f"Successfully mounted {drive_path} with iso9660")
        
        system_cnf_variants = ["system.cnf", "SYSTEM.CNF", "System.cnf"]
        game_id = None
        for root, dirs, files in os.walk(mount_point):
            for variant in system_cnf_variants:
                if variant in files:
                    system_cnf_path = os.path.join(root, variant)
                    with open(system_cnf_path, 'r', encoding='latin-1', errors='ignore') as f:
                        file_text = f.read()
                        print(f"Found {variant} at {system_cnf_path}")
                        for line in file_text.splitlines():
                            if "BOOT" in line.upper():
                                raw_id = line.split("=")[1].strip().split("\\")[1].split(";")[0]
                                game_id = raw_id.replace(".", "").replace("_", "-")
                                print(f"Extracted PSX Game Serial: {game_id}")
                                break
                    if game_id:
                        break
            if game_id:
                break
        
        os.system(f"umount {mount_point}")
        print(f"Unmounted {mount_point}")
        
        if not game_id:
            print("system.cnf not found on disc (checked all case variations).")
        return game_id
    except Exception as e:
        print(f"Error reading PSX disc: {e}")
        os.system(f"umount {mount_point} 2>/dev/null")
        return None

def read_saturn_game_id(drive_path):
    """Read Saturn game serial from disc header at offset 0x20-0x2A."""
    try:
        with open(drive_path, 'rb') as f:
            f.seek(0)  # Sector 0
            sector = f.read(2048)
            game_id = sector[32:42].decode('ascii', errors='ignore').strip()  # Offset 0x20 to 0x2A
            print(f"Extracted Saturn Game Serial: {game_id}")
            return game_id
    except Exception as e:
        print(f"Error reading Saturn disc: {e}")
        return None

def find_game_file(title, system):
    """Search for .chd or .cue game file based on system."""
    paths = PSX_GAME_PATHS if system == "PSX" else SATURN_GAME_PATHS
    
    game_filename = f"{title}.chd"
    for base_path in paths:
        game_file = os.path.join(base_path, game_filename)
        if os.path.exists(game_file):
            print(f"Found .chd game file: {game_file}")
            if os.access(game_file, os.R_OK):
                print(f"Game file {game_file} is readable")
            else:
                print(f"Game file {game_file} is not readable")
            return game_file
    
    game_filename = f"{title}.cue"
    for base_path in paths:
        game_file = os.path.join(base_path, game_filename)
        if os.path.exists(game_file):
            print(f"Found .cue game file: {game_file}")
            if os.access(game_file, os.R_OK):
                print(f"Game file {game_file} is readable")
            else:
                print(f"Game file {game_file} is not readable")
            return game_file
    
    print(f"No .chd or .cue game file found for: {title}")
    return None

def show_popup(message):
    """Display a popup message on MiSTer."""
    try:
        dialog_cmd = f"dialog --msgbox \"{message}\" 10 40"
        with open(MISTER_CMD, "w") as cmd_file:
            cmd_file.write(dialog_cmd + "\n")
            cmd_file.flush()
        print(f"Displayed popup: {message}")
    except Exception as e:
        print(f"Failed to display popup: {e}")

def create_mgl_file(core_path, game_file, mgl_path, system):
    """Create a temporary MGL file for the game."""
    mgl = ET.Element("mistergamedescription")
    rbf = ET.SubElement(mgl, "rbf")
    rbf.text = "_console/psx" if system == "PSX" else "_console/saturn"
    file_tag = ET.SubElement(mgl, "file")
    file_tag.set("delay", "1")
    file_tag.set("type", "s")
    file_tag.set("index", "1" if system == "PSX" else "0")
    file_tag.set("path", game_file)
    
    tree = ET.ElementTree(mgl)
    tree.write(mgl_path, encoding="utf-8", xml_declaration=True)
    print(f"Overwrote MGL file at {mgl_path}")

def log_unknown_game(serial, title, system, drive_path):
    """Log unmatched game to the unknown table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO unknown (serial, title, category, region, system, language, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            serial if serial else "Unknown",
            title,
            "Games",
            "Unknown",
            system,
            "Unknown",
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
        conn.close()
        print(f"Logged unmatched game to unknown table: {serial} ({title}, {system})")
    except Exception as e:
        print(f"Error logging unknown game: {e}")

def launch_game_on_mister(game_serial, title, core_path, system, drive_path):
    """Launch the game on MiSTer using a temporary MGL file."""
    if title == "Unknown Game":
        print(f"Skipping launch for unknown game: {game_serial}")
        log_unknown_game(game_serial, title, system, drive_path)
        return
    
    game_file = find_game_file(title, system)
    if not game_file:
        print(f"Game file not found for {title} ({game_serial}). Triggering save script...")
        save_cmd = f"{SAVE_SCRIPT} \"{drive_path}\" \"{title}\" {system}"
        subprocess.run(save_cmd, shell=True, check=True)
        return
    
    try:
        create_mgl_file(core_path, game_file, TMP_MGL_PATH, system)
        command = f"load_core {TMP_MGL_PATH}"
        print(f"Preparing to send command to {MISTER_CMD}: {command}")
        with open(MISTER_CMD, "w") as cmd_file:
            cmd_file.write(command + "\n")
            cmd_file.flush()
            if os.path.exists(MISTER_CMD):
                print(f"Command '{command}' sent successfully")
            else:
                print(f"Failed to write '{command}' to {MISTER_CMD}")
        print(f"MGL file preserved at {TMP_MGL_PATH} for inspection")
    except Exception as e:
        print(f"Failed to launch game on MiSTer: {e}")

def main():
    print("Starting RetroSpin disc launcher on MiSTer...")
    game_titles = load_game_titles()
    
    psx_core = find_core("PSX")
    saturn_core = find_core("SATURN")
    if not psx_core and not saturn_core:
        show_popup("No PSX or Saturn cores found in /media/fat/_Console/.")
        print("Cannot proceed without cores. Exiting...")
        return
    
    last_game_serial = None
    
    while True:
        drive_path = get_optical_drive()
        if not drive_path:
            print("No optical drive detected. Waiting...")
            time.sleep(10)
            continue
        
        print(f"Checking drive {drive_path}...")
        
        # Try PSX first
        psx_game_serial = read_psx_game_id(drive_path)
        if psx_game_serial:
            if (psx_game_serial, "PSX") != last_game_serial:
                title = game_titles.get((psx_game_serial, "PSX"), "Unknown Game")
                print(f"Found PSX game: {title} ({psx_game_serial})")
                if psx_core:
                    launch_game_on_mister(psx_game_serial, title, psx_core, "PSX", drive_path)
                else:
                    print("No PSX core available to launch game")
                last_game_serial = (psx_game_serial, "PSX")
            else:
                print(f"PSX game {psx_game_serial} already launched. Waiting for new disc...")
            time.sleep(10)
            continue
        
        # Try Saturn if PSX fails
        saturn_game_serial = read_saturn_game_id(drive_path)
        if saturn_game_serial:
            if (saturn_game_serial, "SATURN") != last_game_serial:
                title = game_titles.get((saturn_game_serial, "SATURN"), "Unknown Game")
                print(f"Found Saturn game: {title} ({saturn_game_serial})")
                if saturn_core:
                    launch_game_on_mister(saturn_game_serial, title, saturn_core, "SATURN", drive_path)
                else:
                    print("No Saturn core available to launch game")
                last_game_serial = (saturn_game_serial, "SATURN")
            else:
                print(f"Saturn game {saturn_game_serial} already launched. Waiting for new disc...")
        else:
            print("No game detected. Waiting...")
            last_game_serial = None
        
        time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript stopped by user. Exiting...")