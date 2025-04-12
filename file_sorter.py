import os
from os import path, makedirs, listdir
from shutil import move
from threading import Thread
from win11toast import toast

from config_manager import config, save_config

# Global variable for error dialog function (will be set from GUI)
show_error_dialog = None
prompt_user_for_existing_folder = None
render_scrollable_widget = None
focus_app = None

def set_gui_callbacks(error_dialog_func, prompt_folder_func, refresh_scrollable_func, focus_app_func):
    """Set GUI callback functions needed by the file sorter"""
    global show_error_dialog, prompt_user_for_existing_folder, render_scrollable_widget, focus_app
    show_error_dialog = error_dialog_func
    prompt_user_for_existing_folder = prompt_folder_func
    render_scrollable_widget = refresh_scrollable_func
    focus_app = focus_app_func

def ensure_unique_folder_names(config):
    need_scrollable_refresh = False
    folder_path = config['folder_path']
    folder_extensions_mapping = config['folder_extensions_mapping']
    updated_mapping = {}
    for folder in folder_extensions_mapping.keys():
        unique_folder = folder
        if path.exists(path.join(folder_path, unique_folder)):
            use_existing = prompt_user_for_existing_folder(folder)
            if not use_existing:
                base_folder = folder
                counter = 1
                while path.exists(path.join(folder_path, unique_folder)):
                    unique_folder = f"{base_folder}_{counter}"
                    counter += 1
                if not need_scrollable_refresh: #if any folder name is changed, then refresh the scrollable widget
                    need_scrollable_refresh = True
        updated_mapping[unique_folder] = folder_extensions_mapping[folder]
    save_config(config['folder_path'], updated_mapping)
    return need_scrollable_refresh

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
        focus_app()

    toast(
        'Folder Sorted',
        f'Sorted: "{folder_path}"',
        buttons=buttons,
        audio={'silent': 'true'},
        duration='short'
    )

def sort_files():
    from config_manager import config, load_config
    config_data = load_config()
    folder_path = config_data.get('folder_path', '')

    # Check if the folder_path is valid
    if not folder_path or not path.exists(folder_path):
        return "Folder path is not set or does not exist"

    # Check for existing folders only if the path is not in duplicates_checked_paths
    # (meaning check only if current path hasn't been sorted by user before)
    need_scrollable_refresh = False
    if folder_path not in config_data['duplicates_checked_paths']:
        need_scrollable_refresh = ensure_unique_folder_names(config_data)
        save_config(duplicates_checked_path=folder_path)

    folder_extensions_mapping = config_data.get('folder_extensions_mapping', {}) # load after checking duplicates incase any change

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
                    if not path.exists(target_folder_path):
                        makedirs(target_folder_path)
                    
                    # Generate a unique filename if a file with the same name exists
                    target_file_path = path.join(target_folder_path, file)
                    if path.exists(target_file_path):
                        file = generate_unique_filename(target_folder_path, file)
                        target_file_path = path.join(target_folder_path, file)
                    
                    try:
                        move(file_path, target_file_path)
                    except Exception as e:
                        if show_error_dialog:
                            show_error_dialog(f"Error moving file '{file}': {str(e)}")
                    break

    # Refresh UI if needed and if GUI is active
    if need_scrollable_refresh and render_scrollable_widget:
        try:
            render_scrollable_widget()
        except Exception:
            pass
    
    # Show Windows notification
    notification_thread = Thread(target=show_notification, args=(folder_path,))
    notification_thread.start()
    
    return None  # No error message