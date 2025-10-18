import os
import subprocess
import sys
import time
from utilities.files import find_game_file
from utilities.disc import read_disc

script_dir = os.path.dirname(os.path.abspath(__file__))
script_path = os.path.join(script_dir,"functions", "save_disc.sh")

# Detect all storage devices (mounted and unmounted)
def get_mounted_devices():
    try:
        # List block devices of type disk or part, excluding loop and rom
        result = subprocess.run(
            "lsblk -ln -o NAME,TYPE,MOUNTPOINT | grep -E 'disk|part' | grep -vE 'loop|rom'",
            shell=True, capture_output=True, text=True, check=True
        )
        devices = []
        for line in result.stdout.strip().split('\n'):
            name, dev_type, mountpoint = line.split(maxsplit=2) if line.count(' ') >= 2 else (line.split()[0], line.split()[1], '')
            device = f"/dev/{name}"
            # Skip root filesystem and system mounts unless explicitly used later
            if mountpoint in ('/', '/boot', '/dev', '/proc', '/sys', '/run', '') and not mountpoint.startswith(('/media/', '/mnt/')):
                if dev_type in ('disk', 'part') and mountpoint == '':
                    # Unmounted device, propose a temporary mount point
                    temp_mount = f"/mnt/retrospin_tmp_{name}"
                    devices.append((device, temp_mount, False))
                continue
            devices.append((device, mountpoint, True))
        return devices
    except subprocess.CalledProcessError as e:
        with open('/tmp/retrospin_err.log', 'w') as f:
            f.write(f"Error detecting devices: {e.stderr}")
        print(f"Error detecting devices: {e.stderr}")
        return []

# Mount a device to a temporary mount point
def mount_device(device, temp_mount):
    try:
        os.makedirs(temp_mount, exist_ok=True)
        subprocess.run(f"mount {device} {temp_mount}", shell=True, check=True, stderr=subprocess.PIPE)
        return True
    except (subprocess.CalledProcessError, OSError) as e:
        with open('/tmp/retrospin_err.log', 'w') as f:
            f.write(f"Error mounting {device} to {temp_mount}: {str(e)}")
        print(f"Error mounting {device} to {temp_mount}: {str(e)}")
        return False

# Cleanup temporary mount points
def cleanup_mounts(mount_points):
    for mount in mount_points:
        if mount.startswith('/mnt/retrospin_tmp_'):
            subprocess.run(f"umount {mount} 2>/dev/null", shell=True)
            subprocess.run(f"rmdir {mount} 2>/dev/null", shell=True)

# Start "Reading Disc" infobox in the background
try:
    dialog_cmd = 'dialog --clear --backtitle "RetroSpin" --title "RetroSpin" --infobox "Reading Disc..." 10 40 2>&1 >/dev/tty'
    dialog_proc = subprocess.Popen(dialog_cmd, shell=True, stderr=subprocess.PIPE)
    dialog_pid = dialog_proc.pid
except Exception as e:
    with open('/tmp/retrospin_err.log', 'w') as f:
        f.write(f"Dialog error (Reading Disc): {str(e)}")
    print(f"Dialog error (Reading Disc): {str(e)}")
    sys.exit(1)

# Read disc information
try:
    drive_path, title, system, game_serial = read_disc()
