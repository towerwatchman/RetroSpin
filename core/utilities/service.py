import os
import subprocess
import sys
import time

STARTUP_SCRIPT = "/media/fat/linux/user-startup.sh"
RETROSPIN_CMD = f"{sys.executable} {os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'retrospin.py')} --service &"

def install_service():
    """Add Retrospin to MiSTer startup script."""
    os.makedirs(os.path.dirname(STARTUP_SCRIPT), exist_ok=True)
    with open(STARTUP_SCRIPT, "a") as f:
        f.write(f"\n{RETROSPIN_CMD}\n")

def remove_service():
    """Remove Retrospin from startup script."""
    if not os.path.exists(STARTUP_SCRIPT):
        return
    with open(STARTUP_SCRIPT, "r") as f:
        lines = f.readlines()
    with open(STARTUP_SCRIPT, "w") as f:
        for line in lines:
            if RETROSPIN_CMD not in line:
                f.write(line)

def is_service_running():
    """Check if Retrospin service is running using MiSTer-compatible ps command."""
    try:
        print("Checking if service is running")
        # Use 'ps' alone (BusyBox-compatible) to list all processes
        result = subprocess.run(["ps"], capture_output=True, text=True, check=True)
        print("check done")
        # Check for 'retrospin.py --service' in output
        return "--service" in result.stdout and "retrospin.py" in result.stdout
    except:       
        return False