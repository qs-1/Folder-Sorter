import sys
from os import path
from json import dump, load, JSONDecodeError
from PIL import ImageFont

def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = path.dirname(__file__)

    return path.join(base_path, relative_path)

# Define constants for file paths
CONFIG_FILE = resource_path('config.json')
APP_ICON = resource_path('icons/purp-sort.ico')
DELETE_PNG = resource_path('icons/x.png')

# Define the paths to the font files
REGULAR_PATH = resource_path('fonts/CascadiaCode-Regular.ttf')
SEMIBOLD_PATH = resource_path('fonts/CascadiaCode-SemiBold.ttf')

# Define reserved Windows names
reserved_names = {
    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7",
    "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

# Load the fonts using PIL
try:
    REGULAR_FONT = ImageFont.truetype(REGULAR_PATH, size=12)
    SEMIBOLD_FONT = ImageFont.truetype(SEMIBOLD_PATH, size=12)
except OSError as e:
    print(f"Error loading fonts: {e}")
    sys.exit(1)

# Global config variable
config = None

def save_config(folder_path=None, folder_extensions_mapping=None, duplicates_checked_path=None, dont_show_again=None, window_geometry=None): 
    global config
    if config is None: # Ensure config is loaded if save is called before load 
        load_config()
    # Update config keys
    if folder_path is not None: # Check for None explicitly if empty string is valid
        config['folder_path'] = folder_path
    if folder_extensions_mapping is not None:
        config['folder_extensions_mapping'] = folder_extensions_mapping
    if duplicates_checked_path:
        # Ensure the list exists before appending
        if 'duplicates_checked_paths' not in config or not isinstance(config['duplicates_checked_paths'], list):
            config['duplicates_checked_paths'] = []
        config['duplicates_checked_paths'].append(duplicates_checked_path)
    if dont_show_again is not None:
        config['dont_show_again'] = dont_show_again
    if window_geometry is not None: 
        config['window_geometry'] = window_geometry

    try:
        # Ensure config is not None before saving
        if config is not None:
            with open(CONFIG_FILE, 'w') as f:
                dump(config, f, indent=4) 
        else:
            print("Error: Config is None, cannot save.")
    except IOError as e:
        print(f"Error saving config: {e}")
    except TypeError as e:
        print(f"Error serializing config to JSON: {e}")


def load_config():
    global config
    # If config is already loaded and seems valid, return it
    if config and 'folder_path' in config and 'folder_extensions_mapping' in config:
         # Ensure all expected keys exist, adding defaults if missing
         config.setdefault('duplicates_checked_paths', [])
         config.setdefault('dont_show_again', False)
         config.setdefault('window_geometry', None)
         return config

    default_config = {
        'folder_path': None,
        'folder_extensions_mapping': {
            'Archive': ['rar', 'zip', '7z'],
            'Torrents': ['torrent'],
            'PDFs': ['pdf'],
            'MS office files/Word Docs': ['doc', 'docx'],
            'MS office files/Excel': ['xlsx', 'ods'],
            'MS office files/PPT': ['ppt', 'pptx'],
            'MS office files/csv': ['csv'],
            'Images': ['png', 'jpg', 'jpeg', 'bmp'],
            'Images/Gifs': ['gif'],
            'Images/PSD': ['psd'],
            'Images/ICO': ['ico'],
            'MP3s': ['mp3'],
            'Videos': ['mp4', 'mov', 'avi', 'mkv'],
            'Installer Files': ['exe', 'msi'],
            'Java Files': ['java', 'jar'],
            'Text': ['txt', 'reg']
        },
        'duplicates_checked_paths': [],
        'dont_show_again': False,
        'window_geometry': None
    }

    if path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                loaded_data = load(f)
                # Basic validation
                if isinstance(loaded_data, dict) and 'folder_path' in loaded_data and 'folder_extensions_mapping' in loaded_data:
                    config = loaded_data
                    # Ensure all expected keys exist, adding defaults if missing
                    config.setdefault('duplicates_checked_paths', [])
                    config.setdefault('dont_show_again', False)
                    config.setdefault('window_geometry', None)
                    print("Config loaded successfully.")
                    return config
                else:
                    print("Invalid config file format. Loading default config.")
        except (IOError, JSONDecodeError) as e:
            print(f"Error loading config: {e}. Loading default config.")

    # Use default if file doesn't exist, is invalid, or error occurred
    print("Loading default configuration.")
    config = default_config
    # Save the default config immediately so the file exists
    save_config(
        folder_path=config['folder_path'],
        folder_extensions_mapping=config['folder_extensions_mapping'],
        dont_show_again=config['dont_show_again'],
        window_geometry=config['window_geometry'] # Save the default None
    )
    return config

# Initialize config when module is imported
config = load_config()