import os
import subprocess
import xml.etree.ElementTree as ET

# Import the new Python save_disc function
from core.utilities.save import save_disc  # <-- NEW: Python save_disc

MISTER_CMD = "/dev/MiSTer_cmd"
TMP_MGL_PATH = "/tmp/game.mgl"

# Removed: old shell script path
# SAVE_SCRIPT = "/media/fat/retrospin/core/functions/save_disc.sh"


def create_mgl_file(core_path, game_file, mgl_path, system):
    """Create a temporary MGL file for the game."""
    mgl = ET.Element("mistergamedescription")
    rbf = ET.SubElement(mgl, "rbf")
    rbf.text = f"_console/{system}"
    file_tag = ET.SubElement(mgl, "file")
    file_tag.set("delay", "1")
    file_tag.set("type", "s")
    file_tag.set("index", "1" if system == "psx" else "0")
    file_tag.set("path", game_file)

    tree = ET.ElementTree(mgl)
    tree.write(mgl_path, encoding="utf-8", xml_declaration=True)
    print(f"Created MGL file at {mgl_path}")


def launch_game_on_mister(game_serial, title, core_path, system, drive_path, find_game_file):
    """
    Launch the game on MiSTer using a temporary MGL file.
    If no local game file is found, trigger disc save using Python function.
    """
    # Use generic title for unknown games
    if title == "Unknown Game":
        title = f"Game ({game_serial})"
        print(f"Using generic title for unknown game: {title}")

    # Sanitize title for command-line safety
    title = title.replace('<', '').replace('>', '').replace(':', '').replace('"', '').replace('/', '').replace('\\', '').replace('|', '').replace('?', '').replace('*', '').strip()
    if not title:
        title = "Unknown_Game"

    game_file = find_game_file(title, system)
    if not game_file:
        if title != "Unknown Game":
            print(f"Game file not found for {title} ({game_serial}). Triggering save for matched {system} game.")
            # Use the new Python save_disc function
            try:
                save_disc(drive_path, title, system)
            except Exception as e:
                print(f"Save disc failed in Python: {e}")
        else:
            print(f"Game file not found for {title} ({game_serial}). Skipping save for unmatched {system} game.")
        return

    try:
        create_mgl_file(core_path, game_file, TMP_MGL_PATH, system)
        command = f"load_core {TMP_MGL_PATH}"
        print(f"Preparing to send command to {MISTER_CMD}: {command} for system {system}")
        with open(MISTER_CMD, "w") as cmd_file:
            cmd_file.write(command + "\n")
            cmd_file.flush()
        print(f"Command '{command}' sent successfully to MiSTer")
        print(f"MGL file preserved at {TMP_MGL_PATH} for inspection")
    except Exception as e:
        print(f"Failed to launch game on MiSTer: {e}")