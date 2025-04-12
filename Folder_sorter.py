# Folder Sorter 0.1.0
import sys
from re import compile
from os import path, listdir, makedirs
from json import dump, load, JSONDecodeError
from shutil import move
from threading import Thread
from CTkToolTip import *
from PIL import Image, ImageFont
from win11toast import toast
import customtkinter as ctk
from pystray import Icon, Menu, MenuItem

def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = path.dirname(__file__)

    return path.join(base_path, relative_path)

CONFIG_FILE = resource_path('config.json')
APP_ICON = resource_path('purp-sort.ico')
DELETE_PNG = resource_path('x.png')

# Define the paths to the font files
REGULAR_PATH = resource_path('CascadiaCode-Regular.ttf')
SEMIBOLD_PATH = resource_path('CascadiaCode-SemiBold.ttf')


# Load the fonts using PIL
try:
    REGULAR_FONT = ImageFont.truetype(REGULAR_PATH, size=12)
    SEMIBOLD_FONT = ImageFont.truetype(SEMIBOLD_PATH, size=12)
except OSError as e:
    print(f"Error loading fonts: {e}")
    sys.exit(1)


app = None
popup = None
dialog = None

reserved_names = {
    "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7",
    "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}


#region Configuration Funcs
def save_config(folder_path=None, folder_extensions_mapping=None, duplicates_checked_path=None, dont_show_again=None):
    global config
    # Update config keys
    if folder_path:
        config['folder_path'] = folder_path
    if folder_extensions_mapping:
        config['folder_extensions_mapping'] = folder_extensions_mapping
    if duplicates_checked_path:
        config['duplicates_checked_paths'].append(duplicates_checked_path)
    if dont_show_again is not None:
        config['dont_show_again'] = dont_show_again

    try:
        with open(CONFIG_FILE, 'w') as f:
            dump(config, f)
    except IOError as e:
        print(f"Error saving config: {e}")

def load_config():
    global config
    if path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = load(f)
                # Validate config keys
                if 'folder_path' in config and 'folder_extensions_mapping' in config:
                    return config
                else:
                    print("Invalid config file format. Loading default config.")
        except (IOError, JSONDecodeError) as e:
            print(f"Error loading config: {e}")
    else:
        # Loading default configuration (since no config file exists)
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
            'dont_show_again': False
        }
        #update global config
        config = default_config
        #write to file
        save_config(default_config['folder_path'], default_config['folder_extensions_mapping'], dont_show_again=default_config['dont_show_again'])
        return config
#endregion




#region helper functions
def refresh_path_entry(new_path):
    if not new_path:
        new_path = ""
    try:
        path_entry.configure(state='normal')   #how dis working without global??
        path_entry.delete(0, ctk.END)
        path_entry.insert(0, new_path)
        path_entry.configure(state='disabled') 
        global tooltip
        tooltip.configure(message=new_path if new_path else "No Path Set")

    except:
        pass #edge case when closing the app and trying to refresh the path entry (from path error popup)

def select_folder():
    folder_path = ctk.filedialog.askdirectory()
    if folder_path:
        # print(f"Selected folder: {folder_path}")
        global config
        config['folder_path'] = folder_path
        save_config(config['folder_path'], config['folder_extensions_mapping'])
        # print(config)
        global popup
        if popup:
            refresh_path_entry(folder_path)
            popup.destroy()
            popup = None
        elif path_entry:
            refresh_path_entry(folder_path)
#endregion