except Exception as e:
    # Terminate Reading Disc dialog
    subprocess.run(f"kill {dialog_pid} 2>/dev/null", shell=True)
    subprocess.run("clear >/dev/tty 2>/dev/null", shell=True)
    with open('/tmp/retrospin_err.log', 'w') as f:
        f.write(f"Error reading disc: {str(e)}")
    try:
        subprocess.run(
            f'dialog --clear --backtitle "RetroSpin" --title "RetroSpin" --msgbox "Error reading disc: {str(e)}" 10 50 2>&1 >/dev/tty',
            shell=True, check=True, stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as dialog_e:
        with open('/tmp/retrospin_err.log', 'a') as f:
            f.write(f"\nDialog error (Disc Read Error): {dialog_e.stderr.decode()}")
        print(f"Dialog error (Disc Read Error): {dialog_e.stderr.decode()}")
    sys.exit(1)

# Terminate Reading Disc dialog
subprocess.run(f"kill {dialog_pid} 2>/dev/null", shell=True)
subprocess.run("clear >/dev/tty 2>/dev/null", shell=True)

# Check for storage devices
devices = get_mounted_devices()
if not devices:
    # No devices detected, prompt to use root filesystem
    try:
        result = subprocess.run(
            'dialog --clear --backtitle "RetroSpin" --title "RetroSpin" --yesno "No storage devices detected. Use the root filesystem (/games) to store games?" 10 50 2>&1 >/dev/tty',
            shell=True, capture_output=True, text=True, check=True
        )
        if result.returncode == 0:  # User selected Yes
            selected_mount = "/"
            device = "root"
            is_mounted = True
        else:  # User selected No
            try:
                subprocess.run(
                    'dialog --clear --backtitle "RetroSpin" --title "RetroSpin" --msgbox "No storage device selected. Exiting." 10 50 2>&1 >/dev/tty',
                    shell=True, check=True, stderr=subprocess.PIPE
                )
            except subprocess.CalledProcessError as e:
                with open('/tmp/retrospin_err.log', 'w') as f:
                    f.write(f"Dialog error (No Device Selected): {e.stderr.decode()}")
                print(f"Dialog error (No Device Selected): {e.stderr.decode()}")
            sys.exit(1)
    except subprocess.CalledProcessError as e:
        with open('/tmp/retrospin_err.log', 'w') as f:
            f.write(f"Dialog error (Root Filesystem Prompt): {e.stderr.decode()}")
        print(f"Dialog error (Root Filesystem Prompt): {e.stderr.decode()}")
        sys.exit(1)
else:
    # Create dialog menu for device selection
    menu_items = []
    for i, (device, mountpoint, is_mounted) in enumerate(devices, 1):
        display = mountpoint if is_mounted else f"{device} (unmounted)"
        menu_items.append(f"{i} {display}")
    menu_cmd = f'dialog --clear --backtitle "RetroSpin" --title "Select Storage Device" --menu "Choose a storage device:" 15 50 {len(devices)} {" ".join(menu_items)} 2>&1 >/dev/tty'
    try:
        result = subprocess.run(menu_cmd, shell=True, capture_output=True, text=True, check=True)
        selected_index = int(result.stdout.strip()) - 1
        device, selected_mount, is_mounted = devices[selected_index]
        if not is_mounted:
            # Prompt to mount unmounted device
            try:
                subprocess.run(
                    f'dialog --clear --backtitle "RetroSpin" --title "RetroSpin" --yesno "Mount {device} to {selected_mount}?" 10 50 2>&1 >/dev/tty',
                    shell=True, check=True, stderr=subprocess.PIPE
                )
                if not mount_device(device, selected_mount):
                    raise subprocess.CalledProcessError(1, "mount")
            except subprocess.CalledProcessError as e:
                with open('/tmp/retrospin_err.log', 'w') as f:
                    f.write(f"Dialog error or mount failed for {device}: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}")
                subprocess.run(
                    f'dialog --clear --backtitle "RetroSpin" --title "RetroSpin" --msgbox "Failed to mount {device}. Please try another device." 10 50 2>&1 >/dev/tty',
                    shell=True, stderr=subprocess.PIPE
                )
                cleanup_mounts([selected_mount])
                sys.exit(1)
    except subprocess.CalledProcessError as e:
        with open('/tmp/retrospin_err.log', 'w') as f:
            f.write(f"Dialog error (Device Selection): {e.stderr.decode()}")
        print(f"Dialog error (Device Selection): {e.stderr.decode()}")
        cleanup_mounts([mp for _, mp, _ in devices if mp.startswith('/mnt/retrospin_tmp_')])
        sys.exit(1)

# Check for existing game file
game_file = find_game_file(title, system)
if game_file:
    # Game file exists, show dialog with details
    message = f"Game file already exists for:\nTitle: {title}\nSystem: {system}\nSerial: {game_serial}\nFile: {game_file}"
    try:
        subprocess.run(
            f'dialog --clear --backtitle "RetroSpin" --title "RetroSpin" --msgbox "{message}" 12 60 2>&1 >/dev/tty',
            shell=True, check=True, stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        with open('/tmp/retrospin_err.log', 'w') as f:
            f.write(f"Dialog error (Game Exists): {e.stderr.decode()}")
        print(f"Dialog error (Game Exists): {e.stderr.decode()}")
    cleanup_mounts([mp for _, mp, _ in devices if mp.startswith('/mnt/retrospin_tmp_')])
    sys.exit(0)
else:
    if title != "Unknown Game":
        print(f"Game file not found for {title} ({game_serial}). Triggering save for matched {system} game.")
        save_cmd = f"{script_path} \"{drive_path}\" \"{title}\" {system} \"{selected_mount}\""
        print(f"Executing save command: {save_cmd}")
        try:
            subprocess.run(save_cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Save script failed: {e}")
            cleanup_mounts([mp for _, mp, _ in devices if mp.startswith('/mnt/retrospin_tmp_')])
            sys.exit(1)
    else:
        print(f"Game file not found for {title} ({game_serial}). Skipping save for unmatched {system} game.")
        cleanup_mounts([mp for _, mp, _ in devices if mp.startswith('/mnt/retrospin_tmp_')])
        sys.exit(0)

# Cleanup temporary mount points
cleanup_mounts([mp for _, mp, _ in devices if mp.startswith('/mnt/retrospin_tmp_')])