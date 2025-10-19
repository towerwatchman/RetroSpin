import os
import subprocess
import re
import time
from core.utilities.ui import show_message, yes_no_prompt, show_progress

CDRDAO_PATH = "/media/fat/_Utility/cdrdao"
TOC2CUE_PATH = "/media/fat/_Utility/toc2cue"

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
    """Estimate disc size from TOC for ripping time calculation."""
    toc_file = "/tmp/disc.toc"
    try:
        subprocess.run([CDRDAO_PATH, "read-toc", "--device", drive_path, toc_file], check=True)
        with open(toc_file, "r") as f:
            content = f.read()
        match = re.search(r"Total length: (\d+):(\d+):(\d+)", content)
        if match:
            minutes, seconds, frames = map(int, match.groups())
            total_sectors = (minutes * 60 + seconds) * 75 + frames
            size_mb = total_sectors * 2352 / (1024 * 1024)
            return size_mb
        return 650  # Default estimate
    except:
        return 650

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
    toc_file = "/tmp/disc.toc"

    # Simulate progress (replace with cdrdao output parsing if needed)
    for i in range(0, 101, 10):
        gauge_proc.stdin.write(f"XXX\n{i}\nRipping {title}...\nXXX\n".encode())
        gauge_proc.stdin.flush()
        if i == 0:
            subprocess.run([CDRDAO_PATH, "read-toc", "--device", drive_path, toc_file], check=True)
        elif i == 50:
            subprocess.run([CDRDAO_PATH, "read-cd", "--datafile", bin_file, "--driver", "generic-mmc-raw", "--read-raw", toc_file], check=True)
        elif i == 90:
            subprocess.run([TOC2CUE_PATH, toc_file, cue_file], check=True)
        time.sleep(1)  # Simulate work
    os.remove(toc_file)

def save_disc(drive_path, title, system, serial):
    """Prompt to save disc and rip to USB."""
    info = f"Title: {title}\nSystem: {system}\nSerial: {serial}"
    show_message(info, title="Retrospin")
    if yes_no_prompt("Save this disc?", title="Retrospin"):
        size_mb = get_disc_size_toc(drive_path)
        est_time = f"Estimated time: {int(size_mb / 10)} minutes (at 10MB/s)"
        show_message(est_time, title="Retrospin")
        show_progress("Ripping disc...", lambda proc: rip_disc(drive_path, title, system, proc))
        show_message("Disc saved successfully.", title="Retrospin")