#customtkinter bug, refreshes toplevel icon from default icon after 200 ms of creation, overriding our iconbitmap which ran before it
class ToplevelIco(ctk.CTkToplevel):
    def __init__(self, master=None, icon_path=None):
        super().__init__(master)
        if icon_path:
            self.after(201, lambda: self.iconbitmap(icon_path))

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.master.winfo_x() + self.master.winfo_width() // 2) - (width // 2)
        y = (self.master.winfo_y() + self.master.winfo_height() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')


#region GUI
def config_gui():
    # Load the configuration
    global config
    config = load_config()

    # Initialize the main application window
    global app # to use it in popup window for grab set and wait window
    app = ctk.CTk()
    app.title("Configure Folder Sorter")
    app.geometry("547x700")
    app.iconbitmap(APP_ICON)
    app.resizable(False, True)

    global focus_app
    def focus_app():
        global app
        app.focus_force()

    def on_app_quit():
        global app
        app.destroy()
        app = None
    
    app.protocol("WM_DELETE_WINDOW", on_app_quit)

    # Create customtkinter font objects using loaded fonts
    try:
        ctk_font_regular_11 = ctk.CTkFont(family=REGULAR_FONT.getname()[0], size=11)
        ctk_font_regular_12 = ctk.CTkFont(family=REGULAR_FONT.getname()[0], size=12)
        ctk_font_semibold_12 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=12)
        ctk_font_semibold_13 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=13)
        ctk_font_semibold_14 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=14)
    except Exception as e:
        print(f"Error creating CTkFont objects: {e}")
        sys.exit(1)

    delete_icon = ctk.CTkImage(
        light_image=Image.open(DELETE_PNG),
        dark_image=Image.open(DELETE_PNG),
        size=(10,10)
    )

    #region path selection
    # Create a frame for folder selection
    path_frame = ctk.CTkFrame(app)
    path_frame.pack(fill="x", padx=10, pady=10)

    # Create a label to display the text 'Select Folder:'
    path_label = ctk.CTkLabel(path_frame, text="Folder Path:", font=ctk_font_semibold_14)
    path_label.pack(side="left", padx=(10, 5), pady=7)

    # Create an entry widget to display the selected folder path
    global path_entry # for refreshing
    path_entry = ctk.CTkEntry(path_frame, font=ctk_font_regular_11)
    path_entry.pack(side="left", fill="x", expand=True, padx=5, pady=7)
    path_entry.configure(state='disabled')

    global tooltip
    tooltip = CTkToolTip(path_entry, message=config['folder_path'] if config['folder_path'] else "No Path Set", x_offset=-5, y_offset=20,alpha=0.87, font=('Cascadia Code', 12))
    refresh_path_entry(config['folder_path'])

    # Create a button to open the folder selection dialog
    browse_button = ctk.CTkButton(path_frame, text="Browse", width=12, font=ctk_font_regular_12, command=lambda: select_folder())
    browse_button.pack(side="right", padx=(7,8), pady=7)
    #endregion

    global show_error_dialog # to use it in sort function error handling
    def show_error_dialog(message):
        dialog = ToplevelIco(app, APP_ICON)
        dialog.title("Error")
        
        # Adjust the dialog's width dynamically based on the text length
        dialog.geometry("400x150")
        dialog.minsize(400, 150)
        dialog.resizable(False, False)
        dialog.iconbitmap(APP_ICON)
        
        # Create a label with wrapping text
        label = ctk.CTkLabel(dialog, 
                            text=message, 
                            font=ctk_font_semibold_14,
                            wraplength=380)  # Adjust the wraplength based on the dialog width
        label.pack(pady=(20, 10), padx=10)

        # Create a frame for the button
        button_frame = ctk.CTkFrame(dialog, fg_color="#242424")
        button_frame.pack(pady=10, fill='x')

        def on_ok():
            dialog.destroy()

        # Create OK button
        ok_button = ctk.CTkButton(button_frame, 
                                text="OK", 
                                width=80, 
                                font=ctk_font_semibold_12, 
                                command=on_ok)
        ok_button.pack(pady=10)

        # Allow the dialog to resize dynamically
        dialog.update_idletasks()
        
        # Calculate the exact height required, with minimal extra space
        dialog.geometry(f"{max(400, label.winfo_reqwidth() + 20)}x{label.winfo_reqheight() + button_frame.winfo_reqheight() + 60}")

        # Keep a reference to the dialog window
        dialog.transient(app)
        dialog.grab_set()
        dialog.focus_force()
        app.wait_window(dialog)

    def show_folder_exists_dialog(folder_path, folder_name):
        dialog = ToplevelIco(app, APP_ICON)
        dialog.title("Folder Already Exists")
        
        # Adjust the dialog's width dynamically based on the text length
        dialog.geometry("400x150")
        dialog.minsize(400, 150)
        dialog.resizable(False, False)
        dialog.iconbitmap(APP_ICON)
        
        # Create a label with wrapping text
        label = ctk.CTkLabel(dialog, 
                            text=f"Folder '{folder_name}' already exists in the path '{folder_path}'.", 
                            font=ctk_font_semibold_14,
                            wraplength=380)  # Adjust the wraplength based on the dialog width
        label.pack(pady=(20, 10), padx=10)

        # Create a frame for the buttons
        button_frame = ctk.CTkFrame(dialog, fg_color="#242424")
        button_frame.pack(pady=10, fill='x')

        # Default result is False (rename)
        dialog.result = False

        def use_same_folder():
            # Proceed with using the existing folder
            # print(f"Using existing folder: {path.join(folder_path, folder_name)}")
            dialog.result = True
            dialog.destroy()

        def rename():
            # Close the Toplevel window
            dialog.result = False
            dialog.destroy()

        # Create "Use Same Folder" button
        use_button = ctk.CTkButton(button_frame, 
                                text="Use Same Folder", 
                                width=120, 
                                font=ctk_font_semibold_12, 
                                command=use_same_folder)
        use_button.pack(side="left", padx=(80,0), pady=10)

        # Create "Cancel" button
        rename_button = ctk.CTkButton(button_frame, 
                                    text="Cancel", 
                                    width=80, 
                                    fg_color="#343638",
                                    hover_color="#2d2a2e",
                                    font=ctk_font_semibold_12, 
                                    command=rename)
        rename_button.pack(side="right", padx=(0,100), pady=10)

        # Allow the dialog to resize dynamically
        dialog.update_idletasks()
        
        # Calculate the exact height required, with minimal extra space
        dialog.geometry(f"{max(400, label.winfo_reqwidth() + 20)}x{label.winfo_reqheight() + button_frame.winfo_reqheight() + 60}")

        # Bind the close event to the on_close function
        dialog.protocol("WM_DELETE_WINDOW", rename)

        # Keep a reference to the dialog window
        dialog.transient(app)
        dialog.grab_set()
        dialog.focus_force()
        app.wait_window(dialog)
        
        return dialog.result  

    def validate_input(folder_name, extensions, original_folder=None):    
        if not folder_name.strip():
            return False, "Folder name cannot be empty."
        
        # Check if folder name already exists in the path
        folder_path = config.get('folder_path', '')
        if folder_path and path.exists(path.join(folder_path, folder_name)):
            use_same_folder = show_folder_exists_dialog(folder_path, folder_name)
            if use_same_folder:
                pass
                # print("User wants to use the existing folder.")
            else:
                # Return None to indicate that the user has already been informed
                # print("User wants to rename folder.")
                return None, ""

        # Allow slashes in folder names but check for other invalid characters
        invalid_folder_chars_pattern = compile(r'[\\:*?"<>|]')
        invalid_extension_chars_pattern = compile(r'[\\/:*?"<>|]')

        # Validate folder name
        if invalid_folder_chars_pattern.search(folder_name):
            return False, f"Folder name '{folder_name}' contains invalid characters. Only alphanumeric characters and slashes are allowed."
        if folder_name.upper() in reserved_names:
            return False, f"Folder name '{folder_name}' is a reserved name and cannot be used."
        if '//' in folder_name or '\\' in folder_name:
            return False, f"Folder name '{folder_name}' contains multiple consecutive slashes or backslashes."
        if folder_name.strip('/') == '':
            return False, "Folder name cannot be just slashes."
        if folder_name.startswith('/') or folder_name.endswith('/'):
            return False, "Folder name cannot start or end with a slash."

        # Check if folder name already exists in the config
        for folder in config['folder_extensions_mapping']:
            # Adding a new folder, check entire mapping
            if original_folder is None:
                if folder_name.lower() == folder.lower():
                    return False, f"Folder name '{folder_name}' already exists in the configuration."
            # editing an existing folder, skip the original folder
            else:
                if folder.lower() != original_folder[0].lower() and folder_name.lower() == folder.lower():
                    return False, f"Folder name '{folder_name}' already exists in the configuration."
        
        # Validate extensions
        for ext in extensions:
            if invalid_extension_chars_pattern.search(ext):
                return False, f"Extension '{ext}' contains invalid characters. Only alphanumeric characters are allowed."
            if ext.upper() in reserved_names:
                return False, f"Extension '{ext}' is a reserved name and cannot be used."
            
            # Check if extension already exists in another folder
            for existing_folder, existing_extensions in config['folder_extensions_mapping'].items():
                if original_folder is None:
                    # Adding a new folder, check entire mapping
                    if ext in existing_extensions:
                        return False, f"Extension '{ext}' is already assigned to folder '{existing_folder}'."
                else:
                    # Editing an existing folder, skip the original folder
                    if existing_folder != folder_name and existing_folder != original_folder[0] and ext in existing_extensions:
                        return False, f"Extension '{ext}' is already assigned to folder '{existing_folder}'."
        
        return True, ""

    #region add new category
    # Function to add a new folder and its extensions
    def add_category():
        folder_name = new_category_entry.get().strip()
        extensions_input = new_extensions_entry.get().strip()
        extensions = [ext.strip().replace(' ', '').lower() for ext in extensions_input.split(',') if ext.strip()]
        # print('adding', folder_name, extensions)
        
        # Validate folder name and extensions
        is_valid, error_message = validate_input(folder_name, extensions)
        if is_valid is None:
            # User has already been informed, return without showing the error dialog
            return
        if not is_valid:
            show_error_dialog(error_message)
            return
        

        
        # Add new folder and extensions to config['folder_extensions_mapping']
        config['folder_extensions_mapping'][folder_name] = extensions
        save_config(config['folder_path'], config['folder_extensions_mapping'])
        
        # Refresh scrollable widget
        render_scrollable_widget()

        # Clear the input fields
        new_category_entry.delete(0, ctk.END)
        new_extensions_entry.delete(0, ctk.END)

    # Create a frame for adding new categories and extensions
    add_frame = ctk.CTkFrame(app)
    add_frame.pack(fill="x", padx=10, pady=(0,13))

    # Configure the grid layout
    add_frame.columnconfigure(0, weight=1)
    add_frame.columnconfigure(1, weight=3)

    # Entry for new category name 
    new_category_label = ctk.CTkLabel(add_frame, text="New Category Name:", font=ctk_font_semibold_13)
    new_category_label.grid(row=0, column=0, sticky="w", padx=(10, 5), pady=7)
    new_category_entry = ctk.CTkEntry(add_frame, height=25, font=ctk_font_regular_12)
    new_category_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=7)

    # Entry for new extensions 
    new_extensions_label = ctk.CTkLabel(add_frame, text="Extensions (comma separated):", font=ctk_font_semibold_13)
    new_extensions_label.grid(row=1, column=0, sticky="w", padx=(10, 5), pady=7)
    new_extensions_entry = ctk.CTkEntry(add_frame, height=25, font=ctk_font_regular_12)
    new_extensions_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=7)

    # Button to add new category and extensions 
    add_button = ctk.CTkButton(add_frame, text="Add", width=6, font=ctk_font_regular_12, command=add_category)
    add_button.grid(row=2, column=1, sticky="e", padx=6, pady=(0,7))
    #endregion

    #region edit categories
    # delete category confirmation dialog
    def show_confirmation_dialog(folder_name, on_confirm):
        dialog = ToplevelIco(app, APP_ICON)
        dialog.title("Confirm Delete")
        
        # Adjust the dialog's width dynamically based on the text length
        dialog.geometry("400x150")
        dialog.minsize(400, 150)
        dialog.resizable(False, False)
        dialog.iconbitmap(APP_ICON)
        dialog.center_window()
        
        # Create a label with wrapping text
        label = ctk.CTkLabel(dialog, 
                            text=f"Are you sure you want to delete the category '{folder_name}'?", 
                            font=ctk_font_semibold_14,
                            wraplength=380)  # Adjust the wraplength based on the dialog width
        label.pack(pady=(20, 10), padx=10)
    
        # Add "Don't show again" checkbox
        dont_show_again_var = ctk.StringVar(value="0")
        dont_show_again_checkbox = ctk.CTkCheckBox(dialog, 
                                                text="Don't ask again", 
                                                checkbox_width=18,
                                                checkbox_height=18,
                                                variable=dont_show_again_var, 
                                                onvalue="1", offvalue="0",
                                                font=("Cascadia Code", 12))
        dont_show_again_checkbox.pack(pady=(15,10))
    
        # Create a frame for the buttons
        button_frame = ctk.CTkFrame(dialog, fg_color="#242424")
        button_frame.pack(pady=10, fill='x')
    
        def on_yes():
            on_confirm()
            config['dont_show_again'] = dont_show_again_var.get() == "1"
            save_config(config['folder_path'], config['folder_extensions_mapping'], dont_show_again=config['dont_show_again'])
            dialog.destroy()
    
        def on_no():
            dialog.destroy()
    
        # Create Yes and No buttons
        yes_button = ctk.CTkButton(button_frame, 
                                text="Yes", 
                                width=80, 
                                font=ctk_font_semibold_12, 
                                command=on_yes)
        yes_button.pack(side="left", padx=(100, 0), pady=10)
    
        no_button = ctk.CTkButton(button_frame, 
                                text="No", 
                                width=80, 
                                fg_color="#343638",
                                hover_color="#2d2a2e",
                                font=ctk_font_semibold_12, 
                                command=on_no)
        no_button.pack(side="right", padx=(0, 100), pady=10)
    
        # Bind the close event to the on_close function
        dialog.protocol("WM_DELETE_WINDOW", on_no)
    
        # Allow the dialog to resize dynamically
        dialog.update_idletasks()
        
        # Calculate the exact height required, with minimal extra space
        dialog.geometry(f"{max(400, label.winfo_reqwidth() + 20)}x{label.winfo_reqheight() + dont_show_again_checkbox.winfo_reqheight() + button_frame.winfo_reqheight() + 60}")
    
        # Keep a reference to the dialog window
        dialog.transient(app)
        dialog.grab_set()
        dialog.focus_force()
        app.wait_window(dialog)

    def delete_category(frame, folder_entry):
        folder_name = folder_entry.get().strip()
        
        def on_confirm():
            frame.destroy()
            config['folder_extensions_mapping'].pop(folder_name, None)
            save_config(config['folder_path'], config['folder_extensions_mapping'])
        
        if config.get('dont_show_again', False):
            on_confirm()
        else:
            show_confirmation_dialog(folder_name, on_confirm)
    #endregion

    #region scrollable widget
    def handle_change(is_changed, save_button, remove_button, reset_button):
        if is_changed:
            save_button.pack(side="left", padx=2, pady=5)
            remove_button.place_forget()  # Hide the remove button
            reset_button.pack(side="right", padx=2, pady=5)  # Show the reset button
        else:
            save_button.pack_forget()
            reset_button.pack_forget()  # Hide the reset button
            remove_button.place(relx=0.5, rely=0.5, anchor="center")  # Center the remove button
    def on_entry_change(folder_entry_var, original_folder_name, save_button, remove_button, reset_button):
        new_folder_name = folder_entry_var.get().strip()
        is_changed = new_folder_name != original_folder_name[0]
        handle_change(is_changed, save_button, remove_button, reset_button)
    def on_textbox_change(textbox, original_ext, save_button, remove_button, reset_button):
        new_ext = textbox.get("1.0", "end-1c").strip()
        is_changed = new_ext != original_ext[0]
        handle_change(is_changed, save_button, remove_button, reset_button)

    def save_entry_changes(folder_entry_var, original_folder, textbox, config, save_button, remove_button, reset_button, original_ext):
        new_folder_name = folder_entry_var.get().strip()
        
        new_extensions = textbox.get("1.0", "end-1c").strip()
        new_extensions = [ext.strip().replace(' ', '').lower() for ext in new_extensions.split(',') if ext.strip()]
        
        # Validate folder name and extensions
        is_valid, error_message = validate_input(new_folder_name, new_extensions, original_folder)
        if is_valid is None:
            # User has already been informed, return without showing the error dialog
            return
        if not is_valid:
            show_error_dialog(error_message)
            return
        
        # Update the config with the new folder name and extensions
        del config['folder_extensions_mapping'][original_folder[0]]
        config['folder_extensions_mapping'][new_folder_name] = new_extensions
        
        # Save the updated config
        save_config(config['folder_path'], config['folder_extensions_mapping'])
        
        # Update the original values
        original_folder[0] = new_folder_name
        original_ext[0] = ', '.join(new_extensions)
        
        # Update extensions textbox after save (since save will remove invalid spaces)
        textbox.delete("1.0", "end")
        textbox.insert("1.0", ', '.join(new_extensions))
    
        # Hide the save and reset buttons, show the remove button
        save_button.pack_forget()
        reset_button.pack_forget()
        remove_button.place(relx=0.5, rely=0.5, anchor="center")

    global render_scrollable_widget # to use it when sorting for refresh incase any folder name changed 
    def render_scrollable_widget():
        # Clear the scrollable frame
        for widget in scrollable_frame.winfo_children():
            widget.destroy()
        
        # Add "Folders" and "Extensions" labels before the loop
        header_frame = ctk.CTkFrame(scrollable_frame)
        header_frame.pack(fill="x", padx=5, pady=10)
        
        # Create a frame for the "Folders" label
        folders_frame = ctk.CTkFrame(header_frame, corner_radius=8, fg_color="#242424")
        folders_frame.pack(side="left", padx=(68, 0))
        
        folders_label = ctk.CTkLabel(folders_frame, text="Folders", font=ctk_font_semibold_12)
        folders_label.pack(padx=7)
        
        # Create a frame for the "Extensions" label
        extensions_frame = ctk.CTkFrame(header_frame, corner_radius=8, fg_color="#242424")
        extensions_frame.pack(side="left", padx=(140, 0))  # Adjust the padding as needed
        
        extensions_label = ctk.CTkLabel(extensions_frame, text="Extensions", font=ctk_font_semibold_12)
        extensions_label.pack(padx=7)
    
        # Sort the folder_extensions_mapping dictionary by keys (folder names)
        sorted_folder_extensions = sorted(config['folder_extensions_mapping'].items())
        # Populate the scrollable frame with labels and textboxes
        for folder, extensions in sorted_folder_extensions:
            # Frame for both folder name and extensions
            frame = ctk.CTkFrame(scrollable_frame, width=450)  # Adjust width as needed
            frame.pack(fill="x", padx=2, pady=0)
            
            # Frame for folder name
            label_frame = ctk.CTkFrame(frame, corner_radius=10, width=200, height=40) 
            label_frame.pack_propagate(False)  # Prevent the frame from resizing based on its children
            label_frame.pack(side="left", padx=(5,2), pady=5)
            
            # StringVar for folder entry
            folder_entry_var = ctk.StringVar(value=folder)
            
            # Entry widget for the folder name
            folder_entry = ctk.CTkEntry(label_frame, font=("Cascadia Code", 12), textvariable=folder_entry_var)
            folder_entry.pack(expand=True, fill="both", padx=5, pady=5)
            
            # Textbox for extensions
            textbox = ctk.CTkTextbox(frame, width=200, height=60, font=("Cascadia Code", 12))
            textbox.pack(side="left", padx=(12,0), pady=5)
            textbox.insert("1.0", ', '.join(extensions))
            
            # Store the original values
            original_folder = [folder]
            original_ext = [', '.join(extensions)]
            
            # Create a frame for the buttons
            button_frame = ctk.CTkFrame(frame, width=90, height=40, fg_color="#2b2b2b")
            button_frame.pack_propagate(False)  # Prevent the frame from resizing based on its children
            button_frame.pack(side="left", padx=(7,0), pady=5)
            
            # Create a remove button with an image
            remove_button = ctk.CTkButton(button_frame, width=25, height=25, fg_color="#343638", hover_color='#65000B', image=delete_icon, text="", command=lambda f=frame, fe=folder_entry: delete_category(f, fe))
            remove_button.place(relx=0.5, rely=0.5, anchor="center")  # Center the remove button
            
            # Create a save button (initially hidden)
            save_button = ctk.CTkButton(button_frame, text="Save", width=30, height=25, fg_color="#343638", hover_color='#253417', text_color='#94be6b', font=("Cascadia Code", 9))
            
            # Define the reset function inside the loop to capture the correct variables
            def reset_fields(folder_entry_var=folder_entry_var, textbox=textbox, original_folder=original_folder, original_ext=original_ext):
                folder_entry_var.set(original_folder[0])
                textbox.delete("1.0", "end")  # Clear the textbox content first
                textbox.insert("1.0", original_ext[0])  # Insert the original extensions after clearing
                # Manually call the change handlers to update the buttons
                on_textbox_change(textbox, original_ext, save_button, remove_button, reset_button)
            
            # Create a reset button
            reset_button = ctk.CTkButton(button_frame, text="Reset", width=30, height=25, fg_color="#343638", hover_color='#461505', text_color='#f06a3f', font=("Cascadia Code", 9), command=reset_fields)
            # Initially hide the reset button
            reset_button.pack_forget()
            
            # Configure the save button command after defining reset_button
            save_button.configure(command=lambda fe_var=folder_entry_var, of=original_folder, tb=textbox, sb=save_button, rb=remove_button, rsb=reset_button, oe=original_ext: save_entry_changes(fe_var, of, tb, config, sb, rb, rsb, oe))
            
            # Trace changes to the folder entry
            folder_entry_var.trace_add("write", lambda *args, fe_var=folder_entry_var, of=original_folder, sb=save_button, rb=remove_button, rsb=reset_button: on_entry_change(fe_var, of, sb, rb, rsb))
            
            # Trace changes to the extensions textbox
            def on_text_change(event, tb=textbox, ot=original_ext, sb=save_button, rb=remove_button, rsb=reset_button):
                on_textbox_change(tb, ot, sb, rb, rsb)
            
            textbox.bind("<KeyRelease>", on_text_change)

    # scrollable frame for folders, extensions
    scrollable_frame = ctk.CTkScrollableFrame(app)
    scrollable_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))

    scrollbar = scrollable_frame._scrollbar 
    scrollbar.configure(width=6)  
    
    #initial render
    render_scrollable_widget()
    #endregion

    app.lift()
    focus_app()

    # Start the Tkinter event loop
    app.mainloop()
