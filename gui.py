import sys
import ctypes
import platform 

# initial blurryness fix for Windows
if platform.system() == "Windows": 
    try:                         
        import ctypes            
        ctypes.windll.shcore.SetProcessDpiAwareness(1) 
    except Exception as e:       
        print(f"Note: Failed to set DPI awareness - {e}") 

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
app = None                     # Main configuration window (CTk)
path_popup_window = None       # Transient popup window (ToplevelIco, child)
standalone_popup_window = None # Standalone popup window (CTk, own thread)
standalone_popup_thread = None # Thread for the standalone popup


# region custom CTkToplevel
class ToplevelIco(ctk.CTkToplevel):
    """Custom CTkToplevel that fixes icon updation bug"""
    def __init__(self, master=None, icon_path=None):
        super().__init__(master)
        # Store initial master dimensions if available (assuming master is ConfigWindow)
        if hasattr(master, 'initial_width') and hasattr(master, 'initial_height'):
            self.master_initial_width = master.initial_width
            self.master_initial_height = master.initial_height
        else:
            self.master_initial_width = None
            self.master_initial_height = None

        if icon_path:
            self.after(201, lambda: self.iconbitmap(icon_path))

    def center_window(self):
        self.update_idletasks() # Ensure dialog measurements are up-to-date

        # Get Dialog's size
        dialog_width = self.winfo_reqwidth()
        dialog_height = self.winfo_reqheight()


        if not self.master or not self.master.winfo_exists():
            print("Error: Cannot center dialog, master window invalid.")
            # Fallback: center on screen? Or just place at default?
            # Centering on screen for now as a basic fallback
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = (screen_width // 2) - (dialog_width // 2) 
            y = (screen_height // 2) - (dialog_height // 2)
            self.geometry(f'{dialog_width}x{dialog_height}+{x}+{y}')
            return

        try:
            # --- Get Scaling Factor ---
            scale_factor = 1.0
            try:
                # Try getting scaling factor from the master window first
                self.master.update_idletasks() # Ensure master handle is ready
                scale_factor = ctk.ScalingTracker.get_window_dpi_scaling(self.master.winfo_id())
            except Exception as e_ctk:
                if platform.system() == "Windows":
                    try:
                        scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0
                    except Exception as e_ctypes:
                        scale_factor = 1.0
                else:
                     scale_factor = 1.0

            # --- Master Geometry ---
            master_x = self.master.winfo_x()
            master_y = self.master.winfo_y()

            # Use stored initial logical size if available, otherwise fallback
            if self.master_initial_width is not None and self.master_initial_height is not None:
                master_logical_width = self.master_initial_width
                master_logical_height = self.master_initial_height
            else:
                # Fallback, Get current size
                master_logical_width = self.master.winfo_width()
                master_logical_height = self.master.winfo_height()

            # Calculate sizes and center
            master_actual_width = int(master_logical_width * scale_factor)
            master_actual_height = int(master_logical_height * scale_factor)
            dialog_actual_width = int(dialog_width * scale_factor)
            dialog_actual_height = int(dialog_height * scale_factor)

            # Calculate master's center
            physical_master_center_x = master_x + (master_actual_width // 2)
            physical_master_center_y = master_y + (master_actual_height // 2)

            # Calculate dialog's top-left
            x = physical_master_center_x - (dialog_actual_width // 2)
            y = physical_master_center_y - (dialog_actual_height // 2)

            # Set geometry using  dialog size and position
            geometry_string = f'{dialog_width}x{dialog_height}+{x}+{y}'
            self.geometry(geometry_string)

        except Exception as e: # Fallback if any error occurs during calculation
            print(f"Error during dialog centering: {e}")
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x_fb = (screen_width // 2) - (dialog_width // 2)
            y_fb = (screen_height // 2) - (dialog_height // 2)
            try:
                self.geometry(f'{dialog_width}x{dialog_height}+{x_fb}+{y_fb}')
            except Exception as e_fb:
                 print(f"Error setting fallback geometry: {e_fb}")
# endregion

# region error popups
def show_error_dialog(parent_window, message):
    """Show an error dialog with the specified message"""

    if not parent_window or not parent_window.winfo_exists():
        print(f"Error: show_error_dialog called with invalid parent window. Message: {message}")
        return

    dialog = ToplevelIco(parent_window, APP_ICON)
    dialog.title("Error")

    try:
        ctk_font_semibold_12 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=12)
        ctk_font_semibold_14 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=14)
    except Exception as e:
        print(f"Error creating CTkFont objects: {e}")
        ctk_font_semibold_12 = None
        ctk_font_semibold_14 = None

    dialog.geometry("400x150")
    dialog.minsize(400, 150)
    dialog.resizable(False, False)
    dialog.iconbitmap(APP_ICON)

    label = ctk.CTkLabel(dialog,
                        text=message,
                        font=ctk_font_semibold_14,
                        wraplength=380)
    label.pack(pady=(20, 10), padx=10)

    button_frame = ctk.CTkFrame(dialog, fg_color="#242424")
    button_frame.pack(pady=10, fill='x')

    def on_ok():
        dialog.destroy()

    ok_button = ctk.CTkButton(button_frame,
                            text="OK",
                            width=80,
                            font=ctk_font_semibold_12,
                            command=on_ok)
    ok_button.pack(pady=10)

    dialog.update_idletasks()

    try:
        req_width = label.winfo_reqwidth()
        req_height = label.winfo_reqheight()
        btn_height = button_frame.winfo_reqheight()
        dialog.geometry(f"{max(400, req_width + 20)}x{req_height + btn_height + 60}")
    except Exception:
        pass

    dialog.center_window() 
    dialog.transient(parent_window)
    dialog.grab_set()
    dialog.focus_force()
    parent_window.wait_window(dialog)


def show_folder_exists_dialog(parent_window, folder_path, folder_name):
    """Show a dialog when a folder already exists"""

    if not parent_window or not parent_window.winfo_exists():
        print(f"Error: show_folder_exists_dialog called with invalid parent window for folder: {folder_name}")
        return False

    dialog = ToplevelIco(parent_window, APP_ICON)
    dialog.title("Folder Already Exists")

    try:
        ctk_font_semibold_12 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=12)
        ctk_font_semibold_14 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=14)
    except Exception as e:
        print(f"Error creating CTkFont objects: {e}")
        ctk_font_semibold_12 = None
        ctk_font_semibold_14 = None

    dialog.geometry("400x150")
    dialog.minsize(400, 150)
    dialog.resizable(False, False)
    dialog.iconbitmap(APP_ICON)

    label = ctk.CTkLabel(dialog,
                        text=f"Folder '{folder_name}' already exists in the list.",
                        font=ctk_font_semibold_14,
                        wraplength=380)
    label.pack(pady=(20, 10), padx=10)

    button_frame = ctk.CTkFrame(dialog, fg_color="#242424")
    button_frame.pack(pady=10, fill='x')

    dialog.result = False

    def use_same_folder():
        dialog.result = True
        dialog.destroy()

    def rename():
        dialog.result = False
        dialog.destroy()

    use_button = ctk.CTkButton(button_frame,
                            text="Use Same Folder",
                            width=120,
                            font=ctk_font_semibold_12,
                            command=use_same_folder)
    use_button.pack(side="left", padx=(80,0), pady=10)

    rename_button = ctk.CTkButton(button_frame,
                                text="Cancel",
                                width=80,
                                fg_color="#343638",
                                hover_color="#2d2a2e",
                                font=ctk_font_semibold_12,
                                command=rename)
    rename_button.pack(side="right", padx=(0,100), pady=10)

    dialog.update_idletasks()

    try:
        req_width = label.winfo_reqwidth()
        req_height = label.winfo_reqheight()
        btn_height = button_frame.winfo_reqheight()
        dialog.geometry(f"{max(400, req_width + 20)}x{req_height + btn_height + 60}")
    except Exception:
        pass

    dialog.protocol("WM_DELETE_WINDOW", rename)

    dialog.center_window()
    dialog.transient(parent_window)
    dialog.grab_set()
    dialog.focus_force()
    parent_window.wait_window(dialog)

    return dialog.result
# endregion


# region del row confirmation
def show_confirmation_dialog(parent_window, folder_name, on_confirm_callback):
    """Shows a confirmation dialog for deleting a category."""
    if not parent_window or not parent_window.winfo_exists():
        print(f"Error: show_confirmation_dialog called with invalid parent window for folder: {folder_name}")
        return

    dialog = ToplevelIco(parent_window, APP_ICON)
    dialog.title("Confirm Delete")

    try:
        font_semibold_12 = ("Cascadia Code SemiBold", 12)
        font_semibold_14 = ("Cascadia Code SemiBold", 14)
        font_regular_12 = ("Cascadia Code", 12)
    except Exception as e:
        print(f"Error creating Font objects: {e}")
        font_semibold_12 = ("Arial", 12, "bold")
        font_semibold_14 = ("Arial", 14, "bold")
        font_regular_12 = ("Arial", 12)

    dialog.geometry("400x150")
    dialog.minsize(400, 150)
    dialog.resizable(False, False)
    dialog.center_window()

    label = ctk.CTkLabel(dialog,
                        text=f"Are you sure you want to delete the category '{folder_name}'?",
                        font=font_semibold_14,
                        wraplength=380)
    label.pack(pady=(20, 10), padx=10)

    checkbox_var = ctk.StringVar(value="0")
    checkbox = ctk.CTkCheckBox(dialog,
                               text="Don't ask again",
                               variable=checkbox_var,
                               onvalue="1", offvalue="0",
                               checkbox_width=18, checkbox_height=18,
                               font=font_regular_12)
    checkbox.pack(pady=(15, 10))

    button_frame = ctk.CTkFrame(dialog, fg_color="#242424")
    button_frame.pack(pady=10, fill='x')

    def on_yes():
        should_save_dont_show = checkbox_var.get() == "1"
        dialog.destroy()
        if should_save_dont_show:
            save_config(dont_show_again=True)
        on_confirm_callback()

    def on_no():
        dialog.destroy()

    yes_button = ctk.CTkButton(button_frame,
                            text="Yes",
                            width=80,
                            font=font_semibold_12,
                            command=on_yes)
    yes_button.pack(side="left", padx=(100, 0), pady=10)

    no_button = ctk.CTkButton(button_frame,
                            text="No",
                            width=80,
                            fg_color="#343638",
                            hover_color="#2d2a2e",
                            font=font_semibold_12,
                            command=on_no)
    no_button.pack(side="right", padx=(0, 100), pady=10)

    dialog.update_idletasks()

    try:
        req_width = label.winfo_reqwidth()
        req_height = label.winfo_reqheight()
        chk_height = checkbox.winfo_reqheight()
        btn_height = button_frame.winfo_reqheight()
        dialog.geometry(f"{max(400, req_width + 20)}x{req_height + chk_height + btn_height + 60}")
    except Exception:
        pass

    dialog.protocol("WM_DELETE_WINDOW", on_no)

    dialog.center_window() 
    dialog.transient(parent_window)
    dialog.grab_set()
    dialog.lift()
    dialog.focus_force()
    parent_window.wait_window(dialog)
# endregion


# region unsaved exit popup
def show_unsaved_changes_dialog(parent_window):
    """Shows a confirmation dialog for unsaved changes."""
    if not parent_window or not parent_window.winfo_exists():
        print("Error: show_unsaved_changes_dialog called with invalid parent window.")
        return "cancel" # Default to cancel if parent is invalid

    dialog = ToplevelIco(parent_window, APP_ICON)
    dialog.title("Unsaved Changes")
    dialog.result = "cancel" # Default result if 'X' is clicked

    try:
        font_semibold_12 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=12)
        font_semibold_14 = ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=14)
    except Exception as e:
        print(f"Error creating CTkFont objects: {e}")
        font_semibold_12 = ("Arial", 12, "bold")
        font_semibold_14 = ("Arial", 14, "bold")

    # --- Determine Scaling Factor ---
    scale_factor = 1.0
    if platform.system() == "Windows":
        try:
            scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0
        except Exception:
            try: # Fallback using parent window if ctypes fails
                scale_factor = ctk.ScalingTracker.get_window_dpi_scaling(parent_window.winfo_id())
            except Exception:
                print(f"Error getting scaling factor: {e}")

    dialog.geometry("330x140")
    dialog.minsize(330, 140)
    dialog.resizable(False, False)
    dialog.center_window()


    label = ctk.CTkLabel(dialog,
                        text="You have unsaved changes. What would you like to do?",
                        font=font_semibold_14,
                        wraplength=330)
    label.pack(pady=(25, 15), padx=(16,10))

    button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    button_frame.pack(pady=(18,0), fill='x')

    # --- Button Definitions ---
    def on_save():
        dialog.result = "save"
        dialog.destroy()

    def on_discard():
        dialog.result = "discard"
        dialog.destroy()

    def on_cancel(): # Treat 'X' as Cancel
        dialog.result = "cancel"
        dialog.destroy()


    save_button = ctk.CTkButton(button_frame,
                                text="Save",
                                width=80,
                                font=font_semibold_12,
                                command=on_save)

    discard_button = ctk.CTkButton(button_frame,
                                   text="Discard",
                                   width=80,
                                   fg_color="#B04848",
                                   hover_color="#8E3B3B",
                                   font=font_semibold_12,
                                   command=on_discard)

    # TEMPORARY UI FIX, WILL ADD LAYOUT FOR EACH SCALING LATER 100, 125 ...
    if scale_factor == 1.0:
        # Add more bottom padding to frame and space between buttons for 100% scaling
        button_frame.pack(pady=(18, 10), fill='x') # Increased bottom padding
        save_button.pack(side="left", padx=(90, 10), pady=10) # Reduced outer, added inner padding
        discard_button.pack(side="right", padx=(10, 90), pady=10) # Reduced outer, added inner padding
    else:
        # Default padding for other scaling factors
        button_frame.pack(pady=(18, 0), fill='x')
        save_button.pack(side="left", padx=(100, 0), pady=10)
        discard_button.pack(side="right", padx=(0, 100), pady=10)

    dialog.protocol("WM_DELETE_WINDOW", on_cancel) # Treat 'X' as Cancel

    dialog.update_idletasks()
    dialog.center_window()
    dialog.transient(parent_window)
    dialog.grab_set()
    dialog.lift()
    dialog.focus_force()
    parent_window.wait_window(dialog)

    return dialog.result
# endregion


# region set path root/popup
def _select_and_set_folder_path(popup_to_close):
    """Opens dialog, saves path, updates main GUI if possible, closes popup."""
    folder_path = ctk.filedialog.askdirectory()
    if folder_path:
        save_config(folder_path=folder_path)

        # Try to update the main ConfigWindow's path entry if it exists
        global app
        if app and app.winfo_exists():
            try:
                # Schedule the update on the main GUI thread just in case
                app.after(0, lambda p=folder_path: app.refresh_path_entry(p))
            except Exception as e:
                print(f"Error refreshing main window path entry: {e}")

        # Close the popup that triggered this
        if popup_to_close and popup_to_close.winfo_exists():
            # Use after(0, ...) to ensure this runs after the current event handling
            popup_to_close.after(0, popup_to_close.destroy)

        # Reset global references if the popup being closed is one of the tracked ones
        global path_popup_window, standalone_popup_window
        if popup_to_close == path_popup_window:
            path_popup_window = None
        elif popup_to_close == standalone_popup_window:
            standalone_popup_window = None # Should already be handled by finally, but belt-and-suspenders

def _destroy_standalone_popup():
    """Safely destroys the standalone popup window if it exists."""
    global standalone_popup_window
    if standalone_popup_window and standalone_popup_window.winfo_exists():
        try:
            standalone_popup_window.after(0, standalone_popup_window.destroy)
        except Exception as e:
            print(f"Error scheduling standalone popup destroy: {e}")
    standalone_popup_window = None

def path_prompt_popup(message):
    """Show a popup message with a 'Set' button"""

    global app, path_popup_window, standalone_popup_window, standalone_popup_thread

    def setup_popup(popup_instance, message):
        def on_popup_quit():
            if popup_instance == standalone_popup_window:
                _destroy_standalone_popup()
            else:
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
        set_button = ctk.CTkButton(popup_instance, text="Set", width=50, font=("Cascadia Code SemiBold", 12),
                                   command=lambda: _select_and_set_folder_path(popup_instance))
        set_button.pack(pady=10, anchor="center")

    if app and app.winfo_exists():
        if path_popup_window and path_popup_window.winfo_exists():
             path_popup_window.focus_force()
             return
        path_popup_window = ToplevelIco(app, APP_ICON)
        setup_popup(path_popup_window, message)

        path_popup_window.update_idletasks() # ensure size is calculated
        path_popup_window.center_window() # center relative to parent (app)
        path_popup_window.transient(app)
        path_popup_window.grab_set()
        path_popup_window.lift()
        path_popup_window.focus_force()

    else:
        if standalone_popup_window and standalone_popup_window.winfo_exists():
            standalone_popup_window.focus_force()
            return
        if standalone_popup_thread and standalone_popup_thread.is_alive():
            print("Standalone popup thread already running.")
            return

        def _standalone_popup_target():
            global standalone_popup_window
            try:
                standalone_popup_window = ctk.CTk()
                setup_popup(standalone_popup_window, message) # Setup content 

                # Ensure widgets are created and size is measurable
                standalone_popup_window.update_idletasks()

                # get Scaling Factor
                scale_factor = 1.0
                if platform.system() == "Windows":
                    try:
                        # Use ctypes to get primary monitor scaling
                        scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0
                        print(f"Standalone Popup: Detected Windows Scale Factor: {scale_factor}")
                    except Exception as e:
                        print(f"Standalone Popup: Could not get scale factor via ctypes: {e}. Falling back to 1.0.")


                # get window size and screen size
                width = standalone_popup_window.winfo_reqwidth()
                height = standalone_popup_window.winfo_reqheight()
                screen_width = standalone_popup_window.winfo_screenwidth()
                screen_height = standalone_popup_window.winfo_screenheight()

                # Apply scaling factor to window width and height
                actual_width = int(width * scale_factor)
                actual_height = int(height * scale_factor)

                # Calculate top-left corner (x, y) for window
                x = (screen_width // 2) - (actual_width // 2)
                y = (screen_height // 2) - (actual_height // 2)

                # Set final geometry (size and position) 
                standalone_popup_window.geometry(f'{width}x{height}+{x}+{y}')

                standalone_popup_window.lift()
                standalone_popup_window.focus_force()
                standalone_popup_window.mainloop()

            finally: # Cleanup
                standalone_popup_window = None
                print("Standalone popup closed.")

        print("Starting standalone popup thread.")
        standalone_popup_thread = Thread(target=_standalone_popup_target, daemon=True)
        standalone_popup_thread.start()
# endregion


# region validate input
def validate_input(parent_window, folder_name, extensions, original_folder=None):
    """Validate folder name and extensions against the current config."""
    current_config = load_config()
    folder_path = current_config.get('folder_path', '')
    mapping = current_config.get('folder_extensions_mapping', {})

    folder_name_stripped = folder_name.strip()
    if not folder_name_stripped:
        return False, "Folder name cannot be empty."

    if folder_path and folder_name_stripped.strip('/') and path.exists(path.join(folder_path, folder_name_stripped)):
        should_prompt = False
        if original_folder is None:
            should_prompt = True
        elif original_folder is not None and folder_name_stripped.lower() != original_folder[0].lower():
             should_prompt = True

        if should_prompt:
            use_same_folder = show_folder_exists_dialog(parent_window, folder_path, folder_name_stripped)
            if not use_same_folder:
                return None, ""

    from config_manager import reserved_names

    invalid_folder_chars_pattern = compile(r'[\\:*?"<>|]')
    invalid_extension_chars_pattern = compile(r'[\\/:*?"<>|]')

    if invalid_folder_chars_pattern.search(folder_name_stripped):
        return False, f"Folder name '{folder_name_stripped}' contains invalid characters (\\:*?\"<>|)."
    if folder_name_stripped.upper() in reserved_names:
        return False, f"Folder name '{folder_name_stripped}' is a reserved name."
    if '//' in folder_name_stripped or '\\\\' in folder_name_stripped:
        return False, f"Folder name '{folder_name_stripped}' contains multiple consecutive slashes or backslashes."
    if folder_name_stripped.strip('/') == '':
        return False, "Folder name cannot be just slashes."
    if folder_name_stripped.startswith('/') or folder_name_stripped.endswith('/'):
        return False, "Folder name cannot start or end with a slash."
    if folder_name_stripped.startswith('\\') or folder_name_stripped.endswith('\\'):
         return False, "Folder name cannot start or end with a backslash."

    folder_name_lower = folder_name_stripped.lower()
    for existing_folder in mapping:
        existing_folder_lower = existing_folder.lower()

        if original_folder is None:
            if folder_name_lower == existing_folder_lower:
                return False, f"Folder name '{folder_name_stripped}' already exists in the configuration."
        else:
            original_folder_lower = original_folder[0].lower()
            if folder_name_lower == existing_folder_lower and existing_folder_lower != original_folder_lower:
                return False, f"Folder name '{folder_name_stripped}' already exists in the configuration (used by '{existing_folder}')."

    # --- Extension validation ---
    cleaned_extensions = [] # Keep track for cross-category check

    for ext in extensions:
        ext_stripped = ext.strip().lstrip('.')
        if not ext_stripped: continue # Skip empty entries

        # Basic character validation
        if invalid_extension_chars_pattern.search(ext_stripped):
            return False, f"Extension '{ext_stripped}' contains invalid characters (\\/:*?\"<>|)."
        if ext_stripped.upper() in reserved_names:
            return False, f"Extension '{ext_stripped}' is a reserved name."

        ext_lower = ext_stripped.lower()

        # Check against other existing categories
        for existing_folder, existing_extensions in mapping.items():
            existing_folder_lower = existing_folder.lower()
            existing_extensions_lower = [e.lower().lstrip('.') for e in existing_extensions]

            is_adding = original_folder is None
            is_editing_different_category = not is_adding and existing_folder_lower != original_folder[0].lower()

            if (is_adding or is_editing_different_category) and ext_lower in existing_extensions_lower:
                 return False, f"Extension '{ext_stripped}' is already assigned to folder '{existing_folder}'."

        cleaned_extensions.append(ext_stripped) # Add for cross-category check

    # Check if at least one valid extension was provided
    if not cleaned_extensions:
        return False, "At least one valid extension is required."

    return True, "" # Validation passed
# endregion


# region helper functions
def process_extensions_string(extensions_str):
    """
    Takes a comma-separated string of extensions, cleans them,
    removes duplicates while preserving the order of the first occurrence.
    Returns a list of unique, cleaned extensions in order.
    """
    raw_extensions_list = [ext.strip().lstrip('.').lower() for ext in extensions_str.split(',') if ext.strip()]
    seen_extensions = set()
    ordered_unique_extensions = []
    for ext in raw_extensions_list:
        if ext not in seen_extensions:
            ordered_unique_extensions.append(ext)
            seen_extensions.add(ext)
    return ordered_unique_extensions
# endregion


# region CategoryRow
class CategoryRow(ctk.CTkFrame):
    def __init__(self, master, config_window, folder_name, extensions, fonts, delete_icon):
        super().__init__(master, width=450)
        self.pack(fill="x", padx=2, pady=0)

        self.config_window = config_window
        self.original_folder = folder_name
        self.original_extensions_str = ', '.join(extensions)
        self.fonts = fonts
        self.delete_icon = delete_icon
        self.is_dirty = False # to track unsaved changes

        label_frame = ctk.CTkFrame(self, corner_radius=10, width=200, height=40)
        label_frame.pack_propagate(False)
        label_frame.pack(side="left", padx=(5,2), pady=5)

        self.folder_entry_var = ctk.StringVar(value=self.original_folder)

        self.folder_entry = ctk.CTkEntry(label_frame, font=self.fonts['regular_12'], textvariable=self.folder_entry_var)
        self.folder_entry.pack(expand=True, fill="both", padx=5, pady=5)

        self.extensions_textbox = ctk.CTkTextbox(self, width=200, height=60, font=self.fonts['regular_12'])
        self.extensions_textbox.pack(side="left", padx=(12,0), pady=5)
        self.extensions_textbox.insert("1.0", self.original_extensions_str)

        self.extensions_textbox.bind("<Enter>", lambda e: self._on_textbox_enter(e), add="+")
        self.extensions_textbox.bind("<Leave>", lambda e: self._on_textbox_leave(e), add="+")

        self.button_frame = ctk.CTkFrame(self, width=90, height=40, fg_color="#2b2b2b")
        self.button_frame.pack_propagate(False)
        self.button_frame.pack(side="left", padx=(7,0), pady=5)

        self.remove_button = ctk.CTkButton(self.button_frame, width=25, height=25, fg_color="#343638", hover_color='#65000B',
                                           image=self.delete_icon, text="", command=self.delete_category)
        self.remove_button.place(relx=0.5, rely=0.5, anchor="center")

        self.save_button = ctk.CTkButton(self.button_frame, text="Save", width=30, height=25, fg_color="#343638",
                                         hover_color='#253417', text_color='#94be6b', font=self.fonts['regular_9'],
                                         command=self._handle_save_button_click)
        self.save_button.pack_forget()

        self.reset_button = ctk.CTkButton(self.button_frame, text="Reset", width=30, height=25, fg_color="#343638",
                                          hover_color='#461505', text_color='#f06a3f', font=self.fonts['regular_9'],
                                          command=self.reset_fields)
        self.reset_button.pack_forget()

        self.folder_entry_var.trace_add("write", self._on_entry_change)
        self.extensions_textbox.bind("<KeyRelease>", self._on_textbox_change)

    def _handle_change(self, is_changed):
        """Handle UI changes when field values change.

        This method updates the visibility of the Save, Reset, and Remove buttons
        based on whether the folder name or extensions have been modified from
        their original saved state. It also sets the `is_dirty` flag which is
        used to track unsaved changes when closing the configuration window."""
        self.is_dirty = is_changed # Update dirty state
        if is_changed:
            # Show Save and Reset buttons, hide Remove button
            self.save_button.pack(side="left", padx=2, pady=5)
            self.remove_button.place_forget()
            self.reset_button.pack(side="right", padx=2, pady=5)
        else:
            # Hide Save and Reset buttons, show Remove button
            self.save_button.pack_forget()
            self.reset_button.pack_forget()
            self.remove_button.place(relx=0.5, rely=0.5, anchor="center")

    def _on_entry_change(self, *args):
        """Handle folder name entry changes"""
        new_folder_name = self.folder_entry_var.get().strip()
        current_extensions = self.extensions_textbox.get("1.0", "end-1c").strip()
        # Check if current values differ from the last saved state
        is_changed = (new_folder_name != self.original_folder or
                      current_extensions != self.original_extensions_str)
        self._handle_change(is_changed) # Update UI based on change status

    def _on_textbox_change(self, event=None):
        """Handle extensions textbox changes"""
        current_folder = self.folder_entry_var.get().strip()
        new_ext = self.extensions_textbox.get("1.0", "end-1c").strip()
        # Check if current values differ from the last saved state
        is_changed = (current_folder != self.original_folder or
                      new_ext != self.original_extensions_str)
        self._handle_change(is_changed) # Update UI

    def _handle_save_button_click(self):
        """Handles the click of the row's save button, showing errors if necessary."""
        save_result = self.save_entry_changes()
        if isinstance(save_result, str): # Check if validation returned an error message
            show_error_dialog(self.config_window, save_result)
        # If save_result is True (success) or False (user cancelled sub-dialog), do nothing further here.

    def save_entry_changes(self):
        """Save changes to folder name and extensions, preserving order."""
        new_folder_name = self.folder_entry_var.get().strip()
        new_extensions_str = self.extensions_textbox.get("1.0", "end-1c").strip()

        # Use the helper function
        ordered_unique_extensions = process_extensions_string(new_extensions_str)

        # Use ordered_unique_extensions for validation
        is_valid, error_message = validate_input(self.config_window, new_folder_name, ordered_unique_extensions, original_folder=(self.original_folder,))

        if is_valid is None:
            return False
        if not is_valid:
            return error_message

        # --- Save logic ---
        config_data = load_config()
        config_data['folder_extensions_mapping'].pop(self.original_folder, None)
        config_data['folder_extensions_mapping'][new_folder_name] = ordered_unique_extensions
        save_config(folder_extensions_mapping=config_data['folder_extensions_mapping'])

        self.original_folder = new_folder_name
        self.original_extensions_str = ', '.join(ordered_unique_extensions)

        self.extensions_textbox.delete("1.0", "end")
        self.extensions_textbox.insert("1.0", self.original_extensions_str)

        self._handle_change(False)

        return True

    def reset_fields(self):
        """Resets the fields to their original values."""
        self.folder_entry_var.set(self.original_folder)
        self.extensions_textbox.delete("1.0", "end")
        self.extensions_textbox.insert("1.0", self.original_extensions_str)
        self._handle_change(False) # sets is_dirty to False

    def delete_category(self):
        """Delete this category."""
        folder_name_to_delete = self.original_folder

        def on_confirm():
            """Actual deletion logic, called after confirmation."""
            config_data = load_config()
            config_data['folder_extensions_mapping'].pop(folder_name_to_delete, None)
            save_config(folder_extensions_mapping=config_data['folder_extensions_mapping'])
            self.config_window.render_scrollable_widget()

        current_config = load_config()
        if current_config.get('dont_show_again', False):
             on_confirm()
        else:
             show_confirmation_dialog(self.config_window, folder_name_to_delete, on_confirm)

    def _scroll_textbox(self, event):
        """Scrolls the textbox if scrollable, otherwise allows event propagation."""
        first, last = self.extensions_textbox.yview()
        is_scrollable = first != 0.0 or last != 1.0
        if is_scrollable:
            if event.num == 5 or event.delta < 0:
                self.extensions_textbox.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:
                self.extensions_textbox.yview_scroll(-1, "units")
            return "break"
        else:
            pass

    def _on_textbox_enter(self, event):
        """Bind mouse wheel to textbox scroll handler when mouse enters."""
        self.extensions_textbox.bind("<MouseWheel>", self._scroll_textbox, add="+")
        self.extensions_textbox.bind("<Button-4>", self._scroll_textbox, add="+")
        self.extensions_textbox.bind("<Button-5>", self._scroll_textbox, add="+")

    def _on_textbox_leave(self, event):
        """Unbind mouse wheel from textbox scroll handler when mouse leaves."""
        self.extensions_textbox.unbind("<MouseWheel>")
        self.extensions_textbox.unbind("<Button-4>")
        self.extensions_textbox.unbind("<Button-5>")
# endregion


# region ConfigWindow
class ConfigWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Configure Folder Sorter")
        self.iconbitmap(APP_ICON)
        self.resizable(False, True)
        self.protocol("WM_DELETE_WINDOW", self.on_app_quit)
        # Store initial logical dimensions for child popup windows to use
        self.initial_width = 547
        self.initial_height = 700
        # Use these stored values for the initial geometry setting
        width = self.initial_width
        height = self.initial_height

        try:
            self.fonts = {
                'regular_9': ctk.CTkFont(family=REGULAR_FONT.getname()[0], size=9),
                'regular_11': ctk.CTkFont(family=REGULAR_FONT.getname()[0], size=11),
                'regular_12': ctk.CTkFont(family=REGULAR_FONT.getname()[0], size=12),
                'semibold_12': ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=12),
                'semibold_13': ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=13),
                'semibold_14': ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=14),
            }
            self.delete_icon = ctk.CTkImage(
                light_image=Image.open(DELETE_PNG),
                dark_image=Image.open(DELETE_PNG),
                size=(10,10)
            )
        except Exception as e:
            print(f"Error creating CTkFont objects or loading image: {e}")
            sys.exit(1)

        self._build_path_frame()
        self._build_add_frame()
        self._build_scrollable_frame()

        # --- Center the main window ---
        self.update_idletasks() # Ensure window and widgets exist and sizes are calculated

        # get the scaling factor set by windows
        scale_factor = 1.0
        if platform.system() == "Windows":
            try:
                # GetScaleFactorForDevice(0) returns the scale factor for the primary monitor (e.g., 100, 125, 150)
                scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0
                print(f"Detected Windows Scale Factor: {scale_factor}")

            except Exception as e:
                print(f"Could not get scale factor via ctypes: {e}")
                # Try getting scaling from CustomTkinter after window creation
                try:
                    scale_factor = ctk.ScalingTracker.get_window_dpi_scaling(self.winfo_id())
                    print(f"Detected CustomTkinter Window DPI Scaling: {scale_factor}")
                except Exception as e_ctk:
                    print(f"Could not get scaling via CustomTkinter: {e_ctk}. Falling back to 1.0.")

        # get display size
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Apply scaling factor to window width and height
        actual_width = int(width * scale_factor)
        actual_height = int(height * scale_factor)

        # Calculate top-left corner (x, y) for window
        x = (screen_width // 2) - (actual_width // 2)
        y = (screen_height // 2) - (actual_height // 2)

        # Set final geometry (size and position)
        self.geometry(f'{width}x{height}+{x}+{y}')

        file_sorter.set_gui_callbacks(
            self,
            lambda msg: show_error_dialog(self, msg),
            self.focus_app
        )

        self.render_scrollable_widget()
        self.lift()
        self.focus_app()

    def get_category_rows(self):
        """Returns a list of all CategoryRow widgets."""
        return [widget for widget in self.scrollable_frame.winfo_children()
                if isinstance(widget, CategoryRow)]

    def has_unsaved_changes(self):
        """Checks if any CategoryRow has unsaved changes."""
        for row in self.get_category_rows():
            if row.is_dirty:
                return True
        return False

    def save_all_changes(self, render_on_success=True):
        """Attempts to save changes in all dirty CategoryRow widgets.
        Args:
            render_on_success (bool): If True, re-renders the scrollable widget
                                      if any changes were successfully saved.
        Returns:
            True if all saves were successful.
            False if the user cancelled a sub-dialog during the save process.
            str: The error message from the first validation failure encountered.
        """
        rows_to_rerender = False
        first_error = None
        user_cancelled = False

        # Create a list to avoid issues if render_scrollable_widget modifies the children during iteration
        rows_to_process = self.get_category_rows()

        for row in rows_to_process:
            if row.is_dirty:
                save_result = row.save_entry_changes()

                if isinstance(save_result, str): # Validation error occurred
                    first_error = save_result
                    break # Stop processing on the first error
                elif save_result is False: # User cancellation in a sub-dialog
                    user_cancelled = True
                    break # Stop processing on cancellation
                elif save_result is True: # Successful save for this row
                    rows_to_rerender = True

        if first_error:
            return first_error # Return the specific validation error message

        if user_cancelled:
            print("Save operation cancelled by user in a sub-dialog.")
            return False # Indicate cancellation occurred

        # Only re-render if no errors/cancellations stopped us,
        # some rows were actually saved, AND we are asked to render on success
        if rows_to_rerender and render_on_success: 
            self.render_scrollable_widget()

        return True # All dirty rows were processed successfully without errors or cancellations

    def on_app_quit(self):
        """Handles the application quit event, checking for unsaved changes."""
        if self.has_unsaved_changes():
            result = show_unsaved_changes_dialog(self)
            if result == "save":
                # Call save_all_changes, but tell it not to re-render ui on success
                save_outcome = self.save_all_changes(render_on_success=False)

                if save_outcome is True:
                    # All changes saved successfully
                    self._perform_quit() # Proceed to quit immediately
                elif isinstance(save_outcome, str):
                    # A validation error occurred, show the specific message
                    show_error_dialog(self, f"Failed to save changes:\n\n{save_outcome}")
                    # Do not quit, allow the user to fix the error
                    return
                elif save_outcome is False:
                    # User cancelled a sub-dialog during save_all_changes
                    # No error message needed, just don't quit
                    return

            elif result == "discard":
                self._perform_quit()
            elif result == "cancel":
                # User cancelled the unsaved changes dialog
                return
        else:
            # No unsaved changes
            self._perform_quit()

    def _perform_quit(self):
        """Actually destroys the window and cleans up."""
        global app
        # Clear the global reference in this module
        if app is self:
            app = None
        # Also clear the reference held by file_sorter
        if file_sorter.gui_app_instance is self:
            file_sorter.gui_app_instance = None
            file_sorter.show_error_dialog = None # Clear associated callbacks too
            file_sorter.focus_app = None

        global standalone_popup_thread, standalone_popup_window
        self.destroy()
        print("Config GUI closed.")

    def focus_app(self):
        self.focus_force()

    def _build_path_frame(self):
        """Creates the top frame for folder path selection."""
        config_data = load_config()
        path_frame = ctk.CTkFrame(self)
        path_frame.pack(fill="x", padx=10, pady=10)

        path_label = ctk.CTkLabel(path_frame, text="Folder Path:", font=self.fonts['semibold_14'])
        path_label.pack(side="left", padx=(10, 5), pady=7)

        self.path_entry = ctk.CTkEntry(path_frame, font=self.fonts['regular_11'])
        self.path_entry.pack(side="left", fill="x", expand=True, padx=5, pady=7)
        self.path_entry.configure(state='disabled')

        self.tooltip = CTkToolTip(self.path_entry, message=config_data.get('folder_path', "No Path Set"),
                                  x_offset=-5, y_offset=20, alpha=0.87, font=('Cascadia Code', 12))
        self.refresh_path_entry(config_data.get('folder_path', ''))

        browse_button = ctk.CTkButton(path_frame, text="Browse", width=12, font=self.fonts['regular_12'], command=self.select_folder)
        browse_button.pack(side="right", padx=(7,8), pady=7)


    def refresh_path_entry(self, new_path):
        """Update the path entry with a new path"""
        if not new_path:
            new_path = ""
        try:
            self.path_entry.configure(state='normal')
            self.path_entry.delete(0, ctk.END)
            self.path_entry.insert(0, new_path)
            self.path_entry.configure(state='disabled')
            self.tooltip.configure(message=new_path if new_path else "No Path Set")
        except Exception:
            pass

    def select_folder(self):
        """Open folder selection dialog and update path"""
        folder_path = ctk.filedialog.askdirectory()
        if folder_path:
            save_config(folder_path=folder_path)

            global path_popup_window
            if path_popup_window:
                self.refresh_path_entry(folder_path)
                path_popup_window.destroy()
                path_popup_window = None
            elif self.path_entry:
                self.refresh_path_entry(folder_path)

    def _build_add_frame(self):
        """Creates the frame for adding new categories."""
        add_frame = ctk.CTkFrame(self)
        add_frame.pack(fill="x", padx=10, pady=(0,13))
        add_frame.columnconfigure(0, weight=1)
        add_frame.columnconfigure(1, weight=3)

        new_category_label = ctk.CTkLabel(add_frame, text="New Category Name:", font=self.fonts['semibold_13'])
        new_category_label.grid(row=0, column=0, sticky="w", padx=(10, 5), pady=7)
        self.new_category_entry = ctk.CTkEntry(add_frame, height=25, font=self.fonts['regular_12'])
        self.new_category_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=7)

        new_extensions_label = ctk.CTkLabel(add_frame, text="Extensions (comma separated):", font=self.fonts['semibold_13'])
        new_extensions_label.grid(row=1, column=0, sticky="w", padx=(10, 5), pady=7)
        self.new_extensions_entry = ctk.CTkEntry(add_frame, height=25, font=self.fonts['regular_12'])
        self.new_extensions_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=7)

        add_button = ctk.CTkButton(add_frame, text="Add", width=6, font=self.fonts['regular_12'], command=self.add_category)
        add_button.grid(row=2, column=1, sticky="e", padx=6, pady=(0,7))

    def add_category(self):
        """Adds a new category from the input fields, preserving extension order."""
        folder_name = self.new_category_entry.get().strip()
        extensions_input = self.new_extensions_entry.get().strip()

        # Use the helper function
        ordered_unique_extensions = process_extensions_string(extensions_input)

        # Use ordered_unique_extensions for validation
        is_valid, error_message = validate_input(self, folder_name, ordered_unique_extensions)
        if is_valid is None: return
        if not is_valid:
            show_error_dialog(self, error_message)
            return

        config_data = load_config()
        config_data['folder_extensions_mapping'][folder_name] = ordered_unique_extensions
        save_config(folder_extensions_mapping=config_data['folder_extensions_mapping'])

        self.render_scrollable_widget()

        self.new_category_entry.delete(0, ctk.END)
        self.new_extensions_entry.delete(0, ctk.END)

    def _build_scrollable_frame(self):
        """Creates the main scrollable frame."""
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))
        scrollbar = self.scrollable_frame._scrollbar
        scrollbar.configure(width=6)

    def render_scrollable_widget(self):
        """Renders the list of existing categories using CategoryRow."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        header_frame = ctk.CTkFrame(self.scrollable_frame)
        header_frame.pack(fill="x", padx=5, pady=10)
        folders_frame = ctk.CTkFrame(header_frame, corner_radius=8, fg_color="#242424")
        folders_frame.pack(side="left", padx=(68, 0))
        folders_label = ctk.CTkLabel(folders_frame, text="Folders", font=self.fonts['semibold_12'])
        folders_label.pack(padx=7)
        extensions_frame = ctk.CTkFrame(header_frame, corner_radius=8, fg_color="#242424")
        extensions_frame.pack(side="left", padx=(140, 0))
        extensions_label = ctk.CTkLabel(extensions_frame, text="Extensions", font=self.fonts['semibold_12'])
        extensions_label.pack(padx=7)

        config_data = load_config()
        sorted_folder_extensions = sorted(config_data['folder_extensions_mapping'].items(), key=lambda item: item[0].lower())

        for folder, extensions in sorted_folder_extensions:
            CategoryRow(
                master=self.scrollable_frame,
                config_window=self,
                folder_name=folder,
                extensions=extensions,
                fonts=self.fonts,
                delete_icon=self.delete_icon
            )
# endregion


# region run gui
def launch_config_gui():
    """Launches the main configuration GUI window."""
    global app
    if app and app.winfo_exists():
        print("Config window already open. Focusing.")
        app.focus_app()
        return app

    print("Launching new config window.")
    config_window = ConfigWindow()
    app = config_window
    config_window.mainloop()
    return config_window
# endregion