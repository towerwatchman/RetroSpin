import os
import sys
import time
import subprocess
import tempfile
import shutil
import re

# Add /retrospin to sys.path to ensure core package is found
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(os.path.dirname(script_dir)))

from core.utilities.disc import get_optical_drive, is_disc_present, read_saturn_game_id, read_mcd_game_id, read_psx_game_id
from core.utilities.database import load_game_titles
from core.utilities.ui import show_popup, select_game_title, show_yesno

def sanitize_filename(title):
    """Sanitize title to be safe for filenames."""
    # Replace invalid characters with underscores
    title = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', title)
    # Remove leading/trailing whitespace and periods
    title = title.strip().strip('.')
    # Replace multiple spaces with single underscore
    title = re.sub(r'\s+', '_', title)
    # Ensure non-empty filename
    return title or "unknown_game"

def read_disc():
    """Read the optical disc and return drive path, title, and system."""
    # Show "Reading disc..." dialog gauge
    gauge_process = subprocess.Popen(
        ['dialog', '--gauge', 'RetroSpin\nReading disc...', '10', '50', '0'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    drive_path = get_optical_drive()
    if not drive_path or not is_disc_present(drive_path):
        gauge_process.stdin.write("XXX\n100\nRetroSpin\nNo disc detected\nXXX\n")
        gauge_process.stdin.flush()
        gauge_process.stdin.close()
        gauge_process.wait()
        return drive_path or "none", "none", "none"
    
    try:
        game_titles = load_game_titles()
    except Exception as e:
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - save_disc.py: Failed to load game titles: {e}\n")
        gauge_process.stdin.write("XXX\n100\nRetroSpin\nFailed to load database\nXXX\n")
        gauge_process.stdin.flush()
        gauge_process.stdin.close()
        gauge_process.wait()
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
                    gauge_process.stdin.write("XXX\n100\nRetroSpin\nDisc read complete\nXXX\n")
                    gauge_process.stdin.flush()
                    gauge_process.stdin.close()
                    gauge_process.wait()
                    return drive_path, title, "ss"
    except Exception as e:
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - save_disc.py: Failed to read Saturn game: {e}\n")
    
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
                    gauge_process.stdin.write("XXX\n100\nRetroSpin\nDisc read complete\nXXX\n")
                    gauge_process.stdin.flush()
                    gauge_process.stdin.close()
                    gauge_process.wait()
                    return drive_path, title, "mcd"
    except Exception as e:
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - save_disc.py: Failed to read Mega CD game: {e}\n")
    
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
                    gauge_process.stdin.write("XXX\n100\nRetroSpin\nDisc read complete\nXXX\n")
                    gauge_process.stdin.flush()
                    gauge_process.stdin.close()
                    gauge_process.wait()
                    return drive_path, title, "psx"
    except Exception as e:
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - save_disc.py: Failed to read PSX game: {e}\n")
    
    gauge_process.stdin.write("XXX\n100\nRetroSpin\nNo supported disc detected\nXXX\n")
    gauge_process.stdin.flush()
    gauge_process.stdin.close()
    gauge_process.wait()
    return drive_path, "none", "none"

def save_disc():
    """Save a disc to .bin/.cue format."""
    ripdisc_path = "/media/fat/_Utility"
    output_base_dir = "/media/usb0/games"

    # Read disc information
    drive, title, system = read_disc()

    # Check if disc is valid
    if title == "none" or system == "none":
        show_popup("RetroSpin\nError: No supported disc detected or no database match")
        return 1

    # Sanitize title for filename
    title = sanitize_filename(title)

    # Check ripdisc_path
    cdrdao = os.path.join(ripdisc_path, "cdrdao")
    toc2cue = os.path.join(ripdisc_path, "toc2cue")
    if not (os.path.isdir(ripdisc_path) and os.access(cdrdao, os.X_OK) and os.access(toc2cue, os.X_OK)):
        cdrdao = shutil.which("cdrdao")
        toc2cue = shutil.which("toc2cue")
        if not (cdrdao and toc2cue):
            show_popup(f"RetroSpin\nError: Utility binaries (cdrdao, toc2cue) not found in {ripdisc_path} or system PATH")
            return 1

    # Check output_base_dir
    if not os.path.isdir(output_base_dir):
        output_base_dir = "/usr/games"

    # Set output directory based on system
    system_dirs = {"psx": "PSX", "ss": "Saturn", "mcd": "MegaCD"}
    output_dir = os.path.join(output_base_dir, system_dirs.get(system, ""))
    try:
        os.makedirs(output_dir, exist_ok=True)
        os.system(f"chown mister:mister {output_dir}")
        os.system(f"chmod 775 {output_dir}")
    except OSError as e:
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - save_disc.py: Failed to create output directory {output_dir}: {e}\n")
        show_popup(f"RetroSpin\nError: Cannot create output directory {output_dir}")
        return 1

    cue_file = os.path.join(output_dir, f"{title}.cue")
    bin_file = os.path.join(output_dir, f"{title}.bin")

    # Remove existing files
    for f in [cue_file, bin_file]:
        if os.path.exists(f):
            os.remove(f)

    # Prompt user with title, location, and system on separate lines
    prompt_message = f"RetroSpin\nTitle: {title}\nLocation: {output_dir}\nSystem: {system}\nSave disc?"
    if not show_yesno(prompt_message):
        return 1

    # Show "Preparing to save..." dialog gauge
    gauge_process = subprocess.Popen(
        ['dialog', '--gauge', 'RetroSpin\nPreparing to save...', '10', '50', '0'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Save disc
    with tempfile.NamedTemporaryFile(suffix=".toc", delete=False) as toc_file:
        toc_path = toc_file.name
        # Ensure TOC file doesn't exist
        if os.path.exists(toc_path):
            os.remove(toc_path)
    try:
        subprocess.run(
            [cdrdao, "read-cd", "--read-raw", "--speed", "max", "--datafile", bin_file, "--device", drive, "--driver", "generic-mmc-raw", toc_path],
            check=True, capture_output=True, text=True
        )
        gauge_process.stdin.write("XXX\n50\nRetroSpin\nSaving disc...\nXXX\n")
        gauge_process.stdin.flush()
    except subprocess.CalledProcessError as e:
        gauge_process.stdin.write("XXX\n100\nRetroSpin\nFailed to read disc\nXXX\n")
        gauge_process.stdin.flush()
        gauge_process.stdin.close()
        gauge_process.wait()
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - save_disc.py: Failed to run cdrdao: {e}\nCommand: {e.cmd}\nOutput: {e.stderr}\n")
        show_popup("RetroSpin\nFailed to read disc")
        os.remove(toc_path)
        if os.path.exists(bin_file):
            os.remove(bin_file)
        return 1

    try:
        subprocess.run([toc2cue, toc_path, cue_file], check=True, capture_output=True, text=True)
        gauge_process.stdin.write("XXX\n100\nRetroSpin\nDisc saved successfully\nXXX\n")
        gauge_process.stdin.flush()
    except subprocess.CalledProcessError as e:
        gauge_process.stdin.write("XXX\n100\nRetroSpin\nFailed to create .cue file\nXXX\n")
        gauge_process.stdin.flush()
        gauge_process.stdin.close()
        gauge_process.wait()
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - save_disc.py: Failed to run toc2cue: {e}\nCommand: {e.cmd}\nOutput: {e.stderr}\n")
        show_popup("RetroSpin\nFailed to create .cue file")
        os.remove(toc_path)
        if os.path.exists(bin_file):
            os.remove(bin_file)
        return 1

    gauge_process.stdin.close()
    gauge_process.wait()

    os.remove(toc_path)
    with open(cue_file, "r") as f:
        cue_content = f.read()
    with open(cue_file, "w") as f:
        f.write(cue_content.replace(os.path.basename(bin_file), f"{title}.bin"))
    
    show_popup(f"RetroSpin\nDisc saved successfully to {cue_file}")
    return 0

if __name__ == "__main__":
    sys.exit(save_disc())