import os
import re
import subprocess

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

def is_disc_present(drive_path):
    """Check if a disc is present in the drive."""
    try:
        with open(drive_path, 'rb') as f:
            f.read(1)  # Try reading a byte to check if disc is accessible
        return True
    except Exception as e:
        print(f"No disc detected in {drive_path}: {e}")
        return False

def read_psx_game_id(drive_path):
    """Read PSX game serial from system.cnf on physical disc, minimizing drive activity."""
    mount_point = "/mnt/cdrom"
    try:
        # Ensure mount point is clean
        os.system(f"umount {mount_point} 2>/dev/null")
        if not os.path.exists(mount_point):
            os.makedirs(mount_point)
        
        # Try mounting as ISO9660
        mount_cmd = f"mount {drive_path} {mount_point} -t iso9660 -o ro"
        mount_result = os.system(mount_cmd)
        if mount_result != 0:
            print(f"PSX iso9660 mount failed. Trying udf...")
            mount_cmd = f"mount {drive_path} {mount_point} -t udf -o ro"
            mount_result = os.system(mount_cmd)
            if mount_result != 0:
                print(f"Failed to mount {drive_path} with iso9660 or udf. Return code: {mount_result}")
                os.system(f"umount {mount_point} 2>/dev/null")
                return None
            else:
                print(f"Successfully mounted {drive_path} with udf")
        else:
            print(f"Successfully mounted {drive_path} with iso9660")
        
        system_cnf_variants = ["system.cnf", "SYSTEM.CNF", "System.cnf"]
        game_serial = None
        for root, dirs, files in os.walk(mount_point):
            for variant in system_cnf_variants:
                if variant in files:
                    system_cnf_path = os.path.join(root, variant)
                    try:
                        with open(system_cnf_path, 'r', encoding='latin-1', errors='ignore') as f:
                            file_text = f.read()
                            print(f"Found {variant} at {system_cnf_path}")
                            for line in file_text.splitlines():
                                if "BOOT" in line.upper():
                                    raw_id = line.split("=")[1].strip().split("\\")[1].split(";")[0]
                                    game_serial = raw_id.replace(".", "").replace("_", "-")
                                    print(f"Extracted PSX Game Serial: {game_serial}")
                                    break
                    except Exception as e:
                        print(f"Error reading {system_cnf_path}: {e}")
                    if game_serial:
                        break
            if game_serial:
                break
        
        # Unmount immediately
        os.system(f"umount {mount_point} 2>/dev/null")
        print(f"Unmounted {mount_point}")
        
        if not game_serial:
            print("system.cnf not found on disc (checked all case variations).")
        return game_serial
    except Exception as e:
        print(f"Error reading PSX disc: {e}")
        os.system(f"umount {mount_point} 2>/dev/null")
        return None
    finally:
        os.system(f"umount {mount_point} 2>/dev/null")  # Ensure cleanup

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