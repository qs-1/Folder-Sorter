# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

# Get the current directory
current_dir = Path.cwd()

# Define data files to include (icons and fonts)
data_files = [
    (str(current_dir / 'icons'), 'icons'),
    (str(current_dir / 'fonts'), 'fonts'),
]

# Hidden imports for all necessary dependencies
hidden_imports = [
    'customtkinter',
    'pystray',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'CTkToolTip',
    'win11toast',
    'watchdog',
    'watchdog.observers',
    'tkinter',
    'tkinter.filedialog',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=data_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FolderSorter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(current_dir / 'icons' / 'purp-sort.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FolderSorter',
)