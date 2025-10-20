import subprocess
import time
import os
from evdev import UInput, ecodes as e

# Configurable disc device (change if /dev/sr0 is incorrect)
DISC_DEVICE = "/dev/sr0"

# Function to get current active TTY
def get_tty():
    sys_path = "/sys/devices/virtual/tty/tty0/active"
    if os.path.exists(sys_path):
        with open(sys_path, 'r') as f:
            return f.read().strip()
    raise FileNotFoundError("TTY active file not found")

# Function to simulate F9 key press using uinput
def send_f9():
    capabilities = {
        e.EV_KEY: [e.KEY_F9],
    }
    with UInput(capabilities, name='mister-virtual-kbd') as ui:
        ui.write(e.EV_KEY, e.KEY_F9, 1)  # Key down
        ui.syn()
        ui.write(e.EV_KEY, e.KEY_F9, 0)  # Key up
        ui.syn()

# Function to open console by simulating F9 (similar to Go code)
def open_console():
    subprocess.run(["chvt", "3"], check=True)
    
    tries = 0
    while True:
        if tries > 20:
            raise Exception("Could not switch to tty1")
        
        send_f9()
        time.sleep(0.05)
        
        tty = get_tty()
        if tty == "tty1":
            break
        
        tries += 1

# Function to check if /mnt/cdrom is mounted
def is_mounted():
    return subprocess.run(["mountpoint", "-q", "/mnt/cdrom"]).returncode == 0

# Function to get disc size
def get_disc_size():
    try:
        size_str = subprocess.check_output(
            ["blockdev", "--getsize64", DISC_DEVICE], stderr=subprocess.DEVNULL
        ).decode().strip()
        return int(size_str)
    except (subprocess.CalledProcessError, ValueError):
        return 0

# Function to check if mounted directory is empty
def is_directory_empty(path):
    try:
        return len(os.listdir(path)) == 0
    except OSError:
        return True  # Treat inaccessible directory as empty

# Main polling loop
def main():
    # Ensure /mnt/cdrom exists
    if not os.path.exists("/mnt/cdrom"):
        subprocess.run(["mkdir", "-p", "/mnt/cdrom"], check=True)
    
    console_opened = False
    mounted = False
    
    while True:
        size = get_disc_size()
        
        if size > 0:
            # Disc detected, open console if not already opened
            if not console_opened:
                try:
                    open_console()
                    console_opened = True
                    # Clear screen and show UI only after console is opened
                    os.system("clear")
                    print("MiSTer Disc Poller Started")
                    print("--------------------------")
                    print(f"Disc detected (size: {size} bytes)")
                except Exception as ex:
                    print(f"Error opening console: {ex}")
                    time.sleep(1)
                    continue
            
            # Handle mounting logic
            if not is_mounted():
                mount_result = subprocess.run(["mount", DISC_DEVICE, "/mnt/cdrom"])
                if mount_result.returncode == 0:
                    os.system("clear")
                    print("Disc mounted")
                    if is_directory_empty("/mnt/cdrom"):
                        print("Mounted disc is empty, unmounting...")
                        subprocess.run(["umount", "/mnt/cdrom"])
                        os.system("clear")
                        print("Waiting for new disc...")
                    else:
                        print("Disc loaded")
                        mounted = True
                else:
                    print("Failed to mount disc")
            elif is_mounted() and is_directory_empty("/mnt/cdrom"):
                print("Mounted disc is now empty, unmounting...")
                subprocess.run(["umount", "/mnt/cdrom"])
                mounted = False
                os.system("clear")
                print("Waiting for new disc...")
        else:
            # No disc detected
            if is_mounted():
                subprocess.run(["umount", "/mnt/cdrom"])
                mounted = False
                if console_opened:
                    os.system("clear")
                    print("Disc removed, waiting for new disc...")
            # Reset console_opened if no disc and not mounted
            if console_opened and not is_mounted():
                console_opened = False
        
        time.sleep(1)  # Poll every second

if __name__ == "__main__":
    # Note: This script requires root privileges. Run with sudo.
    # Ensure DISC_DEVICE is your disc drive device (default: /dev/sr0).
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping disc poller...")
        if is_mounted():
            subprocess.run(["umount", "/mnt/cdrom"])
        os.system("clear")