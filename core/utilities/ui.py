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


def wrap_text(text, width):
    """Wrap text to fit within the specified width."""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        word_length = len(word)
        if current_length + word_length + (1 if current_line else 0) <= width:
            current_line.append(word)
            current_length += word_length + (1 if current_line else 0)
        else:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = word_length
    if current_line:
        lines.append(" ".join(current_line))
    
    return "\\n".join(lines)

def show_popup(message):
    """Display a popup message on MiSTer."""
    try:
        if not os.isatty(0):
            print("No controlling terminal for popup, skipping")
            return
        dialog_cmd = f"dialog --msgbox \"{message}\" 12 40 >/dev/tty1"
        print(f"Executing popup command: {dialog_cmd}")
        env = os.environ.copy()
        env["TERM"] = "linux"
        subprocess.run(dialog_cmd, shell=True, check=True, env=env)
    except Exception as e:
        print(f"Failed to display popup: {e}")

def select_game_title(matches, system, serial_key):
    """Prompt user to select a game title from multiple matches."""
    print(f"Multiple matches found for {system} ({serial_key}): {[(serial, title) for serial, title in matches]}")
    try:
        if not os.isatty(0):
            print("No controlling terminal for dialog, using first match")
            return matches[0][1]
        # Sanitize titles for dialog (escape quotes)
        sanitized_matches = [(serial, title.replace('"', '\\"')) for serial, title in matches]
        # Wrap titles to fit dialog width
        wrapped_matches = [(serial, wrap_text(title, 60)) for serial, title in sanitized_matches]
        # Build dialog menu
        dialog_cmd = f"dialog --menu \"Select game title for {system} disc ({serial_key})\" 20 80 10 "
        for i, (serial, title) in enumerate(wrapped_matches, 1):
            dialog_cmd += f"{i} \"{serial} - {title}\" "
        dialog_cmd += "2>/tmp/dialog.out >/dev/tty1"
        print(f"Executing dialog command: {dialog_cmd}")
        
        # Ensure /tmp is writable
        os.makedirs("/tmp", exist_ok=True)
        os.chmod("/tmp", 0o777)
        
        # Execute dialog in foreground
        env = os.environ.copy()
        env["TERM"] = "linux"
        subprocess.run(dialog_cmd, shell=True, check=True, env=env)
        
        # Wait for user input
        time.sleep(5)
        if os.path.exists("/tmp/dialog.out"):
            with open("/tmp/dialog.out", "r") as f:
                choice = f.read().strip()
            print(f"Dialog output: {choice}")
            os.remove("/tmp/dialog.out")
            if choice:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(matches):
                    selected_serial, selected_title = matches[choice_idx]
                    print(f"User selected: {selected_serial} - {selected_title}")
                    return selected_title
        print("No valid selection made. Using first match.")
        return matches[0][1]
    except Exception as e:
        print(f"Error prompting for title selection: {e}")
        return matches[0][1]