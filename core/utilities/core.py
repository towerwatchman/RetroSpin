import os

MISTER_CORE_DIR = "/media/fat/_Console/"

# Mapping from lowercase system names to MiSTer core prefixes (capitalized)
SYSTEM_PREFIXES = {
    "psx": "PSX_",
    "jaguar": "Jaguar_",
    "tgcd": "TurboGrafx16_",
    "neogeo": "NeoGeo_",
    "3do": "3DO_",
    "cdi": "CDi_",
    "megacd": "MegaCD_",
    "saturn": "Saturn_"
}

def find_cores(systems=None):
    """Find the latest core .rbf file for each system in the provided list and return a dict of {system: core_path}."""
    if systems is None:
        systems = []
    available_cores = {}
    for system in systems:
        prefix = SYSTEM_PREFIXES.get(system)
        if not prefix:
            print(f"No prefix defined for system '{system}'. Skipping.")
            continue
        try:
            rbf_files = [f for f in os.listdir(MISTER_CORE_DIR) if f.startswith(prefix) and f.endswith(".rbf")]
            if not rbf_files:
                print(f"No {system} core found in {MISTER_CORE_DIR}. Please place a {prefix}*.rbf file there.")
                continue
            rbf_files.sort(reverse=True)  # Get the latest version
            latest_core = os.path.join(MISTER_CORE_DIR, rbf_files[0])
            if os.path.exists(latest_core):
                print(f"Found {system} core: {latest_core} (capitalized as {rbf_files[0]})")
                available_cores[system] = latest_core
            else:
                print(f"Error: {latest_core} reported but not accessible")
        except Exception as e:
            print(f"Error finding {system} core: {e}")
    print(f"Available cores: {list(available_cores.keys())}")
    return available_cores