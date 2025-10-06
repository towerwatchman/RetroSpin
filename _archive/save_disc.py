import argparse
import logging
import tkinter as tk
from tkinter import messagebox
import os

# Setup logging
logging.basicConfig(filename="retrospin.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    parser = argparse.ArgumentParser(description="Save Disc")
    parser.add_argument("drive", help="CD drive path")
    parser.add_argument("title", help="Game title")
    parser.add_argument("system", choices=["psx", "ss", "mcd"], help="System type")
    args = parser.parse_args()

    root = tk.Tk()
    root.withdraw()
    output_dir = os.path.expanduser(f"~/RetroSpinGames/{args.system.upper()}")
    os.makedirs(output_dir, exist_ok=True)
    messagebox.showinfo("RetroSpin Save", f"Would save {args.title}.bin/.cue to {output_dir}\nSaving not implemented yet")
    logging.warning("Save disc not implemented")
    root.destroy()

if __name__ == "__main__":
    main()