# Folder Sorter

A Python application with a persistent system tray GUI to automatically sort files in a folder based on their extensions.


## Features

*   **GUI Configuration:** Set the target folder and define sorting rules 
*   **System Tray Integration:** Runs minimized, with options to sort, configure and quit
*   **Sorting:** Moves files into configured subfolders based on extensions. Supports nested subfolder definitions (e.g., `Images/Screenshots`)
*   **Conflict Handling:** prompts the user about existing folder names and automatically renames files being moved to avoid overwriting duplicates in the destination folder.
*   **Persistent Settings:** Saves configuration (target folder, sorting rules) to a json file
*   **Notifications:** Provides Windows toast notifications, with a button to open the sorted folder

## Installation

1.  **Prerequisites:** Ensure Python 3.x is installed.
2.  **Clone the Repository (Optional):**
    ```bash
    git clone https://github.com/qs-1/Folder-Sorter.git
    cd Folder-Sorter
    ```
3.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Run the Application:**
    ```bash
    python main.py
    ```
2.  **System Tray Icon:** The application icon will appear in your system tray.
3.  **Initial Configuration:**
    *   Right-click the tray icon and select "Configure".
    *   In the configuration window:
        *   Click "Browse" to select the main folder you want to sort.
        *   Use the "New Category Name" and "Extensions" fields to define your sorting rules (e.g., Folder: `Documents`, Extensions: `pdf, docx, txt`). Click "Add".
        *   Or use the provided default configuration to sort files into common categories like `Images`, `Videos`, `Documents`.
4.  **Sort Files:**
    *   Right-click the tray icon and select "Sort Folder".
    *   Files in your selected target folder will be moved into the subfolders according to the rules you defined.
5.  **Quit:** Right-click the tray icon and select "Quit" to close the application.

## Screenshots

<div align="center">
  <a href="https://ibb.co/zTTbFYQB"><img src="https://i.ibb.co/hJJHcjL4/Folder-Sorter-demo.png" alt="Folder-Sorter-demo" border="0" width="549"></a>
  
</div>

<div align="center">
  <a href="https://imgbb.com/"><img src="https://i.ibb.co/ksSNnf80/Tray.png" alt="Tray Icon" border="0" height="118"></a>
  &nbsp;&nbsp;&nbsp; <!-- Optional: Add some space between images -->
  <a href="https://imgbb.com/"><img src="https://i.ibb.co/FLSnshNQ/Tray-options.png" alt="Tray Menu Options" border="0" height="127"></a>
</div>
