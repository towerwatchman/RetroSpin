import os
import subprocess
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
    """Display a popup message on MiSTer."""
    try:
        dialog_cmd = f"dialog --msgbox \"{message}\" 12 40"
        print(f"Executing popup command: {dialog_cmd}")
        subprocess.run(dialog_cmd, shell=True, check=True, env={"TERM": "linux"})
    except Exception as e:
        print(f"Failed to display popup: {e}")

def select_game_title(matches, system, serial_key):
    """Prompt user to select a game title from multiple matches."""
    print(f"Multiple matches found for {system} ({serial_key}): {[(serial, title) for serial, title in matches]}")
    try:
        # Sanitize titles for dialog (escape quotes)
        sanitized_matches = [(serial, title.replace('"', '\\"')) for serial, title in matches]
        # Wrap titles to fit dialog width
        wrapped_matches = [(serial, wrap_text(title, 60)) for serial, title in sanitized_matches]
        # Build dialog menu
        dialog_cmd = f"dialog --menu \"Select game title for {system} disc ({serial_key})\" 20 80 10 "
        for i, (serial, title) in enumerate(wrapped_matches, 1):
            dialog_cmd += f"{i} \"{serial} - {title}\" "
        dialog_cmd += "2>/tmp/dialog.out"
        print(f"Executing dialog command: {dialog_cmd}")
        
        # Ensure /tmp is writable
        os.makedirs("/tmp", exist_ok=True)
        os.chmod("/tmp", 0o777)
        
        # Execute dialog directly
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