#endregion


#region File Sorting Function
def show_popup(message):
    global popup
    def setup_popup(popup, message):
        def on_popup_quit():
            global popup
            popup.destroy()
            popup = None

        # Create customtkinter font objects using loaded fonts
        try:
            ctk_font_semibold_12 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=12)
            ctk_font_semibold_13 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=13)
        except Exception as e:
            print(f"Error creating CTkFont objects: {e}")
            sys.exit(1)

        popup.title("Path Not Set")
        popup.geometry("350x130")
        popup.resizable(False, False) 
        popup.iconbitmap(APP_ICON)
        popup.protocol("WM_DELETE_WINDOW", on_popup_quit)

        label = ctk.CTkLabel(popup, text=message, font=ctk_font_semibold_13)
        label.pack(pady=(20,15))
        
        set_button = ctk.CTkButton(popup, text="Set", width=50, font=ctk_font_semibold_12, command=lambda: select_folder())
        set_button.pack(pady=10, anchor="center")
    
    if app:
        popup = ToplevelIco(app, APP_ICON)
        setup_popup(popup, message)
        popup.transient(app)  
        popup.grab_set()   
        popup.lift()
        popup.focus_force()
        app.wait_window(popup)
    else:
        popup = ctk.CTk()
        setup_popup(popup, message)
        popup.lift()
        popup.focus_force()
        popup.mainloop()

        
