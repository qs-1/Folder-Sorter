import sys
from re import compile
import customtkinter as ctk
from PIL import Image
from os import path
from threading import Thread
from CTkToolTip import CTkToolTip

from config_manager import (
    config, load_config, save_config, 
    APP_ICON, DELETE_PNG, REGULAR_FONT, SEMIBOLD_FONT
)
import file_sorter

# Global variables to hold references to main GUI elements and threads.
# To allow different functions to access, modify, or check the state of these elements/threads. 
app = None                     # Main configuration window (CTk)
path_popup_window = None       # Transient popup window (ToplevelIco, child of app)
standalone_popup_window = None # Standalone popup window (CTk, own thread)
standalone_popup_thread = None # Thread for the standalone popup
path_entry = None              # CTkEntry widget for updating selected folder path.
tooltip = None                 # CTkToolTip instance for the path entry update

class ToplevelIco(ctk.CTkToplevel):
    """Custom CTkToplevel that fixes icon bug"""
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

def refresh_path_entry(new_path):
    """Update the path entry with a new path"""
    if not new_path:
        new_path = ""
    try:
        global path_entry, tooltip
        path_entry.configure(state='normal')
        path_entry.delete(0, ctk.END)
        path_entry.insert(0, new_path)
        path_entry.configure(state='disabled') 
        tooltip.configure(message=new_path if new_path else "No Path Set")
    except Exception:
        pass  # edge case when closing the app and trying to refresh the path entry

def select_folder():
    """Open folder selection dialog and update path"""
    folder_path = ctk.filedialog.askdirectory()
    if folder_path:
        save_config(folder_path=folder_path)
        
        global path_popup_window 
        if path_popup_window:
            refresh_path_entry(folder_path)
            path_popup_window.destroy() 
            path_popup_window = None    
        elif path_entry:
            refresh_path_entry(folder_path)

def show_error_dialog(message):
    """Show an error dialog with the specified message"""
    global app
    if not app:
        return
        
    dialog = ToplevelIco(app, APP_ICON)
    dialog.title("Error")
    
    # Create font objects
    try:
        ctk_font_semibold_12 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=12)
        ctk_font_semibold_14 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=14)
    except Exception as e:
        print(f"Error creating CTkFont objects: {e}")
        sys.exit(1)
    
    # Adjust the dialog's width dynamically based on the text length
    dialog.geometry("400x150")
    dialog.minsize(400, 150)
    dialog.resizable(False, False)
    dialog.iconbitmap(APP_ICON)
    
    # Create a label with wrapping text
    label = ctk.CTkLabel(dialog, 
                        text=message, 
                        font=ctk_font_semibold_14,
                        wraplength=380)
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
    """Show a dialog when a folder already exists"""
    global app
    if not app:
        return False
        
    dialog = ToplevelIco(app, APP_ICON)
    dialog.title("Folder Already Exists")
    
    # Create font objects
    try:
        ctk_font_semibold_12 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=12)
        ctk_font_semibold_14 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=14)
    except Exception as e:
        print(f"Error creating CTkFont objects: {e}")
        sys.exit(1)
    
    # Adjust the dialog's width dynamically based on the text length
    dialog.geometry("400x150")
    dialog.minsize(400, 150)
    dialog.resizable(False, False)
    dialog.iconbitmap(APP_ICON)
    
    # Create a label with wrapping text
    label = ctk.CTkLabel(dialog, 
                        text=f"Folder '{folder_name}' already exists in the path '{folder_path}'.", 
                        font=ctk_font_semibold_14,
                        wraplength=380)
    label.pack(pady=(20, 10), padx=10)

    # Create a frame for the buttons
    button_frame = ctk.CTkFrame(dialog, fg_color="#242424")
    button_frame.pack(pady=10, fill='x')

    # Default result is False (rename)
    dialog.result = False

    def use_same_folder():
        dialog.result = True
        dialog.destroy()

    def rename():
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

def prompt_user_for_existing_folder(folder_name):
    """Prompt the user when a folder already exists"""
    global app, dialog

    def setup_dialog(dialog, folder_name):
        user_response = None

        def on_confirm():
            nonlocal user_response
            user_response = True
            dialog.destroy()

        def on_cancel():
            nonlocal user_response
            user_response = False
            dialog.destroy()
        
        def on_dialog_quit():
            nonlocal user_response
            user_response = False
            dialog.destroy()
    
        dialog.title("Folder Already Exists")
    
        # Create font objects
        try:
            ctk_font_semibold_12 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=12)
            ctk_font_semibold_14 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=14)
        except Exception as e:
            print(f"Error creating CTkFont objects: {e}")
            sys.exit(1)
    
        # Adjust the dialog's width dynamically based on the text length
        dialog.geometry("400x150")
        dialog.minsize(400, 150)
        dialog.resizable(False, False)
        dialog.iconbitmap(APP_ICON)

        # Create a label with wrapping text
        label = ctk.CTkLabel(dialog, 
                            text=f"The folder '{folder_name}' already exists. Do you want to use the existing folder?", 
                            font=ctk_font_semibold_14,
                            wraplength=380)
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

