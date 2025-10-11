import os
import sys
import time

# Add /retrospin to sys.path to ensure core package is found
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(os.path.dirname(script_dir)))

from core.utilities.disc import get_optical_drive, is_disc_present, read_saturn_game_id, read_mcd_game_id, read_psx_game_id
from core.utilities.database import load_game_titles
from core.utilities.ui import select_game_title

def read_disc():
    """Read the optical disc and return drive path, title, and system."""
    drive_path = get_optical_drive()
    if not drive_path or not is_disc_present(drive_path):
        return drive_path or "none", "none", "none"
    
    try:
        game_titles = load_game_titles()
    except:
        return drive_path, "none", "none"
    
    # Try Saturn
    try:
        saturn_game_serial = read_saturn_game_id(drive_path)
        if saturn_game_serial:
            serial_key = saturn_game_serial.upper()
            matches = []
            for (db_serial, db_system), titles in game_titles.items():
                if db_system == "ss" and (db_serial == serial_key or db_serial.startswith(serial_key)):
                    matches.extend(titles)
            if matches:
                title = matches[0][1] if len(matches) == 1 else select_game_title(matches, "Saturn", serial_key)
                if title and title != "Unknown Game":
                    return drive_path, title, "ss"
    except:
        pass
    
    # Try Sega CD (Mega CD)
    try:
        mcd_game_serial = read_mcd_game_id(drive_path)
        if mcd_game_serial:
            serial_key = mcd_game_serial.upper()
            us_serial_key = serial_key.replace("-00", "")
            matches = []
            for (db_serial, db_system), titles in game_titles.items():
                if db_system == "mcd" and (db_serial == serial_key or db_serial == us_serial_key or db_serial.startswith(serial_key)):
                    matches.extend(titles)
            if matches:
                title = matches[0][1] if len(matches) == 1 else select_game_title(matches, "Mega CD", serial_key)
                if title and title != "Unknown Game":
                    return drive_path, title, "mcd"
    except:
        pass
    
    # Try PSX
    try:
        psx_game_serial = None
        for attempt in range(2):
            psx_game_serial = read_psx_game_id(drive_path)
            if psx_game_serial:
                break
            time.sleep(1)
            os.system("umount /mnt/cdrom 2>/dev/null")
        if psx_game_serial:
            serial_key = psx_game_serial.replace("_", "").upper()
            matches = []
            for (db_serial, db_system), titles in game_titles.items():
                if db_system == "psx" and (db_serial == serial_key or db_serial.startswith(serial_key)):
                    matches.extend(titles)
            if matches:
                title = matches[0][1] if len(matches) == 1 else select_game_title(matches, "PSX", serial_key)
                if title and title != "Unknown Game":
                    return drive_path, title, "psx"
    except:
        pass
    
    return drive_path, "none", "none"

if __name__ == "__main__":
    drive_path, title, system = read_disc()
    print(f"{drive_path}:{title}:{system}")
    sys.exit(0)