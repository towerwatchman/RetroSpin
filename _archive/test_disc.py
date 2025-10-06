import argparse
import logging
import wmi
import re
import os
import time
import tkinter as tk
from tkinter import messagebox
import binascii

# Setup logging to file and console
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("retrospin.log"),
        logging.StreamHandler()
    ]
)

# Try importing pywin32 modules
try:
    import win32file
    import win32con
    import win32api
    PYWIN32_AVAILABLE = True
    logging.debug("pywin32 modules loaded successfully")
except ImportError as e:
    PYWIN32_AVAILABLE = False
    logging.warning(f"pywin32 modules not found: {str(e)}. Falling back to WMI.")

def is_admin():
    """Check if running as admin."""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception as e:
        logging.error(f"Error checking admin status: {str(e)}")
        return False

def find_first_disc_drive():
    """Find the first available CD/DVD drive."""
    start_time = time.time()
    logging.debug("Searching for CD/DVD drives...")
    try:
        c = wmi.WMI()
        drives = [cdrom.Drive for cdrom in c.Win32_CDROMDrive()]
        logging.debug(f"Found drives: {drives}")
        if not drives:
            logging.warning("No disc drives found")
            return None
        drive = drives[0]
        logging.info(f"Selected first disc drive: {drive} (took {time.time() - start_time:.2f}s)")
        return drive
    except Exception as e:
        logging.error(f"Error finding disc drive: {str(e)}")
        return None

def check_disc_presence(drive):
    """Check if a disc is present in the drive."""
    start_time = time.time()
    logging.debug(f"Checking disc presence in drive {drive}")
    if not PYWIN32_AVAILABLE:
        logging.warning("Cannot check disc presence without pywin32")
        return True  # Assume present to proceed
    try:
        handle = win32file.CreateFile(
            f"\\\\.\\{drive}",
            win32con.GENERIC_READ,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
            None,
            win32con.OPEN_EXISTING,
            win32con.FILE_FLAG_NO_BUFFERING,
            None
        )
        if handle == win32file.INVALID_HANDLE_VALUE:
            logging.warning(f"No disc detected in drive {drive}: Error {win32api.GetLastError()}")
            return False
        win32file.CloseHandle(handle)
        logging.debug(f"Disc presence confirmed for drive {drive} (took {time.time() - start_time:.2f}s)")
        return True
    except Exception as e:
        logging.error(f"Error checking disc presence: {str(e)}")
        return False

