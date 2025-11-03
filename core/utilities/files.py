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
    """Remove language mappings, (Beta), (Rev *), dates, and malformed tags from the title, preserving region."""
    cleaned = title
    # Remove language tags (e.g., (En,Fr,De,Es,It), (Ja))
    cleaned = re.sub(r'\s*\((?:En|Fr|De|Es|It|Ja|Ko|Zh)(?:,[A-Za-z]+)*\)\s*$', '', cleaned, flags=re.IGNORECASE)
    # Remove (Beta)
    cleaned = re.sub(r'\s*\(Beta\)\s*$', '', cleaned, flags=re.IGNORECASE)
    # Remove (Rev <number>) (e.g., (Rev 1), (Rev 123))
    cleaned = re.sub(r'\s*\(Rev\s+\d+\)\s*$', '', cleaned, flags=re.IGNORECASE)
    # Remove date tags (e.g., (2000-08-21))
    cleaned = re.sub(r'\s*\(\d{4}-\d{2}-\d{2}\)\s*$', '', cleaned)
    # Remove malformed or incomplete tags (e.g., (Rev, (, (USA)
    cleaned = re.sub(r'\s*\([^\)]*?\s*$', '', cleaned)
    return cleaned.strip()

def find_game_file(title, system):
    """Search for .chd or complete .cue/.bin game files based on system, including subfolders."""
    paths = {
        "psx": PSX_GAME_PATHS,
        "saturn": SATURN_GAME_PATHS,
        "megacd": MCD_GAME_PATHS
    }[system]
    
    # Sanitize title for filename use (keep parentheses, spaces, hyphens)
    safe_title = re.sub(r'[<>:"/\\|?*]', '', title).strip()
    print(f"Searching for game file with full title: {safe_title}")
    
    # Try full title first
    # Check for .chd in base paths and subfolders
    game_filename = f"{safe_title}.chd"
    for base_path in paths:
        for root, dirs, files in os.walk(base_path):
            if game_filename in files:
                game_file = os.path.join(root, game_filename)
                print(f"Found .chd game file with full title: {game_file}")
                if os.access(game_file, os.R_OK):
                    print(f"Game file {game_file} is readable")
                else:
                    print(f"Game file {game_file} is not readable")
                return game_file
    
    # Check for .cue and corresponding .bin in base paths and subfolders
    game_filename = f"{safe_title}.cue"
    for base_path in paths:
        for root, dirs, files in os.walk(base_path):
            if game_filename in files:
                cue_file = os.path.join(root, game_filename)
                bin_filename = f"{safe_title}.bin"
                bin_file = os.path.join(root, bin_filename)
                if os.path.exists(bin_file):
                    print(f"Found complete .cue/.bin pair with full title: {cue_file}, {bin_file}")
                    if os.access(cue_file, os.R_OK) and os.access(bin_file, os.R_OK):
                        print(f"Game files {cue_file} and {bin_file} are readable")
                    else:
                        print(f"Game files {cue_file} or {bin_file} are not readable")
                    return cue_file
                else:
                    print(f"Found .cue without .bin for full title: {cue_file}")
    
    # If full title fails, try cleaned title
    cleaned_title = clean_game_title(title)
    if cleaned_title != safe_title:
        print(f"No files found with full title, trying cleaned title: {cleaned_title}")
        # Sanitize cleaned title
        safe_cleaned_title = re.sub(r'[<>:"/\\|?*]', '', cleaned_title).strip()
        # Check for .chd in base paths and subfolders
        game_filename = f"{safe_cleaned_title}.chd"
        for base_path in paths:
            for root, dirs, files in os.walk(base_path):
                if game_filename in files:
                    game_file = os.path.join(root, game_filename)
                    print(f"Found .chd game file with cleaned title: {game_file}")
                    if os.access(game_file, os.R_OK):
                        print(f"Game file {game_file} is readable")
                    else:
                        print(f"Game file {game_file} is not readable")
                    return game_file
        
        # Check for .cue and corresponding .bin in base paths and subfolders
        game_filename = f"{safe_cleaned_title}.cue"
        for base_path in paths:
            for root, dirs, files in os.walk(base_path):
                if game_filename in files:
                    cue_file = os.path.join(root, game_filename)
                    bin_filename = f"{safe_cleaned_title}.bin"
                    bin_file = os.path.join(root, bin_filename)
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