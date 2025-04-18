# Folder Sorter

A Windows system tray app to automatically sort files into categorized subfolders based on extensions. Includes a GUI for configuration.

**Note:** Currently Windows only due to `win11toast` notifications. Support for macOS and Linux soon.

<div align="center">
  <a href="https://github.com/user-attachments/assets/afad11f3-0050-444c-8eb7-4bf614db6e1b"><img src="https://github.com/user-attachments/assets/afad11f3-0050-444c-8eb7-4bf614db6e1b" alt="Folder-Sorter-demo" border="0" width="549"></a>
</div>

<div align="center">
  <a href="https://github.com/user-attachments/assets/248fff3b-3f66-408d-bad9-1c8b8a89fc76"><img src="https://github.com/user-attachments/assets/248fff3b-3f66-408d-bad9-1c8b8a89fc76" border="0" height="118"></a>
  &nbsp;&nbsp;&nbsp;
  <a href="https://github.com/user-attachments/assets/6fc29ed1-7d09-46b4-9c7a-132d0e0c1c3d"><img src="https://github.com/user-attachments/assets/6fc29ed1-7d09-46b4-9c7a-132d0e0c1c3d" alt="Tray Menu Options" border="0" height="127"></a>
</div>

## Features

*   **System Tray App:** Runs persistently with menu options including sort.
*   **Configuration GUI:** Set target folder & define category/extension rules.
*   **Duplicate Handling:** Avoids overwrites by renaming incoming files if names clash.
*   **Persistent Settings:** Saves configuration to `config.json`.
*   **Windows Notifications:** Notifies upon sort completion with a button to open that folder.

## Installation

1.  **Prerequisites:** Windows, Python 3.x.
2.  **Get Code (Optional):**
    ```bash
    git clone https://github.com/qs-1/Folder-Sorter.git
    cd Folder-Sorter
    ```
3.  **Setup Environment (Recommended):**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    pip install -r requirements.txt
    ```

## Usage

1.  **Run:** `python main.py`
2.  **Configure:** Right-click tray icon -> "Configure".
    *   Set target folder via "Browse".
    *   Add Folder names and comma-separated extensions (e.g., `Documents` | `pdf,docx,txt`).
3.  **Sort:** Right-click tray icon -> "Sort Folder".
4.  **Quit:** Right-click tray icon -> "Quit".
