import os

MISTER_CORE_DIR = "/media/fat/_Console/"

def find_core(system):
    """Find the latest core .rbf file for the given system in /media/fat/_Console/."""
    prefix = {"psx": "PSX_", "ss": "Saturn_", "mcd": "MegaCD_"}[system]
    try:
        rbf_files = [f for f in os.listdir(MISTER_CORE_DIR) if f.startswith(prefix) and f.endswith(".rbf")]
        if not rbf_files:
            print(f"No {system} core found in {MISTER_CORE_DIR}. Please place a {prefix}*.rbf file there.")
            return None
        rbf_files.sort(reverse=True)
        latest_core = os.path.join(MISTER_CORE_DIR, rbf_files[0])
        print(f"Found {system} core: {latest_core}")
        if os.path.exists(latest_core):
            print(f"Verified {latest_core} exists and is readable")
        else:
            print(f"Error: {latest_core} reported but not accessible")
            return None
        return latest_core
    except Exception as e:
        print(f"Error finding {system} core: {e}")
        return None