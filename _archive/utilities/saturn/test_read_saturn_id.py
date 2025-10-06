import ctypes

def read_game_id(drive_letter):
    """Read the game ID from the Sega Saturn disc."""
    drive = f"\\\\.\\{drive_letter}:"
    h = ctypes.windll.kernel32.CreateFileW(drive, 0x80000000, 1, None, 3, 0, None)
    if h == -1:
        raise Exception("Cannot open drive")
    buffer = ctypes.create_string_buffer(2048)
    bytes_read = ctypes.c_ulong(0)
    ctypes.windll.kernel32.ReadFile(h, buffer, 2048, ctypes.byref(bytes_read), None)
    ctypes.windll.kernel32.CloseHandle(h)
    if bytes_read.value < 2048:
        raise Exception("Failed to read sector")
    game_id = buffer[32:42].decode('ascii').strip()
    return game_id

if __name__ == "__main__":
    drive_letter = input("Enter the drive letter of the Saturn disc: ")
    try:
        game_id = read_game_id(drive_letter)
        print(f"Game ID: {game_id}")
    except Exception as e:
        print(f"Error: {e}")