from threading import Thread
from PIL import Image
from pystray import Icon, Menu, MenuItem

from config_manager import APP_ICON
import file_sorter
from gui import config_gui, show_popup

# Global reference to the tray app
tray_app = None

def run_sort_files():
    """Run the file sorting operation"""
    error_message = file_sorter.sort_files()
    if error_message:
        show_popup(error_message)

def quit_app():
    """Quit the application and stop the tray icon"""
    global tray_app
    if tray_app:
        tray_app.stop()

def open_config_gui():
    """Open the configuration GUI"""
    config_gui()

def setup_tray():
    """Set up the system tray icon and menu"""
    global tray_app
    
    # Load icon image
    icon_image = Image.open(APP_ICON) 

    # Create menu items
    menu = Menu(
        MenuItem('Sort Folder', run_sort_files),
        MenuItem('Configure', open_config_gui),
        MenuItem('Quit', quit_app)
    )

    # Create tray icon
    tray_app = Icon("FolderSorter", icon_image, menu=menu)
    tray_app.title = "Folder Sorter"
    
    # Run the tray icon (blocking call)
    tray_app.run()

def start_tray_thread():
    """Start the tray icon in a separate thread"""
    tray_thread = Thread(target=setup_tray)
    tray_thread.daemon = True  # Make thread exit when main thread exits
    tray_thread.start()
    return tray_thread