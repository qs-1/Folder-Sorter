from threading import Thread
from PIL import Image
from config_manager import APP_ICON
from pystray import Icon, Menu, MenuItem

import file_sorter
import gui

# Global reference to the tray app and GUI thread to keep track of when they are running
tray_app = None
config_gui_thread = None

def run_sort_files():
    """Run the file sorting operation, showing a popup if needed in its own thread."""
    error_message = file_sorter.sort_files()
    if error_message:
        # path_prompt_popup on the main GUI thread if available
        if gui.app and gui.app.winfo_exists():
            gui.app.after(0, lambda msg=error_message: gui.path_prompt_popup(msg))
        else:
            # otherwise directly call path_prompt_popup which will now handle separate threading itself
            gui.path_prompt_popup(error_message)

def _config_gui_target():
    """Target function to run config_gui and manage gui.app state."""
    try:
        gui.launch_config_gui()
    finally:
        gui.app = None

def open_config_gui():
    """Open the configuration GUI in a separate thread if not already open."""
    global config_gui_thread

    # Check if the GUI window reference exists and the window is visible
    if gui.app and gui.app.winfo_exists():
        print("Config GUI is already open. Attempting to focus.")
        try:
            # Schedule lift/focus on the GUI's mainloop thread
            gui.app.after(0, gui.focus_app)
        except Exception as e:
            print(f"Error focusing existing GUI: {e}")
        return

    # Check if the thread exists but gui.app isnt created yet
    if config_gui_thread and config_gui_thread.is_alive():
        print("Config GUI thread is already running, but window may be hidden/closing.")
        return

    # Start a new thread for the GUI
    print("Starting new Config GUI thread.")
    config_gui_thread = Thread(target=_config_gui_target, daemon=True)
    config_gui_thread.start()

def quit_app():
    """Quit the application and stop the tray icon"""
    global tray_app, config_gui_thread
    print("Quit requested.")

    # close the standalone popup window if it's running
    if gui.standalone_popup_window and gui.standalone_popup_window.winfo_exists():
        print("Attempting to close standalone popup window...")
        gui._destroy_standalone_popup() # Use the safe destroy function from gui.py

    # close the GUI window if it's running
    if gui.app and gui.app.winfo_exists():
        print("Attempting to close GUI window...")
        try:
            gui.app.after(0, gui.app.destroy)
        except Exception as e:
            print(f"Error scheduling GUI destroy: {e}")
        finally:
            gui.app = None

    # Stop the tray icon
    if tray_app:
        print("Stopping tray icon...")
        tray_app.stop()

    # Wait a bit for the GUI thread to end after destroy command
    if gui.standalone_popup_thread and gui.standalone_popup_thread.is_alive():
        print("Waiting briefly for standalone popup thread...")
        gui.standalone_popup_thread.join(timeout=0.5)
    # Same for config GUI thread
    if config_gui_thread and config_gui_thread.is_alive():
        print("Waiting briefly for GUI thread...")
        config_gui_thread.join(timeout=0.5) 

    print("Quit process finished.")


def setup_tray():
    """Set up the system tray icon and menu"""
    global tray_app
    
    # Load icon image
    icon_image = Image.open(APP_ICON) 

    # Create menu items
    menu = Menu(
        MenuItem('Sort Folder', run_sort_files),
        MenuItem('Configure', open_config_gui), # will run in a separate thread
        MenuItem('Quit', quit_app)
    )

    # Create tray icon
    tray_app = Icon("FolderSorter", icon_image, menu=menu)
    tray_app.title = "Folder Sorter"
    
    print("Running tray icon...")
    # Run the tray icon (blocking call in this thread)
    tray_app.run()
    print("Tray icon stopped.")


def start_tray_thread():
    """Start the tray icon in a separate thread"""
    print("Starting tray thread...")
    tray_thread = Thread(target=setup_tray)
    tray_thread.daemon = False # Make it non-daemon so main thread waits for it
    tray_thread.start()
    return tray_thread

