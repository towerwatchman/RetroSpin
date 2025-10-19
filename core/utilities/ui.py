import subprocess
import os
import sys
import time

def show_main_menu(is_running):
    """Display the main menu with dialog."""
    service_status = "Remove" if is_running else "Install"
    options = [
        f"{service_status} as Service",
        "Test Disc",
        "Save Disc",
        "Update Database",
        "Exit"
    ]
    cmd = ['dialog', '--backtitle', 'Retrospin', '--menu', 'Retrospin Menu', '15', '50', '5']
    for i, opt in enumerate(options):
        cmd.extend([str(i + 1), opt])
    # Use shell=True to match working command with redirections
    cmd_str = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in cmd]) + ' 2>/tmp/retrospin_dialog.out >/dev/tty'
    env = os.environ.copy()
    env["TERM"] = "linux"
    try:
        subprocess.run(cmd_str, shell=True, check=True, env=env)
        with open("/tmp/retrospin_dialog.out", "r") as f:
            choice = f.read().strip()
        os.remove("/tmp/retrospin_dialog.out")
        if choice.isdigit():
            idx = int(choice) - 1
            if idx == 0: return "install_remove"
            elif idx == 1: return "test_disc"
            elif idx == 2: return "save_disc"
            elif idx == 3: return "update_db"
            elif idx == 4: return "exit"
    except subprocess.CalledProcessError as e:
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ui.py: Failed to display menu: {e}\n")
    return "exit"

def show_message(message, title="Retrospin", non_blocking=False):
    """Display a message box with dialog, optionally non-blocking."""
    cmd = ['dialog', '--backtitle', title, '--infobox' if non_blocking else '--msgbox', message, '10', '50']
    cmd_str = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in cmd]) + ' >/dev/tty'
    env = os.environ.copy()
    env["TERM"] = "linux"
    try:
        if non_blocking:
            subprocess.Popen(cmd_str, shell=True, env=env)
            time.sleep(1)  # Brief display
        else:
            subprocess.run(cmd_str, shell=True, check=True, env=env)
    except subprocess.CalledProcessError as e:
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ui.py: Failed to display message: {e}\n")

def yes_no_prompt(message, title="Retrospin"):
    """Display a yes/no prompt with dialog."""
    cmd = ['dialog', '--backtitle', title, '--yesno', message, '10', '50']
    cmd_str = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in cmd]) + ' >/dev/tty'
    env = os.environ.copy()
    env["TERM"] = "linux"
    try:
        return subprocess.run(cmd_str, shell=True, env=env).returncode == 0
    except subprocess.CalledProcessError as e:
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ui.py: Failed to display yes/no: {e}\n")
        return False

def show_progress(message, func):
    """Display a progress gauge with dialog, passing the subprocess to func."""
    cmd = ['dialog', '--backtitle', 'Retrospin', '--gauge', message, '10', '50', '0']
    cmd_str = ' '.join([f'"{arg}"' if ' ' in arg else arg for arg in cmd]) + ' >/dev/tty'
    proc = subprocess.Popen(cmd_str, shell=True, stdin=subprocess.PIPE, env=os.environ.copy())
    try:
        func(proc)  # Pass proc to func for progress updates
        proc.communicate(input=b'XXX\n100\nComplete\nXXX\n')
    except Exception as e:
        proc.communicate()
        show_message(f"Error: {str(e)}", title="Retrospin")