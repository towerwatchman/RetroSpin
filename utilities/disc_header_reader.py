import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os
import win32api
import win32file
import win32con

class DVDHeaderReader:
    def __init__(self, root):
        self.root = root
        self.root.title("DVD Header Reader")
        self.root.geometry("800x600")
        
        # Main frame
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Buttons
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.grid(row=0, column=0, pady=5, sticky=tk.W)
        
        self.select_file_button = ttk.Button(self.button_frame, text="Select Disk Image", command=self.select_file)
        self.select_file_button.grid(row=0, column=0, padx=5)
        
        self.select_dvd_button = ttk.Button(self.button_frame, text="Select DVD Drive", command=self.select_dvd)
        self.select_dvd_button.grid(row=0, column=1, padx=5)
        
        # Treeview for displaying data
        self.tree = ttk.Treeview(self.main_frame, columns=('Row', 'Contents', 'ASCII'), show='headings')
        self.tree.heading('Row', text='Row')
        self.tree.heading('Contents', text='Contents')
        self.tree.heading('ASCII', text='ASCII')
        self.tree.column('Row', width=100)
        self.tree.column('Contents', width=400)
        self.tree.column('ASCII', width=200)
        self.tree.grid(row=1, column=0, pady=10)
        
        # Scrollbar
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=self.scrollbar.set)
        self.scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        # Total bytes label
        self.total_label = ttk.Label(self.main_frame, text="Total: 0 bytes")
        self.total_label.grid(row=2, column=0, pady=5)
        
        self.file_path = None
        
    def select_file(self):
        self.file_path = filedialog.askopenfilename(filetypes=[("All files", "*.*"), ("ISO files", "*.iso")])
        if self.file_path:
            self.read_header(self.file_path)
            
    def select_dvd(self):
        dvds = self.get_dvd_drives()
        if not dvds:
            messagebox.showerror("Error", "No DVD drives detected. Ensure a DVD drive is connected and try running as administrator.")
            return
            
        # Create a new window for DVD selection
        dvd_window = tk.Toplevel(self.root)
        dvd_window.title("Select DVD Drive")
        dvd_window.geometry("300x200")
        
        ttk.Label(dvd_window, text="Select a DVD drive:").pack(pady=5)
        dvd_listbox = tk.Listbox(dvd_window, height=10)
        dvd_listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        
        for dvd in dvds:
            dvd_listbox.insert(tk.END, dvd)
            
        def on_dvd_select():
            selection = dvd_listbox.curselection()
            if selection:
                dvd_path = dvds[selection[0]]
                dvd_window.destroy()
                self.read_header(dvd_path)
                
        ttk.Button(dvd_window, text="Select", command=on_dvd_select).pack(pady=5)
        
    def get_dvd_drives(self):
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
            messagebox.showerror("Error", f"Failed to detect DVD drives: {str(e)}")
        return sorted(drives)
            
    def read_header(self, path):
        # Clear existing treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        try:
            with open(path, 'rb') as f:
                # Seek to start and read first 1MB
                f.seek(0)
                data = f.read(1024 * 1024)
                total_bytes = len(data)
                
                # Process 16 bytes at a time
                for i in range(0, min(total_bytes, 1024 * 1024), 16):
                    row_data = data[i:i+16]
                    row_hex = ' '.join(f'{b:02X}' for b in row_data)
                    row_ascii = ''.join(chr(b) if 32 <= b < 127 else ' ' for b in row_data)
                    row_addr = f'{i:04X}'
                    
                    self.tree.insert('', tk.END, values=(row_addr, row_hex, row_ascii))
                
                self.total_label.config(text=f"Total: {total_bytes} bytes")
                
        except PermissionError:
            messagebox.showerror("Error", "Permission denied. Please run the program as administrator.")
        except FileNotFoundError:
            messagebox.showerror("Error", f"Device or file not found: {path}. Ensure a disc is inserted.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read: {str(e)}")

def main():
    root = tk.Tk()
    app = DVDHeaderReader(root)
    root.mainloop()

if __name__ == "__main__":
    main()