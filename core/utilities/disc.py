import os
import re
import subprocess
import time
from core.utilities.database import load_game_titles
from core.utilities.ui import show_message

def log(message):
    """Log messages to /tmp/retrospin_err.log instead of console."""
    print(message)
    #with open("/tmp/retrospin_err.log", "a") as f:
    #    f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - disc.py: {message}\n")

def get_optical_drive():
    """Detect an optical drive on MiSTer using lsblk."""
    try:
        result = subprocess.run(['lsblk', '-d', '-o', 'NAME,TYPE'], capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "rom":
                dev_path = f"/dev/{parts[0]}"
                log(f"Detected optical drive: {dev_path}")
                return dev_path
        log("No optical drive detected.")
        show_message("No optical drive detected.", title="Retrospin")
        return None
    except Exception as e:
        log(f"Error detecting drive: {e}")
        show_message(f"Error detecting drive: {str(e)}", title="Retrospin")
        return None

def is_disc_present(drive_path):
    """Check if a disc is present in the drive."""
    try:
        with open(drive_path, 'rb') as f:
            f.read(1)  # Try reading a byte to check if disc is accessible
        return True
    except Exception as e:
        log(f"No disc detected in {drive_path}: {e}")
        return False

def is_mounted(drive_path, mount_point):
    """Check if the drive is already mounted at the mount point."""
    try:
        result = subprocess.run(['mount'], capture_output=True, text=True, check=True)
        return f"{drive_path} on {mount_point}" in result.stdout
    except Exception as e:
        log(f"Error checking mount status: {e}")
        return False

def read_psx_game_id(drive_path):
    """Read PSX game serial and disc name from system.cnf on physical disc."""
    mount_point = "/mnt/cdrom"
    disc_name = None
    game_serial = None
    try:
        # Unmount if already mounted
        if is_mounted(drive_path, mount_point):
            log(f"{drive_path} already mounted on {mount_point}, attempting to unmount...")
            os.system(f"umount -f {mount_point} 2>/dev/null")
        else:
            os.system(f"umount {mount_point} 2>/dev/null")
        if not os.path.exists(mount_point):
            os.makedirs(mount_point)
        
        # Try mounting as ISO9660 or UDF
        log(f"Attempting to mount {drive_path} as iso9660...")
        mount_cmd = f"mount {drive_path} {mount_point} -t iso9660 -o ro"
        mount_result = os.system(mount_cmd)
        if mount_result != 0:
            log("PSX iso9660 mount failed. Trying udf...")
            mount_cmd = f"mount {drive_path} {mount_point} -t udf -o ro"
            mount_result = os.system(mount_cmd)
            if mount_result != 0:
                log(f"Failed to mount {drive_path} with iso9660 or udf. Return code: {mount_result}")
                show_message(f"Failed to mount disc: Return code {mount_result}", title="Retrospin")
                return None
            else:
                log(f"Successfully mounted {drive_path} with udf")
        else:
            log(f"Successfully mounted {drive_path} with iso9660")
        
        # Look for system.cnf (case variations)
        system_cnf_variants = ["system.cnf", "SYSTEM.CNF", "System.cnf"]
        for root, dirs, files in os.walk(mount_point):
            # Try to get disc name from filesystem (volume label or directory)
            #try:
            #    disc_name = os.path.basename(root) if root != mount_point else None
            #    if not disc_name:
            #        # Try volume label via blkid
            #        result = subprocess.run(['blkid', drive_path], capture_output=True, text=True)
            #        match = re.search(r'LABEL="([^"]+)"', result.stdout)
            #        if match:
            #            disc_name = match.group(1)
            #except Exception as e:
            #    log(f"Error getting disc name: {e}")
            
            for variant in system_cnf_variants:
                if variant in files:
                    system_cnf_path = os.path.join(root, variant)
                    try:
                        with open(system_cnf_path, 'r', encoding='latin-1', errors='ignore') as f:
                            file_text = f.read()
                            log(f"Found {variant} at {system_cnf_path}")
                            for line in file_text.splitlines():
                                if "BOOT" in line.upper():
                                    raw_id = line.split("=")[1].strip().split("\\")[1].split(";")[0]
                                    game_serial = raw_id.replace(".", "").replace("_", "-")
                                    log(f"Extracted PSX Game Serial: {game_serial}")
                                    break
                    except Exception as e:
                        log(f"Error reading {system_cnf_path}: {e}")
                    if game_serial:
                        break
            if game_serial:
                break
        
        # Unmount immediately
        log(f"Unmounting {mount_point}...")
        os.system(f"umount -f {mount_point} 2>/dev/null")
        log(f"Unmounted {mount_point}")
        
        if not game_serial:
            log("system.cnf not found on disc (checked all case variations).")
            show_message("No system.cnf found on disc.", title="Retrospin")
        return game_serial
    except Exception as e:
        log(f"Error reading PSX disc: {e}")
        show_message(f"Error reading PSX disc: {str(e)}", title="Retrospin")
        return None
    finally:
        if is_mounted(drive_path, mount_point):
            log(f"Final cleanup: Forcing unmount of {mount_point}")
            os.system(f"umount -f {mount_point} 2>/dev/null")

def read_saturn_game_id(drive_path):
    """Read Saturn game serial from disc header (offset 0x20-0x2A)."""
    try:
        with open(drive_path, 'rb') as f:
            f.seek(0)  # Sector 0
            sector = f.read(2048)
            # Saturn: offset 0x20-0x2A (32-42)
            raw_id = sector[32:42].decode('ascii', errors='ignore').strip()
            print(f"Saturn raw serial: {repr(raw_id)}")
            # Match formats like T-12345, MK-81009, GS-9051
            match = re.match(r'^[A-Z0-9]+-[A-Z0-9]+$', raw_id)
            game_serial = raw_id if match else None
            # Validate serial
            if not game_serial or not re.match(r'^[A-Z0-9]+-[A-Z0-9]+$', game_serial):
                print("No valid Saturn serial found in disc header (invalid or empty).")
                return None
            print(f"Extracted Saturn Game Serial: {game_serial}")
            return game_serial
    except Exception as e:
        print(f"Error reading Saturn disc: {e}")
        return None

def read_mcd_game_id(drive_path):
    """Read Sega CD game serial from disc header (offset 0x180)."""
    try:
        with open(drive_path, 'rb') as f:
            f.seek(0)  # Sector 0
            sector = f.read(2048)
            # Sega CD: offset 0x180 (384-400)
            raw_id = sector[384:400].decode('ascii', errors='ignore').strip()
            print(f"Sega CD raw serial: {repr(raw_id)}")
            # Match formats like T-70065, GM-12345, or raw serials (e.g., 12345)
            match = re.match(r'^(?:GM|T-)?\s*([A-Z0-9-]+)(?:\s*-\d+)?\s*$', raw_id)
            game_serial = match.group(1) if match else None
            # Validate serial
            if not game_serial or not re.match(r'^[A-Z0-9-]+$', game_serial):
                print("No valid Sega CD serial found in disc header (invalid or empty).")
                return None
            print(f"Extracted Sega CD Game Serial: {game_serial}")
            return game_serial
    except Exception as e:
        print(f"Error reading Sega CD disc: {e}")
        return None
    
def read_disc():
    """Read the optical disc and return drive path, title, system, and serial."""
    drive_path = get_optical_drive()
    if not drive_path:
        return "none", "none", "none", "none"
    
    if not is_disc_present(drive_path):
        show_message("Testing disc... Please insert a disc if not already.", title="Retrospin")
        return drive_path, "none", "none", "none"
    
    show_message("Reading disc...", title="Retrospin", non_blocking=True)
    
    try:
        game_titles = load_game_titles()
    except Exception as e:
        log(f"Error loading game titles: {e}")
        show_message(f"Error loading database: {str(e)}", title="Retrospin")
        return drive_path, "none", "none", "none"
    
    # Try PSX only for now
    try:
        psx_game_serial, disc_name = read_psx_game_id(drive_path)
        if psx_game_serial:
            serial_key = psx_game_serial.replace("_", "").upper()
            matches = []
            for (db_serial, db_system), titles in game_titles.items():
                if db_system == "psx" and (db_serial == serial_key or db_serial.startswith(serial_key)):
                    matches.extend(titles)
            if matches:
                # Pick first match, log if multiple
                if len(matches) > 1:
                    log(f"Multiple matches for PSX serial {serial_key}: {[t[1] for t in matches]}. Using first: {matches[0][1]}")
                title = matches[0][1]
                if title and title != "Unknown Game":
                    show_message(f"Drive: {drive_path}\nTitle: {title}\nSystem: PSX\nSerial: {serial_key}", title="Retrospin")
                    return drive_path, title, "psx", serial_key
            else:
                # No database match, show serial and disc name
                show_message(f"Disc found but no database match.\nSerial: {serial_key}\nDisc Name: {disc_name}", title="Retrospin")
                return drive_path, "none", "none", serial_key
    except Exception as e:
        log(f"Error processing PSX disc: {e}")
        show_message(f"Error processing PSX disc: {str(e)}", title="Retrospin")
    
    show_message("No valid PSX disc detected.", title="Retrospin")
    return drive_path, "none", "none", "none"