def prompt_user_for_existing_folder(folder_name):
    global dialog

    def setup_dialog(dialog, folder_name):
        user_response = None

        def on_confirm():
            global dialog
            nonlocal user_response
            user_response = True
            dialog.destroy()
            dialog = None
    
        def on_cancel():
            global dialog
            nonlocal user_response
            user_response = False
            dialog.destroy()
            dialog = None
        
        def on_dialog_quit():
            global dialog
            nonlocal user_response
            user_response = False
            dialog.destroy()
            dialog = None
    
        dialog.title("Folder Already Exists")
    
        # Adjust the dialog's width dynamically based on the text length
        dialog.geometry("400x150")
        dialog.minsize(400, 150)
        dialog.resizable(False, False)  # Disable resizing
        dialog.iconbitmap(APP_ICON)

        # Create customtkinter font objects using loaded fonts
        try:
            ctk_font_semibold_12 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=12)
            ctk_font_semibold_14 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=14)
        except Exception as e:
            print(f"Error creating CTkFont objects: {e}")
            sys.exit(1)

        # Create a label with wrapping text
        label = ctk.CTkLabel(dialog, 
                            text=f"The folder '{folder_name}' already exists. Do you want to use the existing folder?", 
                            font=ctk_font_semibold_14,
                            wraplength=380)  # Adjust the wraplength based on the dialog width
        label.pack(pady=(20, 10), padx=10)
    
        # Create a frame for the buttons
        button_frame = ctk.CTkFrame(dialog, fg_color="#242424")
        button_frame.pack(pady=10, fill='x')
    
        # Create Yes and No buttons
        yes_button = ctk.CTkButton(button_frame, 
                                text="Yes", 
                                width=80, 
                                font=ctk_font_semibold_12, 
                                command=on_confirm)
        yes_button.pack(side="left", padx=(100, 0), pady=10)
    
        no_button = ctk.CTkButton(button_frame, 
                                text="No", 
                                width=80, 
                                fg_color="#343638",
                                hover_color="#2d2a2e",
                                font=ctk_font_semibold_12, 
                                command=on_cancel)
        no_button.pack(side="right", padx=(0, 100), pady=10)
    
        # Allow the dialog to resize dynamically
        dialog.update_idletasks()
        
        # Calculate the exact height required, with minimal extra space
        dialog.geometry(f"{max(400, label.winfo_reqwidth() + 20)}x{label.winfo_reqheight() + button_frame.winfo_reqheight() + 60}")
    
        # Bind the close event to the on_dialog_quit function
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_quit)
    
        return dialog, user_response

    if app:
        dialog = ToplevelIco(app, APP_ICON)
        dialog, user_response = setup_dialog(dialog, folder_name)
        dialog.transient(app)
        dialog.grab_set()
        dialog.lift()
        dialog.focus_force()
        app.wait_window(dialog)
    else:
        dialog = ctk.CTk()
        dialog, user_response = setup_dialog(dialog, folder_name)
        dialog.lift()
        dialog.focus_force()
        dialog.mainloop()

    return user_response

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
    
    if app:
        focus_app()

    toast(
        'Folder Sorted',
        f'Sorted: "{folder_path}"',
        buttons=buttons,
        audio={'silent': 'true'},
        duration='short'
    )

