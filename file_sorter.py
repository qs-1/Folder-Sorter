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
    # Check if the instance variable is set, but don't call winfo_exists here
    if gui_app_instance:
        try:
            gui_app_instance.after(0, lambda cb=callback, a=args: cb(*a))
            return True # Scheduling attempted
        except Exception as e:
            # Catch potential errors if the Tk object is already gone
            print(f"Error scheduling GUI call for {callback.__name__}: {e}")
    else:
        # Fallback or error handling if GUI isn't running or instance not set
        print(f"GUI instance not available to schedule call for {callback.__name__}")
    return False # Not scheduled or instance not available

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

    if not folder_path or not path.exists(folder_path):
        return "Folder path is not set or does not exist" 

    folder_extensions_mapping = config_data.get('folder_extensions_mapping', {})
    files_moved = False
    failed_folder_creations = set() # Keep track of folders that failed to be created

    try:
        source_files = listdir(folder_path)
        if not source_files:
            print(f"No files found in '{folder_path}' to sort.")
            return None # Nothing to do
    except OSError as e:
        err_msg = f"Error reading source folder '{folder_path}': {str(e)}"
        if show_error_dialog:
            _schedule_on_gui_thread(show_error_dialog, err_msg)
        else:
            print(err_msg)
        return f"Could not read source folder: {folder_path}"

    print(f"Starting sort for {len(source_files)} items in '{folder_path}'...")

    for original_filename in source_files:
        file_path = path.join(folder_path, original_filename)

        try:
            if not path.isfile(file_path):
                # print(f"Skipping non-file item: '{original_filename}'") # Debug
                continue
        except OSError as e:
            print(f"Could not determine if '{original_filename}' is a file: {e}. Skipping.")
            if show_error_dialog:
                 _schedule_on_gui_thread(show_error_dialog, f"Error accessing '{original_filename}': {str(e)}. Skipping.")
            continue

        # Process only files with extensions
        if '.' in original_filename:
            file_extension = original_filename.split('.')[-1].lower() # Normalize extension for comparison
            
            for category_folder_name, configured_extensions in folder_extensions_mapping.items():
                normalized_configured_extensions = [ext.lower() for ext in configured_extensions]

                if file_extension in normalized_configured_extensions:
                    target_folder_path = path.join(folder_path, category_folder_name)
                    # Normalize path for reliable checking in failed_folder_creations (OS-dependent case handling)
                    normalized_target_folder_path_for_check = path.normcase(target_folder_path)

                    if normalized_target_folder_path_for_check in failed_folder_creations:
                        # If we already know we can't create this folder,
                        # break from inner loop (categories), skip category
                        print(f"Skipping category '{category_folder_name}' for '{original_filename}' as folder creation previously failed.")
                        break 

                    try:
                        # Attempt to create the directory. exist_ok=True means no error if it already exists.
                        makedirs(target_folder_path, exist_ok=True)
                    except OSError as e:
                        err_msg = f"Error creating folder '{target_folder_path}': {str(e)}. Files for this category will be skipped."
                        if show_error_dialog:
                            _schedule_on_gui_thread(show_error_dialog, err_msg)
                        else:
                            print(err_msg)
                        failed_folder_creations.add(normalized_target_folder_path_for_check)
                        break # Break from inner loop (categories), process next file

                    current_filename_to_move = original_filename
                    destination_file_path = path.join(target_folder_path, current_filename_to_move)

                    if path.exists(destination_file_path):
                        current_filename_to_move = generate_unique_filename(target_folder_path, current_filename_to_move)
                        destination_file_path = path.join(target_folder_path, current_filename_to_move)

                    try:
                        print(f"Attempting to move: '{file_path}' to '{destination_file_path}'")
                        move(file_path, destination_file_path)
                        files_moved = True
                        print(f"Successfully moved: '{original_filename}' to '{destination_file_path}'")
                    except OSError as e:
                        err_msg = f"Error moving file '{original_filename}' to '{target_folder_path}': {str(e)}"
                        if show_error_dialog:
                            _schedule_on_gui_thread(show_error_dialog, err_msg)
                        else:
                            print(err_msg)
                    except Exception as e: 
                        err_msg = f"Unexpected error moving file '{original_filename}' to '{target_folder_path}': {str(e)}"
                        if show_error_dialog:
                            _schedule_on_gui_thread(show_error_dialog, err_msg)
                        else:
                            print(err_msg)
                    
                    # Once a file is matched and its move attempted (succeeded or failed),
                    # break from the inner loop (iterating through folder_extensions_mapping)
                    # and move to the next file in the source_files list.
                    break 
    
    if files_moved:
        print("File sorting process completed. Some files were moved.")
        notification_thread = Thread(target=show_notification, args=(folder_path,))
        notification_thread.daemon = True
        notification_thread.start()
    else:
        # No files matched any criteria, or all matched files failed to move,
        # or the source_files list was empty initially
        print("File sorting process completed. No files were moved.")


    return None # successful sort