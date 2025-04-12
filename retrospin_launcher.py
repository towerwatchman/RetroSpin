import os
import time
from retrospin.core import find_core
from retrospin.database import load_game_titles
from retrospin.disc import get_optical_drive, is_disc_present, read_saturn_game_id, read_mcd_game_id, read_psx_game_id
from retrospin.ui import show_popup, select_game_title
from retrospin.launcher import launch_game_on_mister
from retrospin.files import find_game_file

def main():
    print("Starting RetroSpin disc launcher on MiSTer...")
    game_titles = load_game_titles()
    
    psx_core = find_core("psx")
    saturn_core = find_core("ss")
    mcd_core = find_core("mcd")
    if not psx_core and not saturn_core and not mcd_core:
        show_popup("No PSX, Saturn, or Mega CD cores found in /media/fat/_Console/.")
        print("Cannot proceed without cores. Exiting...")
        return
    
    last_game_serial = None
    last_drive_path = None
    
    while True:
        drive_path = get_optical_drive()
        
        # Check if drive is accessible and disc is present
        if drive_path and is_disc_present(drive_path):
            if last_game_serial and drive_path == last_drive_path:
                print(f"Same game already loaded: {last_game_serial}. Waiting for drive to open...")
                time.sleep(1)
                continue
            
            print(f"Checking drive {drive_path}...")
            
            # Try Saturn
            saturn_game_serial = read_saturn_game_id(drive_path)
            if saturn_game_serial:
                serial_key = saturn_game_serial.upper()
                print(f"Looking up Saturn serial: {serial_key}")
                matches = []
                # Check for exact and partial matches
                for (db_serial, db_system), titles in game_titles.items():
                    if db_system == "ss" and (db_serial == serial_key or db_serial.startswith(serial_key)):
                        matches.extend(titles)
                print(f"Saturn matches found: {len(matches)}")
                if matches:
                    if len(matches) == 1:
                        title = matches[0][1]
                    else:
                        title = select_game_title(matches, "Saturn", serial_key)
                    print(f"Found Saturn game: {title} ({saturn_game_serial})")
                    if saturn_core and title != "Unknown Game":
                        launch_game_on_mister(saturn_game_serial, title, saturn_core, "ss", drive_path, find_game_file)
                    else:
                        print(f"No Saturn core or no valid match for {saturn_game_serial}. Skipping.")
                else:
                    print(f"No database match for Saturn serial {saturn_game_serial}. Skipping.")
                last_game_serial = (saturn_game_serial, "ss")
                last_drive_path = drive_path
                time.sleep(1)
                continue
            
            # Try Sega CD
            mcd_game_serial = read_mcd_game_id(drive_path)
            if mcd_game_serial:
                serial_key = mcd_game_serial.upper()
                print(f"Looking up Sega CD serial: {serial_key}")
                matches = []
                # Check for exact and partial matches
                for (db_serial, db_system), titles in game_titles.items():
                    if db_system == "mcd" and (db_serial == serial_key or db_serial.startswith(serial_key)):
                        matches.extend(titles)
                print(f"Sega CD matches found: {len(matches)}")
                if matches:
                    if len(matches) == 1:
                        title = matches[0][1]
                    else:
                        title = select_game_title(matches, "Sega CD", serial_key)
                    print(f"Found Sega CD game: {title} ({mcd_game_serial})")
                    if mcd_core and title != "Unknown Game":
                        launch_game_on_mister(mcd_game_serial, title, mcd_core, "mcd", drive_path, find_game_file)
                    else:
                        print(f"No Sega CD core or no valid match for {mcd_game_serial}. Skipping.")
                else:
                    print(f"No database match for Sega CD serial {mcd_game_serial}. Skipping.")
                last_game_serial = (mcd_game_serial, "mcd")
                last_drive_path = drive_path
                time.sleep(1)
                continue
            
            # Try PSX
            psx_game_serial = None
            for attempt in range(2):
                psx_game_serial = read_psx_game_id(drive_path)
                if psx_game_serial:
                    break
                print(f"PSX read attempt {attempt + 1} failed, retrying after delay...")
                time.sleep(1)
                os.system(f"umount /mnt/cdrom 2>/dev/null")  # Force unmount
            if psx_game_serial:
                serial_key = psx_game_serial.replace("_", "").upper()
                print(f"Looking up PSX serial: {serial_key}")
                matches = []
                # Check for exact and partial matches
                for (db_serial, db_system), titles in game_titles.items():
                    if db_system == "psx" and (db_serial == serial_key or db_serial.startswith(serial_key)):
                        matches.extend(titles)
                print(f"PSX matches found: {len(matches)}")
                if matches:
                    if len(matches) == 1:
                        title = matches[0][1]
                    else:
                        title = select_game_title(matches, "PSX", serial_key)
                    print(f"Found PSX game: {title} ({psx_game_serial})")
                    if psx_core:
                        launch_game_on_mister(psx_game_serial, title, psx_core, "psx", drive_path, find_game_file)
                    else:
                        print("No PSX core available to launch game")
                else:
                    print(f"No database match for PSX serial {psx_game_serial}. Skipping.")
                last_game_serial = (psx_game_serial, "psx")
                last_drive_path = drive_path
                time.sleep(1)
                continue
            
            print("No game detected. Waiting...")
            last_game_serial = None
            last_drive_path = None
        else:
            print("No optical drive or disc detected. Waiting...")
            last_game_serial = None
            last_drive_path = None
        
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript stopped by user. Exiting...")