import sys
import os
import time
import subprocess
from core.utilities.ui import show_main_menu, show_progress, show_message, yes_no_prompt
from core.utilities.service import install_service, remove_service, is_service_running
from core.utilities.disc import read_disc
from core.update_database import populate_database,create_table_schema, connect_to_database
from core.utilities.launcher import launch_game_on_mister
from core.utilities.files import find_game_file
from core.utilities.core import find_cores

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

#Creating database
conn, cursor = connect_to_database()
create_table_schema(cursor)


def save_disc(drive_path, title, system, serial):
    """Call save_disc from save.py."""
    from core.utilities.save import save_disc as save_disc_func
    save_disc_func(drive_path, title, system, serial)

def main():
    """Handle main program logic."""
    print("Starting main")
    args = sys.argv[1:]
    print("checking args")
    if "--save" in args:
        if len(args) != 4:
            error_msg = f"Error: --save expects 4 arguments (drive_path, title, system, serial), got {len(args)}: {args}"
            with open("/tmp/retrospin_err.log", "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - retrospin.py: {error_msg}\n")
            show_message(error_msg, title="Retrospin")
            sys.exit(1)
        drive_path, title, system, serial = args[args.index("--save") + 1:]
        save_disc(drive_path, title, system, serial)
    elif args:
        error_msg = f"Unknown arguments: {args}. Use no arguments for menu or --save with 4 args."
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - retrospin.py: {error_msg}\n")
        show_message(error_msg, title="Retrospin")
        sys.exit(1)
    else:
        print("going to menu")
        handle_menu()

def handle_menu():
    """Display and handle the main menu."""
    while True:
        choice = show_main_menu(is_service_running())
        print(choice)
        if choice == "install_remove":
            if is_service_running():
                if yes_no_prompt("Retrospin is running as a service. Remove it?"):
                    remove_service()
                    show_message("Service removed successfully.")
            else:
                if yes_no_prompt("Install Retrospin as a service?"):
                    install_service()
                    show_message("Service installed successfully.")
        elif choice == "test_disc":
            test_disc()
        elif choice == "save_disc":
            drive_path, title, system, serial = read_disc()
            if title != "none":
                save_disc(drive_path, title, system, serial)
            else:
                show_message("No disc detected or invalid disc.")
        elif choice == "update_db":
            update_database()
        elif choice == "exit":
            break

def test_disc():
    """Test for a disc and display its info."""
    show_message("Testing disc... Please insert a disc if not already.", title="Retrospin")
    start_time = time.time()
    while time.time() - start_time < 10:
        drive_path, title, system, serial = read_disc()
        if drive_path == "none":
            show_message("No optical drive detected.", title="Retrospin")
            return
        if title != "none":
            info = f"Drive: {drive_path}\nTitle: {title}\nSystem: {system}\nSerial: {serial}"
            show_message(info, title="Retrospin")
            return
        show_message("Trying to read disc...", title="Retrospin", non_blocking=True)
        time.sleep(1)
    show_message("No disc detected after 10 seconds.", title="Retrospin")

def update_database():
    """Update the game database."""
    print("update database")
    show_progress("Updating database...", populate_database)

def run_as_service():
    """Run Retrospin in service mode, polling for discs."""
    cores = find_cores(["psx"])  # Start with PSX
    if "psx" not in cores:
        print("PSX core not found. Service exiting.")
        return
    core_path = cores["psx"]
    print("Retrospin service started. Polling for discs...")
    while True:
        drive_path, title, system, serial = read_disc()
        if title != "none" and system == "psx":
            game_file = find_game_file(title, system)
            if game_file:
                launch_game_on_mister(serial, title, core_path, system, drive_path, find_game_file)
            else:
                show_message(f"Disc detected: {title} ({serial}). Launching save menu...", title="Retrospin", non_blocking=True)
                # Ensure title is quoted to handle spaces
                subprocess.Popen([
                    sys.executable,
                    os.path.abspath(__file__),
                    "--save",
                    drive_path,
                    f"{title}",  # Ensure title is a single argument
                    system,
                    serial
                ])
        time.sleep(5)  # Poll every 5 seconds

if __name__ == "__main__":
    try:
        if "--service" in sys.argv:
            run_as_service()
        else:
            main()
    except Exception as e:
        error_msg = f"Fatal error in retrospin.py: {str(e)}"
        with open("/tmp/retrospin_err.log", "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - retrospin.py: {error_msg}\n")
        show_message(error_msg, title="Retrospin")
        
        sys.exit(1)