def sort_files():
    global config
    config = load_config()
    folder_path = config.get('folder_path', '')

    # Check if the folder_path is valid
    if not folder_path or not path.exists(folder_path):
        # print(f"Sorting files in the folder: {folder_path}")

        show_popup("Folder path is not set or does not exist")
        return

    # Check for existing folders only if the path is not in duplicates_checked_paths
    # (meaning check only if current path hasn't been sorted by user before)
    if folder_path not in config['duplicates_checked_paths']:
        need_scrollable_refresh = ensure_unique_folder_names(config)
        save_config(duplicates_checked_path=folder_path)

    folder_extensions_mapping = config.get('folder_extensions_mapping', {}) # load after checking duplicates incase any change

    for file in listdir(folder_path):
        file_path = path.join(folder_path, file)
        if not path.isfile(file_path):
            continue
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
                    show_error_dialog(f"Error moving file '{file}': {str(e)}")
                break
    if app:
        try:
            if need_scrollable_refresh:
                # print('refreshing scrollable widget after')
                render_scrollable_widget()  # Schedule the refresh function to run on the main thread
        except:
            pass
    
    # folder_name = path.basename(folder_path)
    # print(f"Sorted all items in the '{folder_name}' folder.")
    # print('wont check these paths again:', config['duplicates_checked_paths'])
    
    # Show Windows notification
    notification_thread = Thread(target=show_notification, args=(folder_path,))
    notification_thread.start()
