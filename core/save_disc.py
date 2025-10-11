import os
import subprocess
import sys
from utilities.files import find_game_file
from utilities.disc import read_disc

script_dir = os.path.dirname(os.path.abspath(__file__))
script_path = os.path.join(script_dir, "function/" "save_disc.sh")

print(script_dir)
print(script_path)

drive_path, title, system, game_serial = read_disc()
game_file = find_game_file(title, system)
if not game_file:
    if title != "Unknown Game":
        print(f"Game file not found for {title} ({game_serial}). Triggering save for matched {system} game.")
        save_cmd = f"{script_path} \"{drive_path}\" \"{title}\" {system}"
        print(f"Executing save command: {save_cmd}")
        try:
            subprocess.run(save_cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Save script failed: {e}")
    else:
        print(f"Game file not found for {title} ({game_serial}). Skipping save for unmatched {system} game.")