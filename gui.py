# region imports/inits
import ctypes
import platform 
import os
import types
import subprocess

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
    APP_ICON, DELETE_PNG, SETTINGS_PNG, REGULAR_FONT, SEMIBOLD_FONT
)
import file_sorter
from tray_handler import restart_watcher_if_running, pause_watching, resume_watching

# Force dark mode (realized light mode is broken, will fix soon)
ctk.set_appearance_mode("dark")

# Global variables to hold references to main GUI elements and threads.
app = None                     # Main configuration window (CTk)
path_popup_window = None       # Transient popup window (ToplevelIco, child)
standalone_popup_window = None # Standalone popup window (CTk, own thread)
standalone_popup_thread = None # Thread for the standalone popup

# --- Global Font Dictionary - Initialized with Fallbacks ---
FONTS = {
    'regular_9': ("Arial", 9),
    'regular_11': ("Arial", 11),
    'regular_12': ("Arial", 12),
    'semibold_11': ("Arial", 11, "bold"),
    'semibold_12': ("Arial", 12, "bold"),
    'semibold_13': ("Arial", 13, "bold"),
    'semibold_14': ("Arial", 14, "bold"),
    'confirmation_regular_12': ("Arial", 12),
}
_app_fonts_initialized = False

def initialize_app_fonts():
    """
    Tries to initialize the global FONTS dictionary with CTkFont objects.
    Should be called after a root ctk window is available.
    """
    global FONTS, _app_fonts_initialized
    # Only attempt if not already successfully initialized with CTkFont objects
    # or if the current fonts are still tuples (indicating fallback)
    if not _app_fonts_initialized or isinstance(FONTS.get('regular_9'), tuple):
        print("Attempting to initialize CTkFont objects...")
        try:
            # Ensure REGULAR_FONT and SEMIBOLD_FONT are valid font objects
            # from which getname() can be called. This assumes they are loaded
            # correctly by config_manager.
            if REGULAR_FONT is None or SEMIBOLD_FONT is None:
                print("Warning: REGULAR_FONT or SEMIBOLD_FONT not loaded. Cannot create CTkFont objects.")
                _app_fonts_initialized = False # Mark as failed if base fonts are missing
                return

            created_fonts = {
                'regular_9': ctk.CTkFont(family=REGULAR_FONT.getname()[0], size=9),
                'regular_11': ctk.CTkFont(family=REGULAR_FONT.getname()[0], size=11),
                'regular_12': ctk.CTkFont(family=REGULAR_FONT.getname()[0], size=12),
                'semibold_11': ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=11),
                'semibold_12': ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=12),
                'semibold_13': ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=13),
                'semibold_14': ctk.CTkFont(family=SEMIBOLD_FONT.getname()[0], size=14),
            }
            # Use the newly created CTkFont for confirmation_regular_12 if regular_12 was created
            created_fonts['confirmation_regular_12'] = created_fonts.get('regular_12', FONTS['confirmation_regular_12'])
            
            FONTS.update(created_fonts) # Update the global dictionary
            _app_fonts_initialized = True
            print("CTkFont objects initialized successfully.")
        except AttributeError as ae:
            # This can happen if REGULAR_FONT.getname() fails because the font wasn't loaded
            print(f"Note: AttributeError during CTkFont creation (likely font not loaded by FontManager) - {ae}. Using fallback tuple fonts.")
            _app_fonts_initialized = False
        except Exception as e:
            _app_fonts_initialized = False # Failed to init with CTkFont
            # FONTS will retain its tuple-based fallbacks
            print(f"Note: Error creating CTkFont objects - {e}. Using fallback tuple fonts.")
# endregion


