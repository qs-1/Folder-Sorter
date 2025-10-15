from threading import Thread
from PIL import Image
from config_manager import APP_ICON, SORT_LOG_FILE, config, save_config
from pystray import Icon, Menu, MenuItem
import os

import file_sorter

# Global reference to the tray app and GUI thread to keep track of when they are running
tray_app = None
config_gui_thread = None
auto_sort_enabled = config.get('auto_sort_enabled', False)
watcher_is_paused = False


def restart_watcher_if_running():
    """Stops and restarts the file watcher if auto-sort is enabled.
    This is used when the folder path changes."""
    global auto_sort_enabled, watcher_is_paused
    if auto_sort_enabled and not watcher_is_paused:
        print("Folder path changed, restarting watcher...")
        file_sorter.stop_watching()
        file_sorter.start_watching()


def pause_watching():
    """Pauses the file watcher without changing the user's enabled setting."""
    global watcher_is_paused
    if auto_sort_enabled and not watcher_is_paused:
        file_sorter.stop_watching()
        watcher_is_paused = True
        print("Auto-sort paused.")


def resume_watching():
    """Resumes the file watcher if it was paused."""
    global watcher_is_paused
    if auto_sort_enabled and watcher_is_paused:
        file_sorter.start_watching()
        watcher_is_paused = False
        print("Auto-sort resumed.")


def force_disable_auto_sort():
    """Called when the watched folder is deleted."""
    global auto_sort_enabled, watcher_is_paused
    if auto_sort_enabled:
        file_sorter.stop_watching()
        auto_sort_enabled = False
        watcher_is_paused = False
        save_config(auto_sort_enabled=False)
        print("Auto-sort has been forcibly disabled.")


import gui

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
            gui.app.after(0, gui.app.focus_app)
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


def toggle_auto_sort(icon, item):
    global auto_sort_enabled, watcher_is_paused
    parent = gui.app if gui.app and gui.app.winfo_exists() else None
    if not auto_sort_enabled:
        if config.get('show_auto_sort_confirmation', True):
            if not gui.show_auto_sort_confirmation_dialog(parent):
                return

    auto_sort_enabled = not auto_sort_enabled
    save_config(auto_sort_enabled=auto_sort_enabled)
    if auto_sort_enabled:
        if parent:
            file_sorter.stop_watching()
            watcher_is_paused = True
            print("Auto-sort enabled but paused while configuration window is open.")
        else:
            file_sorter.start_watching()
            watcher_is_paused = False
    else:
        file_sorter.stop_watching()
        watcher_is_paused = False

def quit_app():
    """Quit the application and stop the tray icon"""
    global tray_app, config_gui_thread # gui.standalone_popup_thread is managed within gui.py mostly
    print("Quit requested.")

    # Close the standalone popup window if it's running
    if gui.standalone_popup_window and gui.standalone_popup_window.winfo_exists():
        print("Attempting to close standalone popup window...")
        gui._destroy_standalone_popup() # This schedules destroy and sets gui.standalone_popup_window to None

    # Close the main GUI window if it's running
    if gui.app and gui.app.winfo_exists():
        print("Attempting to schedule main GUI window destruction...")
        try:
            # Schedule destroy; the GUI thread itself will handle cleanup including setting gui.app to None
            gui.app.after(0, gui.app.destroy)
        except Exception as e:
            print(f"Error scheduling GUI destroy: {e}")

    # Wait for the standalone popup thread to end
    if gui.standalone_popup_thread and gui.standalone_popup_thread.is_alive():
        print("Waiting for standalone popup thread to finish...")
        gui.standalone_popup_thread.join(timeout=2.0)
        if gui.standalone_popup_thread.is_alive():
            print("Warning: Standalone popup thread did not finish in time.")
        else:
            print("Standalone popup thread finished.")
    gui.standalone_popup_thread = None # Ensure reference is cleared

    # Wait for the main config GUI thread to end
    if config_gui_thread and config_gui_thread.is_alive():
        print("Waiting for main GUI thread to finish...")
        config_gui_thread.join(timeout=2.0) # Increased timeout
        if config_gui_thread.is_alive():
            print("Warning: Main GUI thread did not finish in time.")
        else:
            print("Main GUI thread finished.")
    config_gui_thread = None # Ensure reference is cleared

    # Stop the tray app
    if tray_app:
        print("Stopping tray icon...")
        tray_app.stop()
        
    print("Quit process finished.")


def setup_tray():
    """Set up the system tray icon and menu"""
    global tray_app
    
    # Load icon image
    icon_image = Image.open(APP_ICON) 

    # Create menu items
    menu = Menu(
        MenuItem('Sort Folder', run_sort_files, enabled=lambda item: not auto_sort_enabled),
        MenuItem(
            'Undo Last Sort',
            file_sorter.undo_last_sort,
            enabled=lambda item: os.path.exists(SORT_LOG_FILE) and not auto_sort_enabled
        ),
        MenuItem('Enable Auto-Sort', toggle_auto_sort, checked=lambda item: auto_sort_enabled),
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
    tray_thread = Thread(target=setup_tray, daemon=True)
    tray_thread.start()
    return tray_thread


if auto_sort_enabled:
    file_sorter.start_watching()

