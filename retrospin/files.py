import os
import re

PSX_GAME_PATHS = [
    "/media/fat/games/PSX/",
    "/media/usb0/games/PSX/"
]
SATURN_GAME_PATHS = [
    "/media/fat/games/Saturn/",
    "/media/usb0/games/Saturn/"
]
MCD_GAME_PATHS = [
    "/media/fat/games/MegaCD/",
    "/media/usb0/games/MegaCD/"
]

def clean_game_title(title):
    """Remove language mappings like (En,Fr,De,Es,It) from the title, preserving region."""
    # Remove language tags, e.g., (En,Fr,De,Es,It), (Ja), but keep (Japan), (USA)
    cleaned = re.sub(r'\s*\((?:En|Fr|De|Es|It|Ja|Ko|Zh)(?:,[A-Za-z]+)*\)\s*$', '', title).strip()
    return cleaned

def find_game_file(title, system):
    """Search for .chd or complete .cue/.bin game files based on system."""
    paths = {
        "psx": PSX_GAME_PATHS,
        "ss": SATURN_GAME_PATHS,
        "mcd": MCD_GAME_PATHS
    }[system]
    
    # Sanitize title for filename use (keep parentheses, spaces, hyphens)
    safe_title = re.sub(r'[<>:"/\\|?*]', '', title).strip()
    print(f"Searching for game file with full title: {safe_title}")
    
    # Try full title first
    # Check for .chd
    game_filename = f"{safe_title}.chd"
    for base_path in paths:
        game_file = os.path.join(base_path, game_filename)
        if os.path.exists(game_file):
            print(f"Found .chd game file with full title: {game_file}")
            if os.access(game_file, os.R_OK):
                print(f"Game file {game_file} is readable")
            else:
                print(f"Game file {game_file} is not readable")
            return game_file
    
    # Check for .cue and corresponding .bin
    game_filename = f"{safe_title}.cue"
    for base_path in paths:
        cue_file = os.path.join(base_path, game_filename)
        bin_file = os.path.join(base_path, f"{safe_title}.bin")
        if os.path.exists(cue_file):
            if os.path.exists(bin_file):
                print(f"Found complete .cue/.bin pair with full title: {cue_file}, {bin_file}")
                if os.access(cue_file, os.R_OK) and os.access(bin_file, os.R_OK):
                    print(f"Game files {cue_file} and {bin_file} are readable")
                else:
                    print(f"Game files {cue_file} or {bin_file} are not readable")
                return cue_file
            else:
                print(f"Found .cue without .bin for full title: {cue_file}")
    
    # If full title fails, try cleaned title (remove language tags)
    cleaned_title = clean_game_title(title)
    if cleaned_title != safe_title:
        print(f"No files found with full title, trying cleaned title: {cleaned_title}")
        # Sanitize cleaned title
        safe_cleaned_title = re.sub(r'[<>:"/\\|?*]', '', cleaned_title).strip()
        # Check for .chd
        game_filename = f"{safe_cleaned_title}.chd"
        for base_path in paths:
            game_file = os.path.join(base_path, game_filename)
            if os.path.exists(game_file):
                print(f"Found .chd game file with cleaned title: {game_file}")
                if os.access(game_file, os.R_OK):
                    print(f"Game file {game_file} is readable")
                else:
                    print(f"Game file {game_file} is not readable")
                return game_file
        
        # Check for .cue and corresponding .bin
        game_filename = f"{safe_cleaned_title}.cue"
        for base_path in paths:
            cue_file = os.path.join(base_path, game_filename)
            bin_file = os.path.join(base_path, f"{safe_cleaned_title}.bin")
            if os.path.exists(cue_file):
                if os.path.exists(bin_file):
                    print(f"Found complete .cue/.bin pair with cleaned title: {cue_file}, {bin_file}")
                    if os.access(cue_file, os.R_OK) and os.access(bin_file, os.R_OK):
                        print(f"Game files {cue_file} and {bin_file} are readable")
                    else:
                        print(f"Game files {cue_file} or {bin_file} are not readable")
                    return cue_file
                else:
                    print(f"Found .cue without .bin for cleaned title: {cue_file}")
    
    print(f"No complete .chd or .cue/.bin game files found for: {safe_title} or {cleaned_title}")
    return None