import os
from pathlib import Path
import subprocess
import re
import time
from core.utilities.ui import show_message, yes_no_prompt, show_progress

CDRDAO_PATH = "/media/fat/_Utility/cdrdao"
TOC2CUE_PATH = "/media/fat/_Utility/toc2cue"
TEMP_LOG = "/tmp/retrospin_cdrdao.log"
TOC_FILE = "/tmp/retrospin_temp.toc"

def get_usb_drive():
    """Find a mounted USB drive."""
    try:
        result = subprocess.run(["lsblk", "-o", "NAME,MOUNTPOINT"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "/media/usb" in line:
                parts = line.split()
                return f"/media/{parts[1]}"
        return None
    except:
        return None

def get_disc_size_toc(drive_path):
    """
    Estimate disc size from TOC using cdrdao.
    Falls back to blockdev, then 700MB.
    Returns size in bytes (int).
    """
    # Ensure temp directory exists
    Path("/tmp").mkdir(exist_ok=True)

    # Clean up any existing TOC/log files to prevent cdrdao overwrite error
    for path in [TOC_FILE, TEMP_LOG]:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception as e:
            print(f"Warning: Could not delete {path}: {e}")

    print(f"Reading TOC data to detect disc size, logging to {TEMP_LOG}...")

    # Run cdrdao
    try:
        result = subprocess.run(
            ["cdrdao", "read-toc", "--device", drive_path, TOC_FILE],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=60
        )
        output = result.stdout
        cdrdao_status = result.returncode

        # Save log and print (tee behavior)
        with open(TEMP_LOG, "w") as lf:
            lf.write(output)
        print(output)

    except subprocess.TimeoutExpired:
        print("cdrdao command timed out.")
        output = ""
        cdrdao_status = 1
    except FileNotFoundError:
        print("cdrdao not found in PATH. Is it installed?")
        output = ""
        cdrdao_status = 1
    except Exception as e:
        print(f"cdrdao execution failed: {e}")
        output = ""
        cdrdao_status = 1

    disc_size = None

    # === 1. Parse Leadout from log ===
    if os.path.exists(TEMP_LOG):
        try:
            with open(TEMP_LOG, "r") as f:
                log_content = f.read()
            match = re.search(r"Leadout.*?\((\d+)\)", log_content)
            if match:
                disc_sectors = int(match.group(1))
                if disc_sectors > 0:
                    disc_size = disc_sectors * 2352
                    print(f"Disc size detected via TOC: {disc_size:,} bytes ({disc_sectors} sectors)")
        except Exception as e:
            print(f"Failed to read or parse {TEMP_LOG}: {e}")

    # === 2. Fallback: blockdev ===
    if disc_size is None:
        print("TOC parsing failed, falling back to blockdev...")
        try:
            blockdev_output = subprocess.check_output(
                ["blockdev", "--getsize64", drive_path],
                text=True
            ).strip()
            disc_size = int(blockdev_output)
            if disc_size > 0:
                print(f"Disc size via blockdev: {disc_size:,} bytes")
        except Exception as e:
            print(f"blockdev failed: {e}")

    # === 3. Final fallback: 700 MB ===
    if disc_size is None or disc_size <= 0:
        disc_size = 700 * 1024 * 1024
        print(f"Using fallback size: {disc_size:,} bytes (700 MB)")

    return disc_size  # Always returns a valid int
def rip_disc(drive_path, title, system, gauge_proc):
    """Rip disc to .bin/.cue using cdrdao and toc2cue."""
    usb_path = get_usb_drive()
    if not usb_path:
        show_message("No USB drive found.", title="Retrospin")
        return
    save_path = os.path.join(usb_path, "games", system.upper())
    os.makedirs(save_path, exist_ok=True)
    bin_file = os.path.join(save_path, f"{title}.bin")
    cue_file = os.path.join(save_path, f"{title}.cue")

    # Simulate progress (replace with cdrdao output parsing if needed)
    for i in range(0, 101, 10):
        gauge_proc.stdin.write(f"XXX\n{i}\nRipping {title}...\nXXX\n".encode())
        gauge_proc.stdin.flush()
        if i == 0:
            subprocess.run([CDRDAO_PATH, "read-toc", "--device", drive_path, TOC_FILE], check=True)
        elif i == 50:
            subprocess.run([CDRDAO_PATH, "read-cd", "--datafile", bin_file, "--driver", "generic-mmc-raw", "--read-raw", TOC_FILE], check=True)
        elif i == 90:
            subprocess.run([TOC2CUE_PATH, TOC_FILE, cue_file], check=True)
        time.sleep(1)  # Simulate work
    #os.remove(TOC_FILE)

def save_disc(drive_path, title, system, serial):
    """Prompt to save disc and rip to USB."""
    info = f"Title: {title}\nSystem: {system}\nSerial: {serial}"
    show_message(info, title="Retrospin")
    if yes_no_prompt("Save this disc?", title="Retrospin"):
        size_bytes = get_disc_size_toc(drive_path)
        size_mb = size_bytes / (1024 * 1024)  # Convert to MB
        est_time = f"Estimated time: {int(size_mb / 10)} minutes (at 10MB/s)"
        show_message(est_time, title="Retrospin")
        show_progress("Ripping disc...", lambda proc: rip_disc(drive_path, title, system, proc))
        show_message("Disc saved successfully.", title="Retrospin")