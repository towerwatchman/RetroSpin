import os
import sys
import time

# Add /retrospin to sys.path to ensure core package is found
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(os.path.dirname(script_dir)))

from core.utilities.disc import  read_disc

if __name__ == "__main__":
    drive_path, title, system = read_disc()
    print(f"{drive_path} : {title} : {system}")
    sys.exit(0)