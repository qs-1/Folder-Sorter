# Folder Sorter

A Python application with a graphical user interface (GUI) to automatically sort files in a specified folder into subfolders based on their extensions. The application runs persistently in the system tray for easy access.

## Features

*   **GUI Configuration:** Configure sorting rules using an interface built with CustomTkinter.
    *   Select the target folder to sort.
    *   Add, edit, and delete sorting categories (subfolder names and associated extensions).
    *   Input validation prevents invalid characters, reserved names, and duplicate entries.
*   **System Tray Integration:** Runs minimized in the system tray using `pystray`.
    *   Quick access to sort the target folder.
    *   Open the configuration window.
    *   Quit the application.
*   **Automatic File Sorting:** Moves files from the target folder into configured subfolders based on their file extensions.
*   **Flexible Folder Naming:** Supports subfolders (e.g., `Images/Screenshots`).
*   **Duplicate Handling:**
    *   **Folder Name Conflicts:** If a configured subfolder name already exists in the target directory, it prompts the user to either use the existing folder or automatically rename the new one (e.g., `Documents` -> `Documents_1`).
    *   **File Name Conflicts:** If a file being moved already exists in the destination subfolder, it automatically renames the moved file (e.g., `report.pdf` -> `report_1.pdf`).
*   **Persistent Configuration:** Saves the target folder path and sorting rules to a `config.json`. Includes default rules if no config file is found.
*   **Notifications:** Displays a Windows toast notification via `win11toast` upon successful sorting, with a button to open the sorted folder.


## Installation & Usage

1.  **Prerequisites:**
    *   Python 3.x
    *   Install required libraries using the provided `requirements.txt` file:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Run the application:**
    ```bash
    python main.py
    ```
3.  **Configuration:**
    *   Right-click the Folder Sorter icon in the system tray and select "Configure".
    *   Use the "Browse" button to select the main folder you want to sort.
    *   Add new categories by entering a folder name (e.g., "Documents", "Images/Vacation") and comma-separated extensions (e.g., "pdf, docx", "jpg, png").
    *   Edit or delete existing categories directly in the list. Changes require clicking "Save".
4.  **Sorting:**
    *   Right-click the tray icon and select "Sort Folder".
    *   Files in the configured target folder will be moved according to the rules.