#endregion



#region Tray Icon Functions
def run_sort_files():
    sort_files()

def quit_app(tray_app):
    if app:
        app.destroy()
    # else:
        # print("app is None or already destroyed")
    
    if popup:
        popup.destroy()
    # else:
        # print("popup is None or already destroyed")
    
    if dialog:
        dialog.destroy()
    # else:
        # print("dialog is None or already destroyed")

    # Stop the tray_app
    tray_app.stop()

def open_config_gui():
    if app:        
        # print("Config GUI already open")
        return
    if popup:
        # print("set path popup open as Ctk, cant open another Ctk gui window")
        return
    if dialog:
        # print("dialog open as Ctk, cant open another Ctk gui window")
        return
    # print("Opening config GUI")
    config_gui()

def setup_tray():
    icon_image = Image.open(APP_ICON) 

    menu = Menu(
        MenuItem('Sort Folder', run_sort_files),
        MenuItem('Configure', open_config_gui),
        MenuItem('Quit', lambda: quit_app(tray_app))
    )

    tray_app = Icon("FolderSorter", icon_image, menu=menu)
    tray_app.title = "Folder Sorter"
    tray_app.run()
#endregion

#region Main Execution
if __name__ == "__main__":
    tray_thread = Thread(target=setup_tray)
    tray_thread.start()
#endregion