def _destroy_standalone_popup():
    """Safely destroys the standalone popup window if it exists."""
    global standalone_popup_window
    if standalone_popup_window and standalone_popup_window.winfo_exists():
        try:
            # Schedule destroy on the popup's own mainloop
            standalone_popup_window.after(0, standalone_popup_window.destroy)
        except Exception as e:
            print(f"Error scheduling standalone popup destroy: {e}")
    standalone_popup_window = None # reset global reference

def path_prompt_popup(message):
    """Show a popup message with a 'Set' button
    
    If the main configuration window 'app' exists, displays a Toplevel
    window transient to 'app'. Otherwise, creates a new standalone CTk 
    window running in its own thread.
    """

    # Import global variables to manage app and popup state
    global app, path_popup_window, standalone_popup_window, standalone_popup_thread

    def setup_popup(popup_instance, message):
        def on_popup_quit():
            # 'app' isnt running (standalone popup in its thread)
            if popup_instance == standalone_popup_window:
                _destroy_standalone_popup() # destroy the standalone popup from its own thread
            else: 
                # 'app' is running, destroy transient popup linked to it
                global path_popup_window 
                if popup_instance and popup_instance.winfo_exists():
                    popup_instance.destroy()
                path_popup_window = None 

        popup_instance.title("Path Not Set")
        popup_instance.geometry("350x130")
        popup_instance.resizable(False, False)
        popup_instance.iconbitmap(APP_ICON)
        popup_instance.protocol("WM_DELETE_WINDOW", on_popup_quit)

        label = ctk.CTkLabel(popup_instance, text=message, font=("Cascadia Code SemiBold", 13)) 
        label.pack(pady=(20,15))
        set_button = ctk.CTkButton(popup_instance, text="Set", width=50, font=("Cascadia Code SemiBold", 12), command=select_folder) 
        set_button.pack(pady=10, anchor="center")

    # If the main 'app' config GUI is running
    if app and app.winfo_exists(): 
        if path_popup_window and path_popup_window.winfo_exists(): # Prevent multiple popups  
             path_popup_window.focus_force() 
             return
        path_popup_window = ToplevelIco(app, APP_ICON) 
        setup_popup(path_popup_window, message) 
        path_popup_window.transient(app) 
        path_popup_window.grab_set() 
        path_popup_window.lift() 
        path_popup_window.focus_force() 

    # If 'app' config GUI is not running (make standalone popup)
    else: 
        if standalone_popup_window and standalone_popup_window.winfo_exists(): # Prevent multiple popups
            standalone_popup_window.focus_force()
            return
        if standalone_popup_thread and standalone_popup_thread.is_alive(): 
            print("Standalone popup thread already running.")
            return

        def _standalone_popup_target():
            global standalone_popup_window
            try:
                standalone_popup_window = ctk.CTk() 
                setup_popup(standalone_popup_window, message)
                standalone_popup_window.lift()
                standalone_popup_window.focus_force()
                standalone_popup_window.mainloop() # Mainloop in its own thread
            finally:
                # Ensure reset if mainloop exits unexpectedly
                standalone_popup_window = None
                print("Standalone popup closed.")

        print("Starting standalone popup thread.")
        standalone_popup_thread = Thread(target=_standalone_popup_target, daemon=True)
        standalone_popup_thread.start()

def validate_input(folder_name, extensions, original_folder=None):
    """Validate folder name and extensions"""
    if not folder_name.strip():
        return False, "Folder name cannot be empty."
    
    # Check if folder name already exists in the path
    folder_path = config.get('folder_path', '')
    if folder_path and folder_name.strip('/') and path.exists(path.join(folder_path, folder_name)):
        use_same_folder = show_folder_exists_dialog(folder_path, folder_name)
        if use_same_folder:
            pass
        else:
            # Return None to indicate that the user has already been informed
            return None, ""

    # Validate folder name and extensions for invalid characters
    from config_manager import reserved_names
    
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
        # Editing an existing folder, skip the original folder
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

