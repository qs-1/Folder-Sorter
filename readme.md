# Folder Sorter

A Windows system tray app that automatically monitors a folder and sorts new files into categorized subfolders in real-time along with support for manual sorting.

<p align="center">
  <a href="https://github.com/user-attachments/assets/f4aa473d-79ba-4e57-a12e-0e0818b7a26c">
    <img src="https://github.com/user-attachments/assets/f4aa473d-79ba-4e57-a12e-0e0818b7a26c" alt="Folder-Sorter-demo" style="max-width:100%; height:auto;">
  </a>
</p>
<p align = "center">
  <a href="https://github.com/user-attachments/assets/be9cc253-208e-459a-b41e-2a4a2cd87f51">
    <img src="https://github.com/user-attachments/assets/be9cc253-208e-459a-b41e-2a4a2cd87f51" alt="tray_options" style="max-width:45%; height:auto;">
  </a>
</p>


## Features

* **Automatic Realtime Sorting:** Enable "Auto-Sort" to have the app run in the background to automatically sort new files the moment as they appear in your target folder
* **Undo Sorts:**  Reverse the most recent sort(s) (whether manual or automatic, though you need to disable auto-sorting to undo automatic sorts) 
* **System Tray Integration:** Runs in the system tray for convenience
* **Configuration GUI:** For setting your target folder and define custom folder extension mapping rules
* **Duplicate Handling:** Renames files (like `file_1.txt`) to prevent ever overwriting your existing files
* **Persistent Settings:** Your folder path, rules, and preferences are automatically saved to `%LOCALAPPDATA%\FolderSorter\config.json`


## Installation

1. Go to the [Releases Page](https://github.com/qs-1/Folder-Sorter/releases)
2. Download & run `FolderSorter.exe`
3. Look for the folder icon in your system tray. 


## For Development

**Prerequisites:**

  * Python 3.x
  * Git

**Setup:**

1.  **Clone the repo and navigate into it:**

    ```bash
    git clone https://github.com/qs-1/Folder-Sorter.git
    cd Folder-Sorter
    ```

2.  **Create a virtual environment and install dependencies:**

    ```bash
    # Create and activate the environment
    python -m venv venv
    .\venv\Scripts\activate  # On Windows
    # source venv/bin/activate  # On macOS/Linux

    # Install the required packages
    pip install -r requirements.txt
    ```

3.  **Run the application:**

    ```bash
    python main.py
    ```

    After running, the Folder Sorter icon will appear in your system tray.

## Contributing

Contributions, issues, and feature requests are welcome, feel free create an [issue](https://github.com/qs-1/Folder-Sorter/issues).

## License

This project is licensed under the [MIT License](https://github.com/qs-1/Folder-Sorter/blob/main/LICENSE).
