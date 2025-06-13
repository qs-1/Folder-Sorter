# Folder Sorter

A Windows system tray app to automatically sort files into categorized subfolders based on extensions. Includes a GUI for configuration.

<p align="center">
  <a href="https://github.com/user-attachments/assets/b0e2564a-45c0-41bf-9d9c-e563e1b83d3d">
    <img src="https://github.com/user-attachments/assets/b0e2564a-45c0-41bf-9d9c-e563e1b83d3d" alt="Folder-Sorter-demo" style="max-width:100%; height:auto;">
  </a>
</p>

<p align="center">
  <a href="https://github.com/user-attachments/assets/e930ec31-937b-462e-969d-2fbc21c58e2d">
    <img src="https://github.com/user-attachments/assets/e930ec31-937b-462e-969d-2fbc21c58e2d" alt="tray_icon" style="max-width:45%; height:auto;">
  </a>
  &nbsp;
  <a href="https://github.com/user-attachments/assets/db9b411d-144b-46de-9add-55586eaaecf8">
    <img src="https://github.com/user-attachments/assets/db9b411d-144b-46de-9add-55586eaaecf8" alt="tray_options" style="max-width:45%; height:auto;">
  </a>
</p>


> **⚠️ Disclaimer:** This app directly modifies your file system by moving files based on your configuration. Incorrect configuration or unintended use could lead to permanent changes in your directory structure. **Please ensure your configuration is correct before sorting.**
> 
## Features

* **System Tray Integration:** Runs in the background with menu options for sorting
* **Configuration GUI:** Set target folders and define custom category/extension mapping rules
* **Duplicate Handling:** Automatically renames files to prevent overwrites when name conflicts occur
* **Persistent Settings:** Automatically saves settings to `%LOCALAPPDATA%\FolderSorter\config.json`
* **Windows Notifications:** Shows completion notifications with quick access to open the sorted folder


## Installation

1. Go to the [Releases Page](https://github.com/qs-1/Folder-Sorter/releases)
2. Download & run `FolderSorter.exe`
3. Look for the folder icon in your system tray. Right-click it to configure and sort


## For Developing

### Prerequisites
* Python 3.x

### Setup

1. **Get the Code:**
  ```bash
  git clone https://github.com/qs-1/Folder-Sorter.git
  cd Folder-Sorter
  ```
  
  Alternatively, download the ZIP of the current repo from [here](https://github.com/qs-1/Folder-Sorter/archive/refs/heads/main.zip), extract it, and open the folder.

<br>

2. **Install Dependencies:**
  
  **Recommended approach (using virtual environment):**
  ```bash
  python -m venv venv
  # On Windows
  .\venv\Scripts\activate
  # On macOS/Linux
  # source venv/bin/activate
  pip install -r requirements.txt
  ```
  
  **Alternative (global installation):**
  ```bash
  pip install -r requirements.txt
  ```

### Usage
1. Run `python main.py`
2. Look for the folder icon in your system tray. Right-click it to configure and sort

## Contributing
Contributions, issues, and feature requests are welcome! Feel free create an [issue](https://github.com/qs-1/Folder-Sorter/issues)

## License
This project is licensed under the [MIT License](LICENSE)
