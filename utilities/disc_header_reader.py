import os
import win32api
import win32file
import win32con

def get_dvd_drives():
    drives = []
    try:
        # Get all drive letters
        for drive in win32api.GetLogicalDriveStrings().split('\x00')[:-1]:
            drive = drive.rstrip('\\')
            # Check if the drive is a CDROM
            if win32file.GetDriveType(drive) == win32con.DRIVE_CDROM:
                device_path = f"\\\\.\\{drive}"
                drives.append(device_path)
    except Exception as e:
        print(f"Error detecting DVD drives: {str(e)}")
    return sorted(drives)

def read_header(path):
    try:
        with open(path, 'rb') as f:
            # Seek to start and read first 256 bytes
            f.seek(0)
            data = f.read(1024)
            total_bytes = len(data)
            
            # Print header
            print("\nHeader")
            print("Row\tContents\t\t\t\t\tASCII")
            
            # Process 16 bytes at a time
            for i in range(0, total_bytes, 16):
                row_data = data[i:i+16]
                row_hex = ' '.join(f'{b:02X}' for b in row_data)
                row_ascii = ''.join(chr(b) if 32 <= b < 127 else ' ' for b in row_data)
                row_addr = f'{i:04X}'
                print(f"{row_addr}\t{row_hex:<47}\t{row_ascii}")
            
            print(f"Total: {total_bytes} bytes")
            
    except PermissionError:
        print(f"Error: Permission denied accessing {path}. Ensure you're running as administrator and the drive is not locked.")
    except FileNotFoundError:
        print(f"Error: Device or file not found: {path}. Ensure a disc is inserted.")
    except Exception as e:
        print(f"Error reading {path}: {str(e)}")

def main():
    print("Detecting DVD drives...")
    dvds = get_dvd_drives()
    
    if not dvds:
        print("No DVD drives detected. Ensure a DVD drive is connected and a disc is inserted.")
        return
    
    print("\nAvailable DVD drives:")
    for i, dvd in enumerate(dvds, 1):
        print(f"{i}. {dvd}")
    
    try:
        read_header(dvds[0])
        #choice = int(input("\nEnter the number of the DVD drive to read (e.g., 1): "))
        #if 1 <= choice <= len(dvds):
        #    read_header(dvds[choice - 1])
        #else:
            #print("Invalid selection.")
    except ValueError:
        print("Invalid input. Please enter a number.")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()