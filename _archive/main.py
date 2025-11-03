#!/usr/bin/env python3

import argparse
import os
import platform
import subprocess
import sys
import logging
import signal
import time

# Setup logging
logging.basicConfig(
    filename="/tmp/retrospin.log" if platform.system() != "Windows" else "retrospin.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def get_console_env(var_name, default):
    """Get console path from environment variable or use default."""
    return os.environ.get(var_name, default)

def run_script(script_name, args, root=None):
    """Execute platform-specific script."""
    logging.info("Entering run_script")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    system_info = platform.uname()
    is_mister = system_info.system == "Linux" and "MiSTer" in system_info.release
    logging.info(f"System info: {system_info}, is_mister: {is_mister}")
    if is_mister:
        script_path = os.path.join(script_dir, f"{script_name}.sh")
        cmd = ["/bin/bash", script_path] + args
    else:
        script_path = os.path.join(script_dir, f"{script_name}.py")
        cmd = [sys.executable, script_path] + args
    logging.info(f"Script path: {script_path}")
    if not os.path.exists(script_path):
        logging.error(f"Script not found: {script_path}")
        if is_mister:
            frontend_console = get_console_env("RETROSPIN_FRONTEND_CONSOLE", "/dev/tty2")
            logging.info(f"Using frontend console for error dialog: {frontend_console}")
            try:
                subprocess.run(
                    ["dialog", "--msgbox", f"Error: {script_name} script not found", "10", "40"],
                    stdin=open(frontend_console, "r"), stdout=open(frontend_console, "w"), check=False
                )
            except Exception as e:
                logging.error(f"Failed to run error dialog: {e}")
        else:
            # Fallback to print if no GUI
            print(f"Error: {script_name} script not found")
        return
    logging.info(f"Running {script_path} with args: {args}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info(f"Script {script_name} completed successfully")
        if not is_mister and root:
            root.destroy()
    except subprocess.CalledProcessError as e:
        logging.error(f"Script {script_name} failed: {e}, stdout: {e.stdout}, stderr: {e.stderr}")
        if is_mister:
            frontend_console = get_console_env("RETROSPIN_FRONTEND_CONSOLE", "/dev/tty2")
            logging.info(f"Using frontend console for error dialog: {frontend_console}")
            try:
                subprocess.run(
                    ["dialog", "--msgbox", f"Error running {script_name}: {e}", "10", "40"],
                    stdin=open(frontend_console, "r"), stdout=open(frontend_console, "w"), check=False
                )
            except Exception as dialog_e:
                logging.error(f"Failed to run error dialog: {dialog_e}")
        else:
            # Fallback to print if no GUI
            print(f"Error running {script_name}: {e}")
    logging.info("Exiting run_script")

def setup_mister_console():
    """Initialize MiSTer console."""
    logging.info("Entering setup_mister_console")
    frontend_console = get_console_env("RETROSPIN_FRONTEND_CONSOLE", "/dev/tty2")
    logging.info(f"Setting up console: {frontend_console}")
    if os.path.exists(frontend_console) and os.access(frontend_console, os.W_OK):
        try:
            with open(frontend_console, "w") as f:
                logging.info("Running stty sane")
                subprocess.run(["stty", "sane"], stdout=f, stderr=f, check=False)
                logging.info("Running tput init")
                subprocess.run(["tput", "init"], stdout=f, stderr=f, check=False)
                f.write("\033[?25h")
                f.flush()
            if os.path.exists("/sbin/chvt"):
                # Extract tty number from console path, e.g., /dev/tty2 -> 2
                tty_num = frontend_console.split('/')[-1].replace('tty', '')
                logging.info(f"Switching to tty {tty_num}")
                subprocess.run(["chvt", tty_num], check=False)
            logging.info("Console setup completed successfully")
        except Exception as e:
            logging.error(f"Failed to setup console: {e}")
    else:
        logging.error(f"Console {frontend_console} not accessible")
    logging.info("Exiting setup_mister_console")

def kill_mister():
    """Kill MiSTer process."""
    logging.info("Entering kill_mister")
    logging.info("Checking for MiSTer process...")
    try:
        ps_output = subprocess.run(["ps", "aux"], capture_output=True, text=True, check=True).stdout
        logging.info(f"PS output length: {len(ps_output)}")
        mister_pids = []
        for line in ps_output.splitlines():
            if "/media/fat/MiSTer" in line and "grep" not in line:
                pid = int(line.split()[1])
                mister_pids.append(pid)
                logging.info(f"Found MiSTer process with PID {pid}: {line}")
        if mister_pids:
            for pid in mister_pids:
                logging.info(f"Killing MiSTer process with PID {pid}...")
                os.kill(pid, signal.SIGKILL)
                timeout = 5
                elapsed = 0
                while elapsed < timeout:
                    current_ps = subprocess.run(["ps", "aux"], capture_output=True, text=True).stdout
                    if not any("/media/fat/MiSTer" in l for l in current_ps.splitlines()):
                        logging.info("MiSTer process terminated")
                        break
                    time.sleep(1)
                    elapsed += 1
                else:
                    logging.error("Failed to terminate MiSTer process after 5 seconds")
                    return False
        else:
            logging.info("No MiSTer process found")
        logging.info("Exiting kill_mister: True")
        return True
    except Exception as e:
        logging.error(f"Failed to kill MiSTer: {e}")
        logging.info("Exiting kill_mister: False")
        return False

def relaunch_mister():
    """Relaunch MiSTer process."""
    logging.info("Entering relaunch_mister")
    if os.path.exists("/media/fat/MiSTer"):
        logging.info("Relaunching MiSTer process...")
        try:
            proc = subprocess.Popen(["/media/fat/MiSTer"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logging.info(f"Started MiSTer with PID {proc.pid}")
            time.sleep(2)
            ps_output = subprocess.run(["ps", "aux"], capture_output=True, text=True, check=True).stdout
            if any("/media/fat/MiSTer" in line for line in ps_output.splitlines()):
                logging.info("MiSTer relaunched successfully")
                logging.info("Exiting relaunch_mister: True")
                return True
            else:
                logging.error("Failed to relaunch MiSTer - not found in PS")
                logging.info("Exiting relaunch_mister: False")
                return False
        except Exception as e:
            logging.error(f"Failed to relaunch MiSTer: {e}")
            logging.info("Exiting relaunch_mister: False")
            return False
    else:
        logging.warning("/media/fat/MiSTer not found, skipping relaunch")
    logging.info("Exiting relaunch_mister: True")
    return True

def windows_ui():
    """Launch tkinter UI for Windows/Linux."""
    logging.info("Entering windows_ui")
    try:
        import tkinter as tk
        from tkinter import messagebox, ttk
    except ImportError:
        logging.error("Tkinter not available. Please install python3-tk on Ubuntu.")
        print("Tkinter not available. Please install: sudo apt install python3-tk")
        return

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

    logging.info("Starting tkinter mainloop")
    root.mainloop()
    logging.info("Exiting windows_ui")

def mister_dialog():
    """Launch dialog menu for MiSTer."""
    logging.info("Entering mister_dialog")
    try:
        frontend_console = get_console_env("RETROSPIN_FRONTEND_CONSOLE", "/dev/tty2")
        # Use frontend console for dialog to ensure visibility after chvt
        dialog_console = frontend_console
        logging.info(f"Dialog console: {dialog_console}, Frontend console: {frontend_console}")

        logging.info("Calling kill_mister")
        if kill_mister():
            logging.info("kill_mister succeeded, calling setup_mister_console")
            setup_mister_console()
            logging.info("setup_mister_console completed, preparing dialog cmd")
            cmd = ["dialog", "--menu", "RetroSpin Disc Manager", "15", "40", "3",
                   "1", "Test Disc",
                   "2", "Save Disc",
                   "3", "Run Service"]
            logging.info(f"Dialog command: {cmd}")
            logging.info(f"Opening stdin and stdout on {dialog_console}")
            stdin_fd = open(dialog_console, "r")
            stdout_fd = open(dialog_console, "w")
            logging.info("Running dialog subprocess")
            result = subprocess.run(
                cmd, stdin=stdin_fd, stdout=stdout_fd,
                stderr=open("/tmp/retrospin_dialog.err", "w"), text=True, check=False
            )
            stdin_fd.close()
            stdout_fd.close()
            logging.info(f"Dialog result returncode: {result.returncode}, stdout: '{result.stdout.strip()}'")
            choice = result.stdout.strip()
            if result.returncode == 0 and choice:
                logging.info(f"User selected: {choice}")
                if choice == "1":
                    logging.info("Running test_disc")
                    run_script("test_disc", ["/dev/sr0"])
                elif choice == "2":
                    logging.info("Running save_disc")
                    run_script("save_disc", ["/dev/sr0", "TestGame", "ss"])
                elif choice == "3":
                    logging.info("Running service")
                    run_script("service", [])
            else:
                logging.warning("Dialog failed or no choice made")
        else:
            logging.error("kill_mister failed")
            logging.info(f"Showing error on frontend console: {frontend_console}")
            try:
                subprocess.run(
                    ["dialog", "--msgbox", "Failed to stop MiSTer process", "10", "40"],
                    stdin=open(frontend_console, "r"), stdout=open(frontend_console, "w"), check=False
                )
            except Exception as e:
                logging.error(f"Failed to show error dialog: {e}")
        logging.info("Calling relaunch_mister")
        relaunch_mister()
        logging.info("Exiting mister_dialog")
    except Exception as e:
        logging.error(f"Exception in mister_dialog: {e}", exc_info=True)
        relaunch_mister()

def main():
    logging.info("Entering main")
    try:
        parser = argparse.ArgumentParser(description="RetroSpin Disc Manager")
        parser.add_argument("--test", action="store_true", help="Test disc serial")
        parser.add_argument("--save", action="store_true", help="Save disc to .bin/.cue")
        parser.add_argument("--service", action="store_true", help="Run as background service")
        parser.add_argument("--drive", default="/dev/sr0" if platform.system() != "Windows" else "D:", help="CD drive path")
        parser.add_argument("--title", default="TestGame", help="Game title for save")
        parser.add_argument("--system", default="ss", choices=["psx", "ss", "mcd"], help="System type")
        args = parser.parse_args()
        logging.info(f"Args: {args}")

        system_info = platform.uname()
        logging.info(f"System info: {system_info}")
        is_mister = system_info.system == "Linux" and "MiSTer" in system_info.release
        logging.info(f"is_mister: {is_mister}")

        if not (args.test or args.save or args.service):
            logging.info("No args, launching UI")
            
            mister_dialog()
           

        logging.info("Has args, running specific command")
        if is_mister and args.service:
            run_script("service", [])
        elif args.test:
            run_script("test_disc", [args.drive])
        elif args.save:
            run_script("save_disc", [args.drive, args.title, args.system])
        else:
            frontend_console = get_console_env("RETROSPIN_FRONTEND_CONSOLE", "/dev/tty2")
            logging.info(f"Invalid option, showing error on {frontend_console}")
            if is_mister:
                try:
                    subprocess.run(
                        ["dialog", "--msgbox", "Invalid option or service mode not supported", "10", "40"],
                        stdin=open(frontend_console, "r"), stdout=open(frontend_console, "w"), check=False
                    )
                except Exception as e:
                    logging.error(f"Failed to show invalid option dialog: {e}")
            else:
                # Fallback to print
                print("Invalid option or service mode not supported")
        logging.info("Specific command completed")
    except Exception as e:
        logging.error(f"Exception in main: {e}", exc_info=True)
    finally:
        logging.info("Exiting main")

if __name__ == "__main__":
    main()