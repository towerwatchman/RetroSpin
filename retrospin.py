#!/usr/bin/env python3

import argparse
import os
import platform
import subprocess
import sys
import logging
import signal
import time

# Platform-specific imports
if platform.system() == "Windows" or platform.system() == "Linux":
    import tkinter as tk
    from tkinter import messagebox, ttk

# Setup logging
logging.basicConfig(
    filename="/tmp/retrospin.log" if platform.system() != "Windows" else "retrospin.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def run_script(script_name, args, root=None):
    """Execute platform-specific script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    system_info = platform.uname()
    is_mister = system_info.system == "Linux" and "MiSTer" in system_info.release
    if is_mister:
        script_path = os.path.join(script_dir, f"{script_name}.sh")
        cmd = ["/bin/bash", script_path] + args
    else:
        script_path = os.path.join(script_dir, f"{script_name}.py")
        cmd = [sys.executable, script_path] + args
    if not os.path.exists(script_path):
        logging.error(f"Script not found: {script_path}")
        if is_mister:
            subprocess.run(
                ["dialog", "--msgbox", f"Error: {script_name} script not found", "10", "40"],
                stdin=open("/dev/tty2", "r"), stdout=open("/dev/tty2", "w"), check=False
            )
        else:
            messagebox.showerror("RetroSpin Error", f"{script_name} script not found")
        return
    logging.info(f"Running {script_path} with args: {args}")
    try:
        subprocess.run(cmd, check=True)
        if not is_mister and root:
            root.destroy()
    except subprocess.CalledProcessError as e:
        logging.error(f"Script {script_name} failed: {e}")
        if is_mister:
            subprocess.run(
                ["dialog", "--msgbox", f"Error running {script_name}: {e}", "10", "40"],
                stdin=open("/dev/tty2", "r"), stdout=open("/dev/tty2", "w"), check=False
            )
        else:
            messagebox.showerror("RetroSpin Error", f"Error running {script_name}: {e}")

def setup_mister_console():
    """Initialize MiSTer console."""
    console = "/dev/tty2"
    logging.info(f"Setting up console: {console}")
    if os.path.exists(console) and os.access(console, os.W_OK):
        try:
            with open(console, "w") as f:
                subprocess.run(["stty", "sane"], stdout=f, stderr=f, check=False)
                subprocess.run(["tput", "init"], stdout=f, stderr=f, check=False)
                f.write("\033[?25h")
            if os.path.exists("/sbin/chvt"):
                subprocess.run(["chvt", "2"], check=False)
        except Exception as e:
            logging.error(f"Failed to setup console: {e}")
    else:
        logging.error(f"Console {console} not accessible")

def kill_mister():
    """Kill MiSTer process."""
    logging.info("Checking for MiSTer process...")
    try:
        ps_output = subprocess.run(["ps", "aux"], capture_output=True, text=True, check=True).stdout
        for line in ps_output.splitlines():
            if "/media/fat/MiSTer" in line and "grep" not in line:
                pid = int(line.split()[1])
                logging.info(f"Killing MiSTer process with PID {pid}...")
                os.kill(pid, signal.SIGKILL)
                timeout = 5
                elapsed = 0
                while elapsed < timeout:
                    if not any("/media/fat/MiSTer" in l for l in subprocess.run(["ps", "aux"], capture_output=True, text=True).stdout.splitlines()):
                        logging.info("MiSTer process terminated")
                        return True
                    time.sleep(1)
                    elapsed += 1
                logging.error("Failed to terminate MiSTer process after 5 seconds")
                return False
        logging.info("No MiSTer process found")
        return True
    except Exception as e:
        logging.error(f"Failed to kill MiSTer: {e}")
        return False

def relaunch_mister():
    """Relaunch MiSTer process."""
    if os.path.exists("/media/fat/MiSTer"):
        logging.info("Relaunching MiSTer process...")
        try:
            subprocess.Popen(["/media/fat/MiSTer"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
            ps_output = subprocess.run(["ps", "aux"], capture_output=True, text=True, check=True).stdout
            if any("/media/fat/MiSTer" in line for line in ps_output.splitlines()):
                logging.info("MiSTer relaunched successfully")
                return True
            logging.error("Failed to relaunch MiSTer")
            return False
        except Exception as e:
            logging.error(f"Failed to relaunch MiSTer: {e}")
            return False
    return True

def windows_ui():
    """Launch tkinter UI for Windows/Linux."""
    root = tk.Tk()
    root.title("RetroSpin")
    root.geometry("300x200")

    tk.Label(root, text="RetroSpin Disc Manager", font=("Arial", 14)).pack(pady=10)

    def run_test():
        run_script("test_disc", ["D:"], root)

    def run_save():
        run_script("save_disc", ["D:", "TestGame", "ss"], root)

    def warn_service():
        messagebox.showwarning("RetroSpin", "Service mode is MiSTer-only")
        root.destroy()

    tk.Button(root, text="Test Disc", command=run_test, width=20).pack(pady=5)
    tk.Button(root, text="Save Disc", command=run_save, width=20).pack(pady=5)
    tk.Button(root, text="Run Service", command=warn_service, width=20, state="disabled").pack(pady=5)

    root.mainloop()

def mister_dialog():
    """Launch dialog menu for MiSTer."""
    if kill_mister():
        setup_mister_console()
        cmd = ["dialog", "--menu", "RetroSpin Disc Manager", "15", "40", "3",
               "1", "Test Disc",
               "2", "Save Disc",
               "3", "Run Service"]
        result = subprocess.run(
            cmd, stdin=open("/dev/tty2", "r"), stdout=subprocess.PIPE,
            stderr=open("/tmp/retrospin_dialog.err", "w"), text=True, check=False
        )
        choice = result.stdout.strip()
        if result.returncode == 0 and choice:
            if choice == "1":
                run_script("test_disc", ["/dev/sr0"])
            elif choice == "2":
                run_script("save_disc", ["/dev/sr0", "TestGame", "ss"])
            elif choice == "3":
                run_script("service", [])
        relaunch_mister()
    else:
        subprocess.run(
            ["dialog", "--msgbox", "Failed to stop MiSTer process", "10", "40"],
            stdin=open("/dev/tty2", "r"), stdout=open("/dev/tty2", "w"), check=False
        )
        relaunch_mister()

def main():
    parser = argparse.ArgumentParser(description="RetroSpin Disc Manager")
    parser.add_argument("--test", action="store_true", help="Test disc serial")
    parser.add_argument("--save", action="store_true", help="Save disc to .bin/.cue")
    parser.add_argument("--service", action="store_true", help="Run as background service")
    parser.add_argument("--drive", default="/dev/sr0" if platform.system() != "Windows" else "D:", help="CD drive path")
    parser.add_argument("--title", default="TestGame", help="Game title for save")
    parser.add_argument("--system", default="ss", choices=["psx", "ss", "mcd"], help="System type")
    args = parser.parse_args()

    system_info = platform.uname()
    is_mister = system_info.system == "Linux" and "MiSTer" in system_info.release

    if not (args.test or args.save or args.service):
        if is_mister:
            mister_dialog()
        else:
            windows_ui()
        return

    if is_mister and args.service:
        run_script("service", [])
    elif args.test:
        run_script("test_disc", [args.drive])
    elif args.save:
        run_script("save_disc", [args.drive, args.title, args.system])
    else:
        if is_mister:
            subprocess.run(
                ["dialog", "--msgbox", "Invalid option or service mode not supported", "10", "40"],
                stdin=open("/dev/tty2", "r"), stdout=open("/dev/tty2", "w"), check=False
            )
        else:
            messagebox.showerror("RetroSpin Error", "Invalid option")

if __name__ == "__main__":
    main()