def focus_app():
    """Focus the main application window"""
    global app
    if app:
        app.focus_force()

def config_gui():
    """Main configuration GUI"""
    # Load the configuration
    config_data = load_config()

    # Initialize the main application window
    global app, path_entry, tooltip
    app = ctk.CTk()
    app.title("Configure Folder Sorter")
    app.geometry("547x700")
    app.iconbitmap(APP_ICON)
    app.resizable(False, True)

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
    path_entry = ctk.CTkEntry(path_frame, font=ctk_font_regular_11)
    path_entry.pack(side="left", fill="x", expand=True, padx=5, pady=7)
    path_entry.configure(state='disabled')

    tooltip = CTkToolTip(path_entry, message=config_data['folder_path'] if config_data['folder_path'] else "No Path Set", 
                         x_offset=-5, y_offset=20, alpha=0.87, font=('Cascadia Code', 12))
    refresh_path_entry(config_data['folder_path'])

    # Create a button to open the folder selection dialog
    browse_button = ctk.CTkButton(path_frame, text="Browse", width=12, font=ctk_font_regular_12, command=select_folder)
    browse_button.pack(side="right", padx=(7,8), pady=7)
    #endregion

    def show_confirmation_dialog(folder_name, on_confirm):
        """Show confirmation dialog for category deletion"""
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
                            wraplength=380)
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
            save_config(dont_show_again=dont_show_again_var.get() == "1")
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
        """Delete a category from the config"""
        folder_name = folder_entry.get().strip()
        
        def on_confirm():
            frame.destroy()
            config['folder_extensions_mapping'].pop(folder_name, None)
            save_config(folder_extensions_mapping=config['folder_extensions_mapping'])
        
        if config.get('dont_show_again', False):
            on_confirm()
        else:
            show_confirmation_dialog(folder_name, on_confirm)

    #region add new category
    # Function to add a new folder and its extensions
    def add_category():
        """Add a new category to the config"""
        folder_name = new_category_entry.get().strip()
        extensions_input = new_extensions_entry.get().strip()
        extensions = [ext.strip().replace(' ', '').lower() for ext in extensions_input.split(',') if ext.strip()]
        
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
        save_config(folder_extensions_mapping=config['folder_extensions_mapping'])
        
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

    #region scrollable widget
    def handle_change(is_changed, save_button, remove_button, reset_button):
        """Handle UI changes when field values change"""
        if is_changed:
            save_button.pack(side="left", padx=2, pady=5)
            remove_button.place_forget()  # Hide the remove button
            reset_button.pack(side="right", padx=2, pady=5)  # Show the reset button
        else:
            save_button.pack_forget()
            reset_button.pack_forget()  # Hide the reset button
            remove_button.place(relx=0.5, rely=0.5, anchor="center")  # Center the remove button
            
    def on_entry_change(folder_entry_var, original_folder_name, save_button, remove_button, reset_button):
        """Handle folder name entry changes"""
        new_folder_name = folder_entry_var.get().strip()
        is_changed = new_folder_name != original_folder_name[0]
        handle_change(is_changed, save_button, remove_button, reset_button)
        
    def on_textbox_change(textbox, original_ext, save_button, remove_button, reset_button):
        """Handle extensions textbox changes"""
        new_ext = textbox.get("1.0", "end-1c").strip()
        is_changed = new_ext != original_ext[0]
        handle_change(is_changed, save_button, remove_button, reset_button)

    def save_entry_changes(folder_entry_var, original_folder, textbox, save_button, remove_button, reset_button, original_ext):
        """Save changes to folder name and extensions"""
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
        save_config(folder_extensions_mapping=config['folder_extensions_mapping'])
        
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


    # helper function to scroll only the specific textbox
    # and prevent event propagation
    def _scroll_textbox(event, textbox):
        """Scrolls the textbox if scrollable, otherwise allows event propagation."""
        first, last = textbox.yview()

        # Check if the textbox is actually scrollable (content exceeds view)
        is_scrollable = first != 0.0 or last != 1.0

        if is_scrollable:
            # Determine scroll direction (platform-dependent)
            if event.num == 5 or event.delta < 0:
                textbox.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:
                textbox.yview_scroll(-1, "units")
            return "break"  # Stop event propagation ONLY if textbox was scrolled
        else:
            # If not scrollable, do nothing and let the event propagate
            # to the parent scrollable frame by not returning "break".
            pass 

    def _on_textbox_enter(event, textbox):
        """Bind mouse wheel to textbox scroll handler when mouse enters."""
        # Always bind, the handler itself will decide whether to block propagation
        textbox.bind("<MouseWheel>", lambda e: _scroll_textbox(e, textbox), add="+")
        textbox.bind("<Button-4>", lambda e: _scroll_textbox(e, textbox), add="+") # Scroll up
        textbox.bind("<Button-5>", lambda e: _scroll_textbox(e, textbox), add="+") # Scroll down

    def _on_textbox_leave(event, textbox):
        """Unbind mouse wheel from textbox scroll handler when mouse leaves."""
        # Always unbind on leave
        textbox.unbind("<MouseWheel>")
        textbox.unbind("<Button-4>")
        textbox.unbind("<Button-5>")
    


    def render_scrollable_widget():
        """Render the scrollable widget with folders and extensions"""
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
        sorted_folder_extensions = sorted(config['folder_extensions_mapping'].items(), key=lambda item: item[0].lower())
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

            # Add event bindings for nested scrolling
            textbox.bind("<Enter>", lambda e, tb=textbox: _on_textbox_enter(e, tb), add="+")
            textbox.bind("<Leave>", lambda e, tb=textbox: _on_textbox_leave(e, tb), add="+")

            # Store the original values
            original_folder = [folder]
            original_ext = [', '.join(extensions)]
            
            # Create a frame for the buttons
            button_frame = ctk.CTkFrame(frame, width=90, height=40, fg_color="#2b2b2b")
            button_frame.pack_propagate(False)  # Prevent the frame from resizing based on its children
            button_frame.pack(side="left", padx=(7,0), pady=5)
            
            # Create a remove button with an image
            remove_button = ctk.CTkButton(button_frame, width=25, height=25, fg_color="#343638", hover_color='#65000B', 
                                        image=delete_icon, text="", command=lambda f=frame, fe=folder_entry: delete_category(f, fe))
            remove_button.place(relx=0.5, rely=0.5, anchor="center")  # Center the remove button
            
            # Create a save button (initially hidden)
            save_button = ctk.CTkButton(button_frame, text="Save", width=30, height=25, fg_color="#343638", 
                                        hover_color='#253417', text_color='#94be6b', font=("Cascadia Code", 9))
            
            # Define the reset function inside the loop to capture the correct variables
            def reset_fields(folder_entry_var=folder_entry_var, textbox=textbox, original_folder=original_folder, original_ext=original_ext):
                folder_entry_var.set(original_folder[0])
                textbox.delete("1.0", "end")  # Clear the textbox content first
                textbox.insert("1.0", original_ext[0])  # Insert the original extensions after clearing
                # Manually call the change handlers to update the buttons
                on_textbox_change(textbox, original_ext, save_button, remove_button, reset_button)
            
            # Create a reset button
            reset_button = ctk.CTkButton(button_frame, text="Reset", width=30, height=25, fg_color="#343638", 
                                        hover_color='#461505', text_color='#f06a3f', font=("Cascadia Code", 9), command=reset_fields)
            # Initially hide the reset button
            reset_button.pack_forget()
            
            # Configure the save button command after defining reset_button
            save_button.configure(command=lambda fe_var=folder_entry_var, of=original_folder, tb=textbox, 
                                        sb=save_button, rb=remove_button, rsb=reset_button, oe=original_ext: 
                                        save_entry_changes(fe_var, of, tb, sb, rb, rsb, oe))
            
            # Trace changes to the folder entry
            folder_entry_var.trace_add("write", lambda *args, fe_var=folder_entry_var, of=original_folder, 
                                    sb=save_button, rb=remove_button, rsb=reset_button: 
                                    on_entry_change(fe_var, of, sb, rb, rsb))
            
            # Trace changes to the extensions textbox
            def on_text_change(event, tb=textbox, ot=original_ext, sb=save_button, rb=remove_button, rsb=reset_button):
                on_textbox_change(tb, ot, sb, rb, rsb)
            
            textbox.bind("<KeyRelease>", on_text_change)

    # scrollable frame for folders, extensions
    scrollable_frame = ctk.CTkScrollableFrame(app)
    scrollable_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))

    scrollbar = scrollable_frame._scrollbar 
    scrollbar.configure(width=6)  
    
    # Set GUI callbacks for file_sorter
    file_sorter.set_gui_callbacks(show_error_dialog, prompt_user_for_existing_folder, render_scrollable_widget, focus_app)
    
    # Initial render
    render_scrollable_widget()
    #endregion

    app.lift()
    focus_app()

    # Start the Tkinter event loop
    app.mainloop()