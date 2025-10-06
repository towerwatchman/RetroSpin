import os
import ctypes
from ctypes import wintypes
import sqlite3

# Windows-specific imports for low-level disc access
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

# Drive types
DRIVE_CDROM = 5

def get_optical_drives():
    """Get a list of optical drive letters."""
    drive_bits = kernel32.GetLogicalDrives()
    drives = []
    
    for i in range(26):  # A-Z
        if drive_bits & (1 << i):
            drive_letter = chr(65 + i)
            drive_path = f"{drive_letter}:\\"
            if kernel32.GetDriveTypeW(drive_path) == DRIVE_CDROM:
                drives.append(drive_letter)
    
    return drives

def get_drive_handle(drive_letter):
    """Get a handle to the optical drive for raw reading."""
    drive_path = f"\\\\.\\{drive_letter}:"
    handle = kernel32.CreateFileW(
        drive_path,
        wintypes.DWORD(0x80000000),  # GENERIC_READ
        wintypes.DWORD(0x00000001 | 0x00000002),  # FILE_SHARE_READ | FILE_SHARE_WRITE
        None,
        wintypes.DWORD(3),  # OPEN_EXISTING
        wintypes.DWORD(0),
        None
    )
    
    if handle == -1:
        raise ctypes.WinError(ctypes.get_last_error())
    return handle

def read_raw_disc(handle, offset, length):
    """Read raw data from the disc at the specified offset."""
    buffer = ctypes.create_string_buffer(length)
    bytes_read = wintypes.DWORD()
    
    kernel32.SetFilePointer(handle, offset, None, 0)  # FILE_BEGIN
    
    success = kernel32.ReadFile(
        handle,
        buffer,
        length,
        ctypes.byref(bytes_read),
        None
    )
    
    if not success:
        raise ctypes.WinError(ctypes.get_last_error())
    
    return buffer.raw[:bytes_read.value]

def read_system_cnf_filesystem(drive_letter):
    """Try reading SYSTEM.CNF directly from the filesystem."""
    file_path = f"{drive_letter}:\\SYSTEM.CNF"
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='latin-1') as f:
                file_text = f.read()
                print(f"Found SYSTEM.CNF at {file_path}")
                print("SYSTEM.CNF contents preview:")
                print(file_text[:200])
                return file_text
        else:
            print(f"SYSTEM.CNF not found at {file_path}")
            return None
    except Exception as e:
        print(f"Error reading SYSTEM.CNF from filesystem: {e}")
        return None

def read_system_cnf_sectors(drive_letter):
    """Fallback to reading SYSTEM.CNF by scanning sectors."""
    try:
        handle = get_drive_handle(drive_letter)
        sector_size = 2048
        max_sectors = 20000
        search_string = b"SYSTEM.CNF"
        
        for sector in range(16, max_sectors):
            offset = sector * sector_size
            buffer = read_raw_disc(handle, offset, sector_size)
            
            if search_string in buffer:
                print(f"Found SYSTEM.CNF reference at sector {sector}")
                file_offset = offset
                file_data = read_raw_disc(handle, file_offset, sector_size * 20)  # 40KB
                file_text = file_data.decode('latin-1', errors='ignore')
                print("SYSTEM.CNF contents preview:")
                print(file_text[:200])
                return file_text
        
        print(f"Scanned {max_sectors} sectors; SYSTEM.CNF not found.")
        return None
    
    except Exception as e:
        print(f"Error reading drive {drive_letter} sectors: {e}")
        return None
    
    finally:
        if 'handle' in locals():
            kernel32.CloseHandle(handle)

def get_psx_id_from_disc(drive_letter):
    """Extract PS1 game ID from SYSTEM.CNF, trying filesystem first then sectors."""
    valid_prefixes = ("SLUS", "SLES", "SCES", "SLPS", "SCPS", "SCUS")
    
    # Try filesystem first
    file_text = read_system_cnf_filesystem(drive_letter)
    if not file_text:
        print("Falling back to sector-by-sector reading...")
        file_text = read_system_cnf_sectors(drive_letter)
    
    if file_text:
        for line in file_text.splitlines():
            line = line.strip()
            print(f"Processing line: '{line}'")
            if "BOOT" in line.upper():
                raw_id = line.split("=")[1].strip().split("\\")[1].split(";")[0]
                game_id = raw_id.replace("_", "-").replace(".", "")
                print(f"Raw game ID from SYSTEM.CNF: {raw_id}")
                print(f"Normalized game ID: {game_id}")
                if any(game_id.startswith(prefix) for prefix in valid_prefixes):
                    return game_id
                else:
                    print(f"Invalid PS1 ID format: {game_id}")
                    return None
        print("No line containing 'BOOT' found in SYSTEM.CNF.")
        return None
    else:
        return None

def find_ps1_disc():
    """Find the first optical drive with a PS1 disc."""
    optical_drives = get_optical_drives()
    
    if not optical_drives:
        print("No optical drives detected.")
        return None, None
    
    print(f"Detected optical drives: {', '.join(optical_drives)}")
    
    for drive in optical_drives:
        print(f"Checking drive {drive} for a PS1 disc...")
        game_id = get_psx_id_from_disc(drive)
        if game_id:
            return drive, game_id
    
    print("No PS1 discs found.")
    return None, None

def lookup_game(game_id):
    """Look up game details in the games.db database."""
    conn = sqlite3.connect("games.db")
    cursor = conn.cursor()
    cursor.execute("SELECT title, region, system FROM games WHERE game_id = ?", (game_id,))
    result = cursor.fetchone()
    conn.close()
    return result if result else (None, None, None)

def main():
    print("Scanning for PS1 discs in all optical drives...")
    
    drive_letter, game_id = find_ps1_disc()
    
    if game_id:
        print(f"\nFound PS1 disc in drive {drive_letter}")
        print(f"Game ID: {game_id}")
        
        # Match against database
        title, region, system = lookup_game(game_id)
        if title:
            print(f"Game Title: {title}")
            print(f"Region: {region}")
            print(f"System: {system}")
          
        else:
            print("Game not found in database.")
    else:
        print("\nFailed to identify any PS1 disc. Possible causes:")
        print("- No disc inserted in an optical drive")
        print("- Non-PS1 disc or damaged disc")
        print("- Optical drive not compatible or not detected")

if __name__ == "__main__":
    main()