# region custom CTkToplevel
class ToplevelIco(ctk.CTkToplevel):
    """Custom CTkToplevel that fixes icon updation bug"""
    def __init__(self, master=None, icon_path=None):
        super().__init__(master)
        if icon_path:
            self.after(201, lambda: self.iconbitmap(icon_path))

    def center_window(self, width=None, height=None):
        self.update_idletasks() # Ensure dialog measurements are up to date

        dialog_width = width if width is not None else self.winfo_width()
        dialog_height = height if height is not None else self.winfo_height()

        if not self.master or not self.master.winfo_exists():
            print("Error: Cannot center dialog, master window invalid.")
            # Fallback: center on screen
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = max(0, (screen_width // 2) - (dialog_width // 2))
            y = max(0, (screen_height // 2) - (dialog_height // 2))
            self.geometry(f'{dialog_width}x{dialog_height}+{x}+{y}')
            return

        try:
            # --- Get Scaling Factor (Prioritize ctypes on Windows) ---
            scale_factor = 1.0
            if platform.system() == "Windows":
                try:
                    scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0
                except Exception as e_ctypes:
                    print(f"Dialog Center: Error getting scaling via ctypes ({e_ctypes}), trying CTk...")
                    try:
                        # Fallback to CTk ScalingTracker
                        self.master.update_idletasks() # Ensure master handle is ready
                        scale_factor = ctk.ScalingTracker.get_window_dpi_scaling(self.master.winfo_id())
                    except Exception as e_ctk:
                        print(f"Dialog Center: Error getting scaling via CTk ({e_ctk}), using 1.0.")
                        scale_factor = 1.0 # Ultimate fallback

            # --- Master Geometry ---
            master_x = self.master.winfo_x()
            master_y = self.master.winfo_y()
            master_logical_width = self.master.winfo_width()
            master_logical_height = self.master.winfo_height()

            # Calculate sizes and center
            master_actual_width = int(master_logical_width * scale_factor)
            master_actual_height = int(master_logical_height * scale_factor)
            dialog_actual_width = int(dialog_width * scale_factor)
            dialog_actual_height = int(dialog_height * scale_factor)

            # Calculate master's physical center on screen
            physical_master_center_x = master_x + (master_actual_width // 2)
            physical_master_center_y = master_y + (master_actual_height // 2)

            # Calculate dialog's top-left physical position
            x = physical_master_center_x - (dialog_actual_width // 2)
            y = physical_master_center_y - (dialog_actual_height // 2)

            # Ensure dialog is within screen bounds
            x = max(0, x)
            y = max(0, y)

            # Set geometry using potentially provided dialog size and calculated position
            geometry_string = f'{dialog_width}x{dialog_height}+{x}+{y}'
            self.geometry(geometry_string)

        except Exception as e: # Fallback if any error occurs during calculation
            print(f"Error during dialog centering: {e}")
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x_fb = max(0, (screen_width // 2) - (dialog_width // 2))
            y_fb = max(0, (screen_height // 2) - (dialog_height // 2))
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

    # Create main content frame with padding
    content_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    content_frame.pack(fill="both", expand=True, padx=20, pady=20)
    content_frame.columnconfigure(0, weight=1)
    content_frame.rowconfigure(0, weight=1)
    content_frame.rowconfigure(1, weight=0)

    label = ctk.CTkLabel(
        content_frame,
        text=message,
        font=FONTS['semibold_14'],
        wraplength=380,
        # justify="left"
    )
    label.grid(row=0, column=0, sticky="nsew", pady=(0, 15))

    button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    button_frame.grid(row=1, column=0, sticky="ew")
    button_frame.columnconfigure(0, weight=1)

    def on_ok():
        dialog.destroy()

    ok_button = ctk.CTkButton(
        button_frame,
        text="OK",
        width=80,
        font=FONTS['semibold_12'],
        text_color="#13140e",
        fg_color="#a3ab8a",
        hover_color="#858e6e",
        command=on_ok
    )
    ok_button.grid(row=0, column=0, pady=10)

    # Set minimum size and update
    dialog.update_idletasks()
    min_width = max(380, label.winfo_reqwidth() + 40) 
    min_height = label.winfo_reqheight() + ok_button.winfo_reqheight() + 80
    dialog.minsize(min_width, min_height)
    dialog.resizable(False, False)
    
    # Center on parent
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
    dialog.result = False  # Default result


    # Create main content frame with padding
    content_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    content_frame.pack(fill="both", expand=True, padx=20, pady=20)
    content_frame.columnconfigure(0, weight=1)
    content_frame.rowconfigure(0, weight=1)
    content_frame.rowconfigure(1, weight=0)

    # Message label
    label = ctk.CTkLabel(
        content_frame,
        text=f"Folder '{folder_name}' already exists in the list.",
        font=FONTS['semibold_14'],
        wraplength=380,
        # justify="left"
    )
    label.grid(row=0, column=0, sticky="nsew", pady=(0, 15))

    # Button frame
    button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    button_frame.grid(row=1, column=0, sticky="ew")
    
    # Configure button frame columns for spacing
    button_frame.columnconfigure(0, weight=1)
    button_frame.columnconfigure(1, weight=0)
    button_frame.columnconfigure(2, weight=1)
    button_frame.columnconfigure(3, weight=0)
    button_frame.columnconfigure(4, weight=1)

    def use_same_folder():
        dialog.result = True
        dialog.destroy()

    def rename():
        dialog.result = False
        dialog.destroy()

    use_button = ctk.CTkButton(
        button_frame,
        text="Use Same Folder",
        width=120,
        font=FONTS['semibold_12'],
        text_color="#13140e",
        fg_color="#a3ab8a",
        hover_color="#858e6e",
        command=use_same_folder
    )
    use_button.grid(row=0, column=1, padx=10, pady=10)

    rename_button = ctk.CTkButton(
        button_frame,
        text="Cancel",
        width=80,
        fg_color="#343638",
        hover_color="#2d2a2e",
        font=FONTS['semibold_12'],
        command=rename
    )
    rename_button.grid(row=0, column=3, padx=10, pady=10)

    # Set minimum size and update
    dialog.update_idletasks()
    min_width = max(380, label.winfo_reqwidth() + 40)
    min_height = label.winfo_reqheight() + button_frame.winfo_reqheight() + 80
    dialog.minsize(min_width, min_height)
    dialog.resizable(False, False)

    dialog.protocol("WM_DELETE_WINDOW", rename)
    dialog.center_window(width=min_width, height=min_height)
    dialog.transient(parent_window)
    dialog.grab_set()
    dialog.focus_force()
    parent_window.wait_window(dialog)

    return dialog.result
# endregion

# region Auto-sort confirmation
def show_auto_sort_confirmation_dialog(parent_window):
    """Shows a confirmation dialog for enabling auto-sort."""
    is_standalone = not (parent_window and parent_window.winfo_exists())

    if is_standalone:
        dialog_root = ctk.CTk()
        dialog_root.withdraw()
        initialize_app_fonts()
        dialog = ToplevelIco(dialog_root, APP_ICON)
    else:
        dialog_root = parent_window
        dialog = ToplevelIco(dialog_root, APP_ICON)

    dialog.title("Enable Auto-Sort?")
    dialog.result = False

    content_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    content_frame.pack(fill="both", expand=True, padx=20, pady=20)
    content_frame.columnconfigure(0, weight=1)
    content_frame.rowconfigure(0, weight=1)
    content_frame.rowconfigure(1, weight=0)
    content_frame.rowconfigure(2, weight=0)

    label = ctk.CTkLabel(
        content_frame,
        text="Enabling auto-sort will automatically move new files in the target folder.\n\nAre you sure you want to continue?",
        font=FONTS['semibold_14'],
        wraplength=380,
    )
    label.grid(row=0, column=0, sticky="nsew", pady=(0, 15))

    checkbox_var = ctk.StringVar(value="0")
    checkbox = ctk.CTkCheckBox(
        content_frame,
        text="Don't ask again",
        variable=checkbox_var,
        onvalue="1", offvalue="0",
        font=FONTS['semibold_12'],
        checkbox_width=18, checkbox_height=18
    )
    checkbox.grid(row=1, column=0, pady=(0, 15))

    button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    button_frame.grid(row=2, column=0, sticky="ew")
    button_frame.columnconfigure(0, weight=1)
    button_frame.columnconfigure(1, weight=0)
    button_frame.columnconfigure(2, weight=1)
    button_frame.columnconfigure(3, weight=0)
    button_frame.columnconfigure(4, weight=1)

    def on_yes():
        if checkbox_var.get() == "1":
            from config_manager import save_config
            save_config(show_auto_sort_confirmation=False)
        dialog.result = True
        dialog.destroy()

    def on_no():
        dialog.result = False
        dialog.destroy()

    yes_button = ctk.CTkButton(
        button_frame,
        text="Yes",
        width=80,
        font=FONTS['semibold_12'],
        text_color="#13140e",
        fg_color="#a3ab8a",
        hover_color="#858e6e",
        command=on_yes
    )
    yes_button.grid(row=0, column=1, padx=10, pady=10)

    no_button = ctk.CTkButton(
        button_frame,
        text="No",
        width=80,
        fg_color="#343638",
        hover_color="#2d2a2e",
        font=FONTS['semibold_12'],
        command=on_no
    )
    no_button.grid(row=0, column=3, padx=10, pady=10)

    dialog.update_idletasks()
    min_width = max(380, label.winfo_reqwidth() + 40)
    min_height = (label.winfo_reqheight() + checkbox.winfo_reqheight() +
                  button_frame.winfo_reqheight() + 80)
    dialog.minsize(min_width, min_height)
    dialog.resizable(False, False)

    dialog.protocol("WM_DELETE_WINDOW", on_no)

    if is_standalone:
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = max(0, (screen_width // 2) - (min_width // 2))
        y = max(0, (screen_height // 2) - (min_height // 2))
        dialog.geometry(f'{min_width}x{min_height}+{x}+{y}')
    else:
        dialog.center_window(width=min_width, height=min_height)

    if not is_standalone and parent_window and parent_window.winfo_exists():
        dialog.transient(parent_window)
    dialog.grab_set()
    dialog.focus_force()

    dialog_root.wait_window(dialog)

    if is_standalone and dialog_root.winfo_exists():
        dialog_root.destroy()

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

    # Create main content frame
    content_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    content_frame.pack(fill="both", expand=True, padx=20, pady=20)
    content_frame.columnconfigure(0, weight=1)
    content_frame.rowconfigure(0, weight=1) # Label
    content_frame.rowconfigure(1, weight=0) # Checkbox
    content_frame.rowconfigure(2, weight=0) # Buttons

    label = ctk.CTkLabel(
        content_frame,
        text=f"Are you sure you want to delete the category '{folder_name}'?",
        font=FONTS['semibold_14'],
        wraplength=380,
        # justify="left"
    )
    label.grid(row=0, column=0, sticky="nsew", pady=(0, 15))

    checkbox_var = ctk.StringVar(value="0")
    checkbox = ctk.CTkCheckBox(
        content_frame,
        text="Don't ask again",
        variable=checkbox_var,
        onvalue="1", offvalue="0",
        checkbox_width=18, checkbox_height=18,
        font=FONTS['semibold_12']
    )
    checkbox.grid(row=1, column=0, pady=(0, 15))

    button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    button_frame.grid(row=2, column=0, sticky="ew")
    button_frame.columnconfigure(0, weight=1)
    button_frame.columnconfigure(1, weight=0)
    button_frame.columnconfigure(2, weight=1)
    button_frame.columnconfigure(3, weight=0)
    button_frame.columnconfigure(4, weight=1)

    def on_yes():
        should_save_dont_show = checkbox_var.get() == "1"
        dialog.destroy()
        if should_save_dont_show:
            save_config(dont_show_again=True)
        on_confirm_callback()

    def on_no():
        dialog.destroy()

    yes_button = ctk.CTkButton(
        button_frame,
        text="Yes",
        width=80,
        font=FONTS['semibold_12'],
        text_color="#13140e",
        fg_color="#a3ab8a",
        hover_color="#858e6e",
        command=on_yes
    )
    yes_button.grid(row=0, column=1, padx=10, pady=10)

    no_button = ctk.CTkButton(
        button_frame,
        text="No",
        width=80,
        fg_color="#343638",
        hover_color="#2d2a2e",
        font=FONTS['semibold_12'],
        command=on_no
    )
    no_button.grid(row=0, column=3, padx=10, pady=10)

    # Set minimum size and update
    dialog.update_idletasks()
    min_width = max(380, label.winfo_reqwidth() + 40)
    min_height = (label.winfo_reqheight() + checkbox.winfo_reqheight() + 
                  button_frame.winfo_reqheight() + 80)
    dialog.minsize(min_width, min_height)
    dialog.resizable(False, False)

    dialog.protocol("WM_DELETE_WINDOW", on_no)
    dialog.center_window(width=min_width, height=min_height)
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
        return "cancel"

    dialog = ToplevelIco(parent_window, APP_ICON)
    dialog.title("Unsaved Changes")
    dialog.result = "cancel"  # Default result

    # Create main content frame
    content_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    content_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # Message label
    label = ctk.CTkLabel(
        content_frame,
        text="You have unsaved changes.",
        font=FONTS['semibold_14']
    )
    label.pack(pady=10)

    # Button frame
    button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    button_frame.pack(pady=(20,10))

    def on_save():
        dialog.result = "save"
        dialog.destroy()

    def on_discard():
        dialog.result = "discard"
        dialog.destroy()

    save_button = ctk.CTkButton(
        button_frame,
        text="Save",
        width=80,
        font=FONTS['semibold_12'],
        text_color="#13140e",
        fg_color="#a3ab8a",
        hover_color="#858e6e",
        command=on_save
    )
    save_button.pack(side="left", padx=10)

    discard_button = ctk.CTkButton(
        button_frame,
        text="Discard",
        width=80,
        text_color="#13140e",
        fg_color="#E85555",
        hover_color="#D04040",
        font=FONTS['semibold_12'],
        command=on_discard
    )
    discard_button.pack(side="left", padx=10)

    # Set dialog size
    dialog.update_idletasks()
    width = 350
    height = 150
    dialog.minsize(width, height)
    dialog.resizable(False, False)

    dialog.protocol("WM_DELETE_WINDOW", lambda: setattr(dialog, 'result', 'cancel') or dialog.destroy())
    dialog.center_window(width=width, height=height)
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
            popup_to_close.after(0, popup_to_close.destroy)

        # Reset global references if the popup being closed is one of the tracked ones
        global path_popup_window, standalone_popup_window
        if popup_to_close == path_popup_window:
            path_popup_window = None
        elif popup_to_close == standalone_popup_window:
            standalone_popup_window = None

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
        popup_instance.resizable(False, False)
        popup_instance.iconbitmap(APP_ICON)
        popup_instance.protocol("WM_DELETE_WINDOW", on_popup_quit)
    
        content_frame = ctk.CTkFrame(popup_instance, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)  # Label row
        content_frame.rowconfigure(1, weight=0)  # Button frame row
    
        # --- Message label ---
        label = ctk.CTkLabel(
            content_frame, 
            text=message, 
            font=FONTS['semibold_14'],
            wraplength=380, 
            # justify="left" 
        )
        label.grid(row=0, column=0, sticky="nsew", pady=(0, 15)) 
    
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew")
        button_frame.columnconfigure(0, weight=1)  
    
        # --- Set button ---
        set_button = ctk.CTkButton(
            button_frame, 
            text="Set", 
            width=80,
            font=FONTS['semibold_12'],
            text_color="#13140e",
            fg_color="#a3ab8a",
            hover_color="#858e6e",
            command=lambda: _select_and_set_folder_path(popup_instance)
        )
        set_button.grid(row=0, column=0, pady=10) 
    

        popup_instance.update_idletasks()
        
        label_req_w = label.winfo_reqwidth()
        label_req_h = label.winfo_reqheight()
        button_req_h = set_button.winfo_reqheight()
        
        min_width = max(380, label_req_w + 40) 
        min_height = label_req_h + button_req_h + 80

        popup_instance.minsize(min_width, min_height)
        popup_instance.update_idletasks()
        popup_instance.geometry(f"{min_width}x{min_height}") 
        popup_instance.update_idletasks()

        return min_width, min_height 

    if app and app.winfo_exists():
        if path_popup_window and path_popup_window.winfo_exists():
             path_popup_window.after(0, path_popup_window.focus_force)
             return
        
        path_popup_window = ToplevelIco(app, APP_ICON)

        popup_min_width, popup_min_height = setup_popup(path_popup_window, message)
        path_popup_window.update_idletasks() 
        path_popup_window.center_window(width=popup_min_width, height=popup_min_height) 
        path_popup_window.update_idletasks()
        path_popup_window.transient(app)
        path_popup_window.grab_set()
        path_popup_window.lift()
        path_popup_window.focus_force()
        app.wait_window(path_popup_window)

    else: # Main app doesn't exist, handle standalone
        if standalone_popup_window and standalone_popup_window.winfo_exists():
            try:
                standalone_popup_window.after(0, standalone_popup_window.focus_force)
            except Exception as e:
                print(f"Error scheduling focus for standalone popup: {e}")
            return
        if standalone_popup_thread and standalone_popup_thread.is_alive():
            print("Standalone popup thread already running. Preventing new popup.")
            return

        def _standalone_popup_target():
            global standalone_popup_window

            try:
                standalone_popup_window = ctk.CTk()
                initialize_app_fonts() 
                popup_min_width, popup_min_height = setup_popup(standalone_popup_window, message)
                standalone_popup_window.update_idletasks()

                # get Scaling Factor
                scale_factor = 1.0
                if platform.system() == "Windows":
                    try:
                        scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0
                        print(f"Standalone Popup: Detected Windows Scale Factor: {scale_factor}")
                    except Exception as e:
                        print(f"Standalone Popup: Could not get scale factor via ctypes: {e}. Falling back to 1.0.")

                # get screen size
                screen_width = standalone_popup_window.winfo_screenwidth()
                screen_height = standalone_popup_window.winfo_screenheight()

                # Use the dimensions returned by setup_popup
                width = popup_min_width
                height = popup_min_height

                # Apply scaling factor to window width and height for position calculation
                actual_width = int(width * scale_factor)
                actual_height = int(height * scale_factor)

                # Calculate top-left corner (x, y) for window
                x = (screen_width // 2) - (actual_width // 2)
                y = (screen_height // 2) - (actual_height // 2)

                # Set final geometry
                final_geom = f'{width}x{height}+{x}+{y}'
                standalone_popup_window.geometry(final_geom)
                standalone_popup_window.update_idletasks()
                standalone_popup_window.lift()
                standalone_popup_window.focus_force()
                
                print("Starting standalone popup mainloop.")
                standalone_popup_window.mainloop()

            except Exception as e:
                print(f"Error during _standalone_popup_target execution: {e}")
            finally: # Cleanup for this thread
                print("Standalone popup mainloop ended.")
                # Ensure standalone_popup_window is None if this thread exits,
                if standalone_popup_window is not None:
                    standalone_popup_window = None

        print("Starting standalone popup thread.")
        standalone_popup_thread = Thread(target=_standalone_popup_target, daemon=True)
        standalone_popup_thread.start()
# endregion


# region validate input
def validate_input(folder_name, extensions, original_folder=None):
    """Validate folder name and extensions against the current config."""
    current_config = load_config()
    mapping = current_config.get('folder_extensions_mapping', {})

    folder_name_stripped = folder_name.strip()
    if not folder_name_stripped:
        return False, "Folder name cannot be empty."
    
    from config_manager import reserved_names

    invalid_folder_chars_pattern = compile(r'[\\:*?"<>|]') 
    invalid_extension_chars_pattern = compile(r'[\\/:*?"<>|]')

    if invalid_folder_chars_pattern.search(folder_name_stripped):
        return False, f"Folder name '{folder_name_stripped}' contains invalid characters (e.g., \\:*?\"<>|)."
    if folder_name_stripped.upper() in reserved_names:
        return False, f"Folder name '{folder_name_stripped}' is a reserved name."
    if '//' in folder_name_stripped or '\\\\' in folder_name_stripped:
        return False, f"Folder name '{folder_name_stripped}' contains multiple consecutive slashes or backslashes."
    if folder_name_stripped.strip('/') == '': # Catches names like "/" or "///"
        return False, "Folder name cannot be just slashes."
    if folder_name_stripped.startswith('/') or folder_name_stripped.endswith('/'):
        return False, "Folder name cannot start or end with a slash."
    if folder_name_stripped.startswith('\\') or folder_name_stripped.endswith('\\'):
         return False, "Folder name cannot start or end with a backslash."

    if folder_name_stripped == "." or folder_name_stripped == "..":
        return False, f"Folder name cannot be '{folder_name_stripped}' as it's a special directory reference."

    folder_name_lower = folder_name_stripped.lower()
    for existing_folder_key_in_map in mapping: 
        existing_folder_key_lower = existing_folder_key_in_map.lower()

        if original_folder is None: # Adding a new category
            if folder_name_lower == existing_folder_key_lower:
                return False, f"Folder name '{folder_name_stripped}' already exists in the configuration."
        else: # Editing an existing category
            original_folder_name_lower = original_folder.lower() 
            if folder_name_lower == existing_folder_key_lower and existing_folder_key_lower != original_folder_name_lower:
                return False, f"Folder name '{folder_name_stripped}' already exists (used by category '{existing_folder_key_in_map}')."

    # --- Extension validation ---
    processed_extensions_for_check = [] 

    for ext_input in extensions: 
        ext_stripped = ext_input.strip().lstrip('.')
        if not ext_stripped: continue

        if invalid_extension_chars_pattern.search(ext_stripped):
            return False, f"Extension '{ext_stripped}' contains invalid characters (e.g., \\/:*?\"<>|)."
        if ext_stripped.upper() in reserved_names:
            return False, f"Extension '{ext_stripped}' is a reserved name."

        ext_lower = ext_stripped.lower()

        for existing_folder_name_in_map, existing_extensions_in_map in mapping.items():
            existing_folder_name_in_map_lower = existing_folder_name_in_map.lower()
            
            normalized_existing_extensions = existing_extensions_in_map 

            is_adding_new_category = original_folder is None
            is_editing_a_different_category = not is_adding_new_category and \
                                              existing_folder_name_in_map_lower != original_folder.lower()

            if (is_adding_new_category or is_editing_a_different_category) and \
               ext_lower in normalized_existing_extensions:
                 return False, f"Extension '{ext_stripped}' is already assigned to folder '{existing_folder_name_in_map}'."
        
        processed_extensions_for_check.append(ext_stripped)

    if not processed_extensions_for_check:
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
    def __init__(self, master, config_window, folder_name, extensions, delete_icon):
        super().__init__(master)
        self.pack(fill="x", padx=2, pady=0) # expand row horizontally

        self.config_window = config_window
        self.original_folder = folder_name
        self.original_extensions_str = ', '.join(extensions)
        self.delete_icon = delete_icon
        self.is_dirty = False # to track unsaved changes

        label_frame = ctk.CTkFrame(self, corner_radius=10, height=40)
        label_frame.pack_propagate(False)
        label_frame.pack(side="left", fill="x", expand=True, padx=(5,2), pady=5)

        self.folder_entry_var = ctk.StringVar(value=self.original_folder)

        self.folder_entry = ctk.CTkEntry(label_frame, font=FONTS['regular_12'], textvariable=self.folder_entry_var)
        self.folder_entry.pack(expand=True, fill="both", padx=5, pady=5) 

        self.extensions_textbox = ctk.CTkTextbox(self, height=60, font=FONTS['regular_12'])
        self.extensions_textbox.pack(side="left", fill="x", expand=True, padx=(12,0), pady=5)
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
                                         hover_color='#253417', text_color='#94be6b', font=FONTS['regular_9'],
                                         command=self._handle_save_button_click)
        self.save_button.pack_forget()

        self.reset_button = ctk.CTkButton(self.button_frame, text="Reset", width=30, height=25, fg_color="#343638",
                                          hover_color='#461505', text_color='#f06a3f', font=FONTS['regular_9'],
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
        is_valid, error_message = validate_input(new_folder_name, ordered_unique_extensions, original_folder=self.original_folder)
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
        pause_watching()
        initialize_app_fonts() 
        self.title("Configure Folder Sorter")
        self.iconbitmap(APP_ICON)
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self.on_app_quit)

        # --- Load Config Early for Geometry ---
        saved_geometry = config.get("window_geometry")

        # --- Initialize delete_icon ---
        try:
            self.delete_icon = ctk.CTkImage(
                light_image=Image.open(DELETE_PNG),
                dark_image=Image.open(DELETE_PNG),
                size=(10, 10)
            )
        except Exception as e:
            print(f"Error loading delete image: {e}")
            self.delete_icon = None

        # --- Initialize settings_icon ---
        try:
            self.settings_icon = ctk.CTkImage(
                light_image=Image.open(SETTINGS_PNG),
                dark_image=Image.open(SETTINGS_PNG),
                size=(12,13)
            )
        except Exception as e:
            print(f"Error loading settings image: {e}")
            self.settings_icon = None

        # --- Build UI Elements ---
        self._build_path_frame()
        self._build_add_frame()
        self._build_scrollable_frame() 

        # --- Set Initial Geometry & Minimum Size ---
        geometry_applied = False
        if saved_geometry:
            try:
                if isinstance(saved_geometry, str) and 'x' in saved_geometry and '+' in saved_geometry:
                    self.geometry(saved_geometry)
                    print(f"Applied saved geometry: {saved_geometry}")
                    geometry_applied = True
                else:
                    print(f"Warning: Invalid saved geometry format '{saved_geometry}'. Falling back to centering.")
            except Exception as e:
                print(f"Error applying saved geometry '{saved_geometry}': {e}. Falling back to centering.")

        if not geometry_applied:
            print("No valid saved geometry found. Centering window.")
            self._center_window_fallback()

        min_width = 547
        min_height = 334
        self.minsize(min_width, min_height)

        # --- Force update of main window geometry before populating scrollable frame ---
        self.update_idletasks() 

        # --- Setup callbacks for cross-thread gui function calls ---
        file_sorter.set_gui_callbacks(
            self, 
            lambda msg: show_error_dialog(self, msg), 
            self.focus_app 
        )

        # --- Defer initial rendering of scrollable content ---
        self.after_idle(self.render_scrollable_widget) 

        self.lift()
        self.focus_app()

    def _center_window_fallback(self):
        """Centers the window on the screen (used for first launch or errors)."""

        # Default desired size
        default_width = 547
        default_height = 700

        try:
            # --- Set minimum size FIRST ---
            self.minsize(default_width, default_height)

            # --- Apply initial size (position will be set later) ---
            self.geometry(f'{default_width}x{default_height}')
            self.update_idletasks() # Process geometry and minsize changes

            # --- Calculate Position using the INTENDED default size ---
            scale_factor = 1.0
            if platform.system() == "Windows":
                try:
                    # Prioritize ctypes for scaling
                    scale_factor = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100.0
                    # print(f"Fallback Center: Using ctypes scale factor: {scale_factor}") # Optional debug
                except Exception as e_ctypes:
                    print(f"Fallback Center: Error getting scaling via ctypes ({e_ctypes}), trying CTk...")
                    try:
                        # Fallback to CTk ScalingTracker
                        scale_factor = ctk.ScalingTracker.get_window_dpi_scaling(self.winfo_id())
                    except Exception as e_ctk:
                        print(f"Fallback Center: Error getting scaling via CTk ({e_ctk}), using 1.0.")
                        scale_factor = 1.0 # Ultimate fallback
            # print(f"Fallback Center: Final Scale Factor: {scale_factor}") # Debug

            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()

            # Use the DEFAULT size for centering calculation
            actual_width_scaled = int(default_width * scale_factor)
            actual_height_scaled = int(default_height * scale_factor)

            x = max(0, (screen_width // 2) - (actual_width_scaled // 2))
            y = max(0, (screen_height // 2) - (actual_height_scaled // 2))

            # --- Set final geometry using DEFAULT size and calculated position ---
            final_geometry = f'{default_width}x{default_height}+{x}+{y}'
            self.geometry(final_geometry)
            print(f"Centered window geometry: {final_geometry}")

        except Exception as e:
            print(f"Error during fallback centering: {e}")
            # Apply a basic default if centering fails
            try:
                # Use the default size variables here
                self.geometry(f'{default_width}x{default_height}+100+100')
            except Exception as basic_e:
                print(f"Failed to set even basic geometry: {basic_e}")

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
        # --- Try to save geometry FIRST ---
        try:
            # Ensure window still exists and update pending changes
            if self.winfo_exists():
                self.update_idletasks() # Process pending events like resize/move
                current_geometry = self.geometry()
                # Basic check: Avoid saving clearly invalid small sizes if possible
                # (This is a heuristic, might need adjustment)
                try:
                    size_part = current_geometry.split('+')[0]
                    w_str, h_str = size_part.split('x')
                    if int(w_str) > 50 and int(h_str) > 50: # Only save if size seems reasonable
                         save_config(window_geometry=current_geometry)
                         print(f"Saved geometry on quit attempt: {current_geometry}")
                    else:
                         print(f"Skipping save of potentially invalid geometry: {current_geometry}")
                except Exception:
                     print(f"Could not parse geometry to validate size, saving anyway: {current_geometry}")
                     save_config(window_geometry=current_geometry) # Save if parsing fails
            else:
                print("Window already destroyed, cannot save geometry.")
        except Exception as e:
            print(f"Error saving window geometry during quit: {e}")

        # --- Now handle unsaved changes ---
        proceed_with_quit = True # Assume we can quit unless checks fail
        if self.has_unsaved_changes():
            result = show_unsaved_changes_dialog(self)
            if result == "save":
                save_outcome = self.save_all_changes(render_on_success=False)
                if save_outcome is True:
                    proceed_with_quit = True # Save successful, can quit
                elif isinstance(save_outcome, str):
                    show_error_dialog(self, f"Failed to save changes:\n\n{save_outcome}")
                    proceed_with_quit = False # Save failed, don't quit
                elif save_outcome is False:
                    proceed_with_quit = False # User cancelled save, don't quit
            elif result == "discard":
                proceed_with_quit = True # Discarding, can quit
            elif result == "cancel":
                proceed_with_quit = False # User cancelled, don't quit
        else:
            # No unsaved changes
            proceed_with_quit = True

        # --- Perform actual quit if allowed ---
        if proceed_with_quit:
            resume_watching()
            self._perform_quit()
        else:
            print("Quit cancelled.") # User chose not to quit or save failed

    def _perform_quit(self):
        """Actually destroys the window and cleans up references."""
        global app
        print("Performing quit...") # Added print

        # --- Clear References ---
        # References are cleared after geometry is saved in on_app_quit
        if app is self:
            app = None
        if file_sorter.gui_app_instance is self:
            file_sorter.gui_app_instance = None
            file_sorter.show_error_dialog = None
            file_sorter.focus_app = None

        # --- Destroy Window ---
        try:
            if self.winfo_exists():
                self.destroy()
            print("Config GUI closed.")
        except Exception as e:
            print(f"Error during window destruction: {e}")

    def focus_app(self):
        """Brings the window to the front and gives it focus."""
        try:
            if self.winfo_exists():
                self.lift()
                self.focus_force()
                # Optional: De-iconify if minimized (platform-dependent)
                if platform.system() == "Windows":
                    self.wm_state('normal') # Should restore from minimized
                else:
                    self.deiconify() # General Tkinter method
        except Exception as e:
            print(f"Error focusing app window: {e}")


    def _build_path_frame(self):
        """Creates the top frame for folder path selection."""
        path_frame = ctk.CTkFrame(self)
        path_frame.pack(fill="x", padx=10, pady=10)

        path_label = ctk.CTkLabel(path_frame, text="Folder Path:", font=FONTS['semibold_14'])
        path_label.pack(side="left", padx=(10, 8), pady=7)

        path_display_frame = ctk.CTkFrame(
            path_frame,
            fg_color="#232323",
            corner_radius=8,
            width=320,
            height=32
        )
        path_display_frame.pack_propagate(False)
        path_display_frame.pack(side="left", fill="x", expand=True, pady=3)

        self.path_display_label = ctk.CTkLabel(
            path_display_frame,
            text="No path set",
            font=FONTS['regular_11'],
            anchor="w",
            cursor="hand2",
            text_color="#d8dcc7"
        )
        self.path_display_label.pack(side="left", fill="both", expand=True, padx=(6, 2), pady=7)
        self.path_display_label.bind("<Button-1>", self._on_path_click)

        self.path_tooltip = CTkToolTip(
            self.path_display_label,
            message="No Path Set. Click Browse to select.",
            x_offset=-5, y_offset=20, alpha=0.87, font=FONTS['regular_12']
        )

        browse_button = ctk.CTkButton(
            path_frame,
            text="Browse",
            width=12,
            font=FONTS['semibold_12'],
            text_color="#13140e",
            fg_color="#a3ab8a",
            hover_color="#858e6e",
            command=self.select_folder
        )
        browse_button.pack(side="right", padx=(10,8), pady=7)

        self.refresh_path_display(config.get('folder_path', ''))

    def refresh_path_display(self, new_path):
        """Update the path display label and tooltip with a new path."""
        if new_path and path.isdir(new_path):
            display_text = new_path
            tooltip_message = f"Click to open folder: {new_path}"
        elif new_path and not path.isdir(new_path):
            display_text = "Invalid path - click to set"
            tooltip_message = f"Invalid path: {new_path}. Click to browse for folder."
        else:
            display_text = "Click to set folder path"
            tooltip_message = "No path set. Click to browse for folder."
        
        try:
            if hasattr(self, 'path_display_label') and self.path_display_label.winfo_exists():
                self.path_display_label.configure(text=display_text)
            if hasattr(self, 'path_tooltip') and self.path_tooltip:
                self.path_tooltip.configure(message=tooltip_message)
        except Exception as e:
            print(f"Error refreshing path display: {e}")


    def select_folder(self):
        """Open folder selection dialog and update path display."""
        folder_path_selected = ctk.filedialog.askdirectory()
        if folder_path_selected:
            save_config(folder_path=folder_path_selected)
            self.refresh_path_display(folder_path_selected)
            restart_watcher_if_running()

    def _on_path_click(self, event=None):
        current_path = config.get('folder_path')
        if not current_path or not path.isdir(current_path):
            self.select_folder()
            return
        try:
            if platform.system() == "Windows":
                os.startfile(current_path)
            elif platform.system() == "Darwin":
                subprocess.run(['open', current_path], check=True)
            else:
                subprocess.run(['xdg-open', current_path], check=True)
        except Exception as e:
            show_error_dialog(self, f"An error occurred while opening folder:\n{current_path}\n{e}")

    def _build_add_frame(self):
        """Creates the frame for adding new categories."""
        add_frame = ctk.CTkFrame(self)
        add_frame.pack(fill="x", padx=10, pady=(0,13)) 
        add_frame.columnconfigure(1, weight=1)

        new_category_label = ctk.CTkLabel(add_frame, text="New Category Name:", font=FONTS['semibold_13'])
        new_category_label.grid(row=0, column=0, sticky="w", padx=(10, 5), pady=7)
        self.new_category_entry = ctk.CTkEntry(add_frame, height=25, font=FONTS['semibold_12'])
        # sticky="ew" makes the entry fill its grid cell horizontally
        self.new_category_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=7)

        new_extensions_label = ctk.CTkLabel(add_frame, text="Extensions (comma separated):", font=FONTS['semibold_13'])
        new_extensions_label.grid(row=1, column=0, sticky="w", padx=(10, 5), pady=7)
        self.new_extensions_entry = ctk.CTkEntry(add_frame, height=25, font=FONTS['semibold_12'])
        self.new_extensions_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=7)

        add_button = ctk.CTkButton(
            add_frame,
            text="Add",
            width=6,
            font=FONTS['semibold_12'],
            text_color="#13140e",
            fg_color="#a3ab8a",
            hover_color="#858e6e",
            command=self.add_category
        )
        add_button.grid(row=2, column=1, sticky="e", padx=6, pady=(0,7))

    def add_category(self):
        """Adds a new category from the input fields, preserving extension order."""
        folder_name = self.new_category_entry.get().strip()
        extensions_input = self.new_extensions_entry.get().strip()

        # Use the helper function
        ordered_unique_extensions = process_extensions_string(extensions_input)

        # Use ordered_unique_extensions for validation
        is_valid, error_message = validate_input(folder_name, ordered_unique_extensions)
        
        if is_valid is None: return
        if not is_valid:
            show_error_dialog(self, error_message)
            return

        # config should be loaded already
        config['folder_extensions_mapping'][folder_name] = ordered_unique_extensions
        save_config(folder_extensions_mapping=config['folder_extensions_mapping'])

        self.render_scrollable_widget()

        self.new_category_entry.delete(0, ctk.END)
        self.new_extensions_entry.delete(0, ctk.END)
    
    def open_settings_dialog(self):
        """Open the settings dialog window."""
        dialog = ToplevelIco(self, APP_ICON)
        dialog.title("Settings")
        dialog.resizable(False, False)

        # Main content frame with padding
        content_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # --- Settings Groups Frame ---
        settings_frame = ctk.CTkFrame(content_frame, fg_color="#232323", corner_radius=10)
        settings_frame.pack(fill="x", pady=(0, 15), ipady=5)

        # --- Notification Settings Group ---
        notif_section = ctk.CTkFrame(settings_frame, fg_color="transparent")
        notif_section.pack(fill="x", padx=15, pady=(8, 5))
        
        # Header with underline separator
        notif_header_frame = ctk.CTkFrame(notif_section, fg_color="transparent")
        notif_header_frame.pack(fill="x")
        
        notif_header = ctk.CTkLabel(
            notif_header_frame, 
            text="Notifications", 
            font=FONTS['semibold_13'],
            text_color="#a3ab8a"
        )
        notif_header.pack(side="left", anchor="w", pady=(0, 2))
        
        # Separator
        notif_separator = ctk.CTkFrame(notif_section, height=1, fg_color="#3a3a3a")
        notif_separator.pack(fill="x", pady=(0, 6))

        # Setting container (adds visual separation)
        notif_container = ctk.CTkFrame(notif_section, fg_color="#2a2a2a", corner_radius=6)
        notif_container.pack(fill="x", padx=5, pady=(0, 3))
        
        # --- Custom darkmode checkbox style (white tick) ---
        notif_var = ctk.BooleanVar(value=config.get("enable_notifications", True))
        notif_checkbox = ctk.CTkCheckBox(
            notif_container,
            text="Enable notifications after sorting",
            variable=notif_var,
            font=FONTS['regular_12'],
            fg_color="#7a8164",
            border_color="#7a8164", 
            hover_color="#5d634d",
            checkbox_height=22,
            checkbox_width=22,
            text_color="#d8dcc7"
        )
        notif_checkbox.pack(anchor="w", padx=10, pady=(12, 12))

        # --- UI Settings Group ---
        ui_section = ctk.CTkFrame(settings_frame, fg_color="transparent")
        ui_section.pack(fill="x", padx=15, pady=(5, 5))
        
        # Header with underline separator
        ui_header_frame = ctk.CTkFrame(ui_section, fg_color="transparent")
        ui_header_frame.pack(fill="x") 
        
        ui_header = ctk.CTkLabel(
            ui_header_frame, 
            text="User Interface", 
            font=FONTS['semibold_13'],
            text_color="#a3ab8a"
        )
        ui_header.pack(side="left", anchor="w", pady=(0, 2))
        
        # Separator
        ui_separator = ctk.CTkFrame(ui_section, height=1, fg_color="#3a3a3a")
        ui_separator.pack(fill="x", pady=(0, 6))

        # Setting container (adds visual separation)
        ui_container = ctk.CTkFrame(ui_section, fg_color="#2a2a2a", corner_radius=6)
        ui_container.pack(fill="x", padx=5, pady=(0, 3))
        
        # --- Custom darkmode checkbox style (white tick) ---
        confirm_delete_var = ctk.BooleanVar(value=not config.get("dont_show_again", False))
        confirm_delete_checkbox = ctk.CTkCheckBox(
            ui_container,
            text="Confirm before deleting categories",
            variable=confirm_delete_var,
            font=FONTS['regular_12'],
            fg_color="#7a8164",
            border_color="#7a8164", 
            hover_color="#5d634d",
            checkbox_height=22,
            checkbox_width=22,
            text_color="#d8dcc7"
        )
        confirm_delete_checkbox.pack(anchor="w", padx=10, pady=(12, 12))

        # --- Advanced Settings Group ---
        advanced_section = ctk.CTkFrame(settings_frame, fg_color="transparent")
        advanced_section.pack(fill="x", padx=15, pady=(5, 0))
        
        # Header with underline separator
        advanced_header_frame = ctk.CTkFrame(advanced_section, fg_color="transparent")
        advanced_header_frame.pack(fill="x") 
        
        advanced_header = ctk.CTkLabel(
            advanced_header_frame, 
            text="Advanced", 
            font=FONTS['semibold_13'],
            text_color="#a3ab8a"
        )
        advanced_header.pack(side="left", anchor="w", pady=(0, 2))
        
        # Separator
        advanced_separator = ctk.CTkFrame(advanced_section, height=1, fg_color="#3a3a3a")
        advanced_separator.pack(fill="x", pady=(0, 8))

        # Setting container 
        advanced_container = ctk.CTkFrame(advanced_section, fg_color="transparent", corner_radius=6)
        advanced_container.pack(fill="x", padx=5)
        
        # Config folder button
        def open_config_folder_action():
            from config_manager import open_config_folder
            success = open_config_folder()
            if success:
                print("Config folder opened successfully")
            else:
                print("Failed to open config folder")
        
        config_folder_btn = ctk.CTkButton(
            advanced_container,
            text="Open Config Folder",
            width=140,
            height=28,
            font=FONTS['regular_12'],
            fg_color="#343638",
            hover_color="#404347",
            text_color="#d8dcc7",
            command=open_config_folder_action
        )
        config_folder_btn.pack(anchor="w")

        # --- Button Frame ---
        button_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(0, 5))
        button_frame.columnconfigure(0, weight=1) 
        
        def on_save():
            # Save notification setting
            config["enable_notifications"] = notif_var.get()
            
            # Save confirm delete setting
            config["dont_show_again"] = not confirm_delete_var.get()
            
            # Save all config changes
            save_config()
            dialog.destroy()

        save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            width=80,
            font=FONTS['semibold_12'],
            text_color="#13140e",
            fg_color="#a3ab8a",
            hover_color="#858e6e",
            command=on_save
        )
        save_btn.grid(row=0, column=1, padx=(10, 0), pady=(10, 0))
        
        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=80,
            font=FONTS['semibold_12'],
            fg_color="#343638",
            hover_color="#2d2a2e",
            command=dialog.destroy
        )
        cancel_btn.grid(row=0, column=0, padx=(0, 10), pady=(10, 0), sticky="e")

        # Set dialog size based on content
        dialog.update_idletasks()
        min_width = 400
        min_height = dialog.winfo_reqheight()
        dialog.minsize(min_width, min_height)
        
        # Position and show dialog
        dialog.center_window()
        dialog.transient(self)
        dialog.grab_set()
        dialog.focus_force()
        self.wait_window(dialog)

    def _build_scrollable_frame(self):
        """Creates the main scrollable frame."""
        self.scrollable_frame = ctk.CTkScrollableFrame(self)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))
        scrollbar = self.scrollable_frame._scrollbar
        scrollbar.configure(width=6)

    def render_scrollable_widget(self):
        """Renders the list of existing categories using CategoryRow."""
        # Destroy existing widgets first
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Build Header using the same structure as CategoryRow
        header_frame = ctk.CTkFrame(self.scrollable_frame)
        header_frame.pack(fill="x", padx=2, pady=5)

        # --- Folder Column ---
        folders_frame = ctk.CTkFrame(
            header_frame,
            corner_radius=10,
            height=40,
            fg_color="#2b2b2b"
        )
        folders_frame.pack_propagate(False)
        folders_frame.pack(side="left", fill="x", expand=True, padx=(5,2), pady=5)
        # put the label in its own bubble
        folder_label_frame = ctk.CTkFrame(
            folders_frame,
            corner_radius=8,
            fg_color="#242424"
        )
        folder_label_frame.pack(anchor="center", pady=5, padx=8)

        folders_label = ctk.CTkLabel(
            folder_label_frame,
            text="Folders",
            font=FONTS['semibold_12']
        )
        folders_label.pack(padx=8)
        CTkToolTip(
            folders_label,
            message=(
                "Folder name: The category for sorted files.\n"
                "Example: 'Pictures', 'PDFs', 'Work Documents'\n"
                "Use slashes to create subfolders, 'MS/docx' will create 'docx' inside 'MS'."
            ),
            x_offset=0, y_offset=20, alpha=0.92, font=FONTS['regular_11']
        )

        # --- Extensions Column ---
        extensions_frame = ctk.CTkFrame(
            header_frame,
            corner_radius=10,
            height=40,
            fg_color="#2b2b2b"
        )
        extensions_frame.pack_propagate(False)
        extensions_frame.pack(side="left", fill="x", expand=True, padx=(12,0), pady=5)
        # put the label in its own bubble
        ext_label_frame = ctk.CTkFrame(
            extensions_frame,
            corner_radius=8,
            fg_color="#242424"
        )
        ext_label_frame.pack(anchor="center", pady=5, padx=8)

        extensions_label = ctk.CTkLabel(
            ext_label_frame,
            text="Extensions",
            font=FONTS['semibold_12']
        )
        extensions_label.pack(padx=8)

        CTkToolTip(
            extensions_label,
            message=(
                "Extensions: Comma-separated list, no dots.\n"
                "Example: jpg, png, pdf, docx\n"
                "Spaces are ignored. Use only valid file extensions."
            ),
            x_offset=0, y_offset=20, alpha=0.92, font=FONTS['regular_11']
        )


        # --- Settings Button Column ---
        button_frame = ctk.CTkFrame(
            header_frame,
            width=90,
            height=40,
            fg_color="transparent"
        )
        button_frame.pack_propagate(False)
        button_frame.pack(side="left", padx=(7,0), pady=5)

        settings_button = ctk.CTkButton(
            button_frame,
            width=25, height=25,
            font=FONTS['semibold_12'],
            fg_color="#242424",
            hover_color="#343638",
            image=self.settings_icon,
            text="",
            command=self.open_settings_dialog
        )
        settings_button.place(relx=0.5, rely=0.5, anchor="center")

        # config should be loaded already
        sorted_folder_extensions = sorted(config['folder_extensions_mapping'].items(), key=lambda item: item[0].lower())

        # Build Rows
        for folder, extensions in sorted_folder_extensions:
            CategoryRow(
                master=self.scrollable_frame,
                config_window=self,
                folder_name=folder,
                extensions=extensions,
                delete_icon=self.delete_icon
            )
        
        self.scrollable_frame.update_idletasks()
# endregion

# region run gui
def launch_config_gui():
    """Launches the main configuration GUI window."""
    global app, standalone_popup_window, standalone_popup_thread

    if app and app.winfo_exists():
        print("Config window already open. Focusing.")
        app.focus_app()
        return app

    # If standalone path prompt popup is active or its thread is running, ensure it's closed and thread terminated
    popup_was_active = False
    if standalone_popup_window is not None:
        popup_was_active = True
        print("Standalone popup window object exists. Attempting to close.")
        _destroy_standalone_popup() # standalone_popup_window to None

    if standalone_popup_thread is not None and standalone_popup_thread.is_alive():
        popup_was_active = True
        print("Standalone popup thread is alive. Waiting for it to close...")
        standalone_popup_thread.join(timeout=3.0)
        if standalone_popup_thread.is_alive():
            print("Warning: Standalone popup thread did not close in time. Problems may occur.")
        else:
            print("Standalone popup thread successfully closed.")
    
    standalone_popup_thread = None

    if popup_was_active:
        print("Proceeding to launch config window after popup closure attempt.")

    print("Launching new config window.")
    config_window = ConfigWindow()
    app = config_window
    
    try:
        config_window.mainloop()
    finally:
        # ensure 'app' is cleared if the mainloop exits unexpectedly 
        if app is config_window and (not hasattr(config_window, '_w') or not config_window.winfo_exists()):
            app = None
            print("ConfigWindow mainloop exited, global 'app' reference cleared in launch_config_gui.")

    return config_window
# endregion