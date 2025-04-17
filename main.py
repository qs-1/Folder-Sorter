"""

Folder Sorter - an application to sort files into categorized folders

This module is the entry point for the application.
It initializes the tray icon and manages the app.

"""

import sys
from os import path

# Make sure imports work even if running from a different directory
current_dir = path.dirname(path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from tray_handler import start_tray_thread

def main():
    """Main function to start the application"""
    # Start the tray icon in a separate thread
    tray_thread = start_tray_thread()
    
    # Keep the main thread alive until the tray thread exits
    try:
        tray_thread.join()
    except KeyboardInterrupt:
        print("Application stopped by user")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())