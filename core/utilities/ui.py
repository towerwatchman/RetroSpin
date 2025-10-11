import os
import subprocess
import sys
import time

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
    """Display a popup message on MiSTer with OK button."""
    try:
        dialog_cmd = f"dialog --ok-label \"OK\" --msgbox \"{message}\" 12 40"
        env = os.environ.copy()
        env["TERM"] = "linux"
        # Try current terminal, fallback to /dev/tty
        tty = os.ttyname(0) if os.isatty(0) else "/dev/tty"
        dialog_cmd += f" >{tty} 2>/tmp/retrospin_dialog_err.log"
        subprocess.run(dialog_cmd, shell=True, check=True, env=env)
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to display popup: {e}\nPopup message: {message}"
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ui.py: {error_msg}\n")
        print(error_msg, file=sys.stderr)

def show_yesno(message):
    """Display a yes/no prompt on MiSTer, return True for Yes, False for No."""
    try:
        dialog_cmd = f"dialog --yesno \"{message}\" 12 60"
        env = os.environ.copy()
        env["TERM"] = "linux"
        # Try current terminal, fallback to /dev/tty
        tty = os.ttyname(0) if os.isatty(0) else "/dev/tty"
        dialog_cmd += f" >{tty} 2>/tmp/retrospin_dialog_err.log"
        result = subprocess.run(dialog_cmd, shell=True, check=True, capture_output=True, env=env)
        return result.returncode == 0  # 0 for Yes, 1 for No
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to display yes/no prompt: {e}\nYes/No message: {message}"
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ui.py: {error_msg}\n")
        print(error_msg, file=sys.stderr)
        return False  # Default to No on error

def select_game_title(matches, system, serial_key):
    """Prompt user to select a game title from multiple matches."""
    try:
        if not os.isatty(0):
            with open("/tmp/retrospin_err.log", "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ui.py: No controlling terminal for dialog, using first match\n")
            return matches[0][1]
        # Sanitize titles for dialog (escape quotes)
        sanitized_matches = [(serial, title.replace('"', '\\"')) for serial, title in matches]
        # Wrap titles to fit dialog width
        wrapped_matches = [(serial, wrap_text(title, 60)) for serial, title in sanitized_matches]
        # Build dialog menu
        dialog_cmd = f"dialog --menu \"Select game title for {system} disc ({serial_key})\" 20 80 10 "
        for i, (serial, title) in enumerate(wrapped_matches, 1):
            dialog_cmd += f"{i} \"{serial} - {title}\" "
        dialog_cmd += "2>/tmp/dialog.out"
        
        # Ensure /tmp is writable
        os.makedirs("/tmp", exist_ok=True)
        os.chmod("/tmp", 0o777)
        
        # Execute dialog in foreground
        env = os.environ.copy()
        env["TERM"] = "linux"
        tty = os.ttyname(0) if os.isatty(0) else "/dev/tty"
        dialog_cmd += f" >{tty}"
        subprocess.run(dialog_cmd, shell=True, check=True, env=env)
        
        # Read dialog output
        if os.path.exists("/tmp/dialog.out"):
            with open("/tmp/dialog.out", "r") as f:
                choice = f.read().strip()
            os.remove("/tmp/dialog.out")
            if choice:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(matches):
                    selected_serial, selected_title = matches[choice_idx]
                    with open("/tmp/retrospin_err.log", "a") as f:
                        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ui.py: User selected: {selected_serial} - {selected_title}\n")
                    return selected_title
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ui.py: No valid selection made. Using first match.\n")
        return matches[0][1]
    except subprocess.CalledProcessError as e:
        error_msg = f"Error prompting for title selection: {e}"
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - ui.py: {error_msg}\n")
        return matches[0][1]