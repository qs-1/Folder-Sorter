from os import path, makedirs, listdir
from shutil import move
from threading import Thread
from win11toast import toast
from config_manager import load_config

# Global variables for GUI callbacks and app instance
gui_app_instance = None
show_error_dialog = None
focus_app = None

def set_gui_callbacks(app_instance, error_dialog_func, focus_app_func):
    """Set GUI callback functions needed by the file sorter"""
    global gui_app_instance, show_error_dialog, focus_app
    gui_app_instance = app_instance
    show_error_dialog = error_dialog_func
    focus_app = focus_app_func

def _schedule_on_gui_thread(callback, *args):
    """Safely schedules a function call on the GUI thread if possible."""
    if gui_app_instance and gui_app_instance.winfo_exists():
        try:
            gui_app_instance.after(0, lambda cb=callback, a=args: cb(*a))
            return True # Scheduled
        except Exception as e:
            print(f"Error scheduling GUI call: {e}")
    else:
        # Fallback or error handling if GUI isn't running
        print(f"GUI not available to schedule call for {callback.__name__}")
    return False # Not scheduled


def generate_unique_filename(directory, filename):
    base, extension = path.splitext(filename)
    counter = 1
    new_filename = filename
    while path.exists(path.join(directory, new_filename)):
        new_filename = f"{base}_{counter}{extension}"
        counter += 1
    return new_filename

def show_notification(folder_path):
    buttons = [
        {'activationType': 'protocol', 'arguments': f'file:///{folder_path}', 'content': 'Open Folder'}
    ]

    if focus_app:
        _schedule_on_gui_thread(focus_app) # Schedule focus_app call

    toast(
        'Folder Sorted',
        f'Sorted: "{folder_path}"',
        buttons=buttons,
        audio={'silent': 'true'},
        duration='short'
    )

def sort_files():
    config_data = load_config()
    folder_path = config_data.get('folder_path', '')

    # Check if the folder_path is valid
    if not folder_path or not path.exists(folder_path):
        return "Folder path is not set or does not exist" 

    folder_extensions_mapping = config_data.get('folder_extensions_mapping', {})

    files_moved = False # Flag to check if any file was actually moved

    for file in listdir(folder_path):
        file_path = path.join(folder_path, file)
        if not path.isfile(file_path):
            continue

        # Check if file has an extension
        if '.' in file:
            file_extension = file.split('.')[-1]
            for folder, ext_list in folder_extensions_mapping.items():
                if file_extension.lower() in ext_list:
                    target_folder_path = path.join(folder_path, folder)
                    # --- This is the sufficient check ---
                    if not path.exists(target_folder_path):
                        try:
                            makedirs(target_folder_path)
                        except Exception as e:
                             if show_error_dialog:
                                _schedule_on_gui_thread(show_error_dialog, f"Error creating folder '{target_folder_path}': {str(e)}")
                             continue # Skip moving this file if folder creation failed

                    # Generate a unique filename if a file with the same name exists
                    target_file_path = path.join(target_folder_path, file)
                    if path.exists(target_file_path):
                        file = generate_unique_filename(target_folder_path, file)
                        target_file_path = path.join(target_folder_path, file)

                    try:
                        move(file_path, target_file_path)
                        files_moved = True # Mark that at least one file was moved
                    except Exception as e:
                        if show_error_dialog:
                            # Schedule show_error_dialog call
                            _schedule_on_gui_thread(show_error_dialog, f"Error moving file '{file}': {str(e)}")
                    break # Move to next file in listdir once matched

    # Show Windows notification only if files were actually moved
    if files_moved:
        notification_thread = Thread(target=show_notification, args=(folder_path,))
        notification_thread.start()

    return None  # No error message, sorting was successful or no files needed moving