import subprocess
import time
import os
from evdev import UInput, ecodes as e

class Keyboard:
    def __init__(self):
        """Initialize a virtual keyboard device, similar to NewKeyboard in keyboard.go."""
        capabilities = {
            e.EV_KEY: [e.KEY_F9, e.KEY_F12],  # Register F9 and F12
        }
        try:
            self.device = UInput(capabilities, name='mrext', version=1)
        except Exception as ex:
            raise Exception(f"Failed to create virtual keyboard: {ex}")

    def close(self):
        """Close the virtual keyboard device, similar to Close in keyboard.go."""
        if hasattr(self, 'device'):
            self.device.close()

    def press(self, key):
        """Simulate a key press and release, similar to Press in keyboard.go."""
        self.device.write(e.EV_KEY, key, 1)  # Key down
        self.device.syn()
        time.sleep(0.04)  # 40ms delay, matching sleepTime in keyboard.go
        self.device.write(e.EV_KEY, key, 0)  # Key up
        self.device.syn()

    def console(self):
        """Simulate F9 key press to open console, similar to Console in keyboard.go."""
        self.press(e.KEY_F9)

    def exit_console(self):
        """Simulate F12 key press to exit console, similar to ExitConsole in keyboard.go."""
        self.press(e.KEY_F12)

def get_tty():
    """Get the current active TTY, similar to getTty in scripts.go."""
    sys_path = "/sys/devices/virtual/tty/tty0/active"
    if os.path.exists(sys_path):
        with open(sys_path, 'r') as f:
            return f.read().strip()
    raise FileNotFoundError("TTY active file not found")

def open_console(kbd):
    """Open the console by simulating F9, wait 5 seconds, then F12, similar to OpenConsole in scripts.go."""
    try:
        subprocess.run(["chvt", "3"], check=True)
    except subprocess.CalledProcessError as ex:
        raise Exception(f"Failed to switch to tty3: {ex}")

    tries = 0
    while True:
        if tries > 20:
            raise Exception("Could not switch to tty1")
        
        kbd.console()
        time.sleep(0.05)  # 50ms delay, matching scripts.go
        tty = get_tty()
        if tty == "tty1":
            break
        tries += 1
    
    # Wait 5 seconds and press F12
    print("Waiting 5 seconds before sending F12...")
    time.sleep(5)
    kbd.exit_console()

def main():
    """Test the Keyboard class with F9 and F12 simulation."""
    print("Initializing virtual keyboard...")
    try:
        kbd = Keyboard()
    except Exception as ex:
        print(f"Error: {ex}")
        return

    try:
        print("Attempting to open console (F9 simulation)...")
        open_console(kbd)
        print("Successfully switched to tty1")
        print(f"Current TTY: {get_tty()}")
    except Exception as ex:
        print(f"Error opening console: {ex}")
    finally:
        kbd.close()
        print("Virtual keyboard closed")

if __name__ == "__main__":
    # Note: This script requires root privileges for /dev/uinput and chvt.
    try:
        main()
    except KeyboardInterrupt:
        print("\nTest aborted")