def read_disc_serial(drive):
    """Read disc serial for Saturn, Sega CD, PSX."""
    start_time = time.time()
    logging.debug(f"Attempting to read serial from drive {drive}")
    if not PYWIN32_AVAILABLE:
        logging.warning("WMI cannot read disc serials; requires pywin32")
        return None, None, None

    if not is_admin():
        logging.warning("Not running as admin; disc read may fail")

    # Sector-aligned read (2048 bytes)
    sector_size = 2048
    offsets = [0x0, 0x8000]  # Prioritize Saturn header

    # Initial spin-up
    logging.debug("Initial drive spin-up (1 second)")
    time.sleep(1)

    for offset in offsets:
        logging.debug(offset)
        aligned_offset = (offset // sector_size) * sector_size
        if offset != aligned_offset:
            logging.debug(f"Adjusting offset 0x{offset:04x} to sector-aligned 0x{aligned_offset:04x}")
            offset = aligned_offset

        logging.debug(f"Trying offset 0x{offset:04x}")
        try:
            logging.debug(f"Opening drive {drive} with CreateFile (no buffering)")
            handle = win32file.CreateFile(
                f"\\\\.\\{drive}",
                win32con.GENERIC_READ,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
                None,
                win32con.OPEN_EXISTING,
                win32con.FILE_FLAG_NO_BUFFERING,
                None
            )
            if handle == win32file.INVALID_HANDLE_VALUE:
                error_code = win32api.GetLastError()
                logging.error(f"Failed to open drive {drive}: Error {error_code}")
                return None, None, None

            try:
                logging.debug(f"Seeking to offset 0x{offset:04x}")
                win32file.SetFilePointer(handle, offset, win32file.FILE_BEGIN)
                logging.debug(f"Reading {sector_size} bytes")
                (data, read_bytes) = win32file.ReadFile(handle, sector_size)
                logging.debug(f"Read {read_bytes} bytes")
                if read_bytes != sector_size:
                    logging.error(f"Incomplete read from disc: expected {sector_size}, got {read_bytes} bytes")
                    continue

                try:
                    text = data.decode('ascii', errors='ignore')
                    text_clean = text[:100].replace('\n', ' ')
                    hex_data = binascii.hexlify(data).decode('ascii')
                    logging.debug(f"Raw data (first 100 chars, offset 0x{offset:04x}): {text_clean}")
                    logging.debug(f"Raw data (hex, first 200 chars, offset 0x{offset:04x}): {hex_data[:200]}")
                except Exception as e:
                    logging.error(f"Error decoding data at offset 0x{offset:04x}: {str(e)}")
                    continue

                # Saturn serials (Western: T-XXXXY, Japan: GS-XXXX)
                #saturn = re.search(r'(T-[0-9]{4}[A-Z]|GS-[0-9]{4})', text)
                #saturn_serial = saturn.group(0) if saturn else None
                #sega_cd = re.search(r'T-[0-9]{5}-[0-9]{2}', text)
                #sega_cd_serial = sega_cd.group(0) if sega_cd else None
                #psx = re.search(r'S[LUC][UE][PS]-?[0-9]{5}', text)
                #psx_serial = psx.group(0) if psx else None

                #logging.debug(f"Saturn regex match: {saturn.group(0) if saturn else 'None'}")
                #logging.info(f"Saturn serial (offset 0x{offset:04x}): {saturn_serial or 'None'}")
                #logging.info(f"Sega CD serial (offset 0x{offset:04x}): {sega_cd_serial or 'None'}")
                #logging.info(f"PSX serial (offset 0x{offset:04x}): {psx_serial or 'None'}")
                #if saturn_serial or sega_cd_serial or psx_serial:
                #    logging.info(f"Serial read completed (total time: {time.time() - start_time:.2f}s)")
                #    return saturn_serial, sega_cd_serial, psx_serial
            except Exception as e:
                logging.error(f"Error during disc read at offset 0x{offset:04x}: {str(e)}")
            finally:
                logging.debug("Closing drive handle")
                win32file.CloseHandle(handle)
        except Exception as e:
            logging.error(f"Error accessing drive {drive} at offset 0x{offset:04x}: {str(e)}")
    logging.error("No valid serials found at any offset")
    logging.info(f"Serial read failed (total time: {time.time() - start_time:.2f}s)")
    return None, None, None

def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Test Disc Serial")
    parser.add_argument("drive", nargs="?", default=None, help="CD drive path")
    args = parser.parse_args()

    drive = args.drive if args.drive else find_first_disc_drive()
    if not drive:
        logging.error("No disc drive detected")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("RetroSpin Test", "No disc drive detected")
        root.destroy()
        raise Exception("No disc drive detected")

    if not check_disc_presence(drive):
        logging.error("No disc present in drive")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("RetroSpin Test", "No disc present in drive")
        root.destroy()
        raise Exception("No disc present in drive")

    saturn_serial, sega_cd_serial, psx_serial = read_disc_serial(drive)
    message = "Disc Serials:\n"
    message += f"Saturn: {saturn_serial or 'None'}\n"
    message += f"Sega CD: {sega_cd_serial or 'None'}\n"
    message += f"PSX: {psx_serial or 'None'}"
    logging.info(message)
    logging.info(f"Total operation time: {time.time() - start_time:.2f}s")
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("RetroSpin Test", message)
    root.destroy()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(str(e))
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("RetroSpin Test", str(e))
        root.destroy()