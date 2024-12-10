# main.spec
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import shutil
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Determine base path from sys.argv[0]
base_path = os.path.abspath(os.path.dirname(sys.argv[0]))

# Adjust paths as needed. Here we assume:
# - .env is one level above the current directory
#   If it's in the same directory as run_with_webview.py, change parent_dir to base_path
parent_dir = os.path.abspath(os.path.join(base_path, ".."))
env_file = os.path.join(parent_dir, ".env")

app_file = os.path.join(base_path, "app.py")
run_with_webview_file = os.path.join(base_path, "run_with_webview.py")

datas = []
binaries = []
hiddenimports = []

# Include the `.env` file if it exists
if os.path.exists(env_file):
    datas.append((env_file, '.'))
else:
    print(f"Warning: .env file not found at {env_file}")

# Include app.py and run_with_webview.py
if os.path.exists(app_file):
    datas.append((app_file, "."))
else:
    raise FileNotFoundError(f"{app_file} not found.")

if os.path.exists(run_with_webview_file):
    datas.append((run_with_webview_file, "."))
else:
    raise FileNotFoundError(f"{run_with_webview_file} not found.")

# Include driver installers if they exist
drivers_dir = os.path.join(base_path, "drivers")
if os.path.exists(drivers_dir):
    for driver in os.listdir(drivers_dir):
        driver_path = os.path.join(drivers_dir, driver)
        if os.path.isfile(driver_path):
            datas.append((driver_path, "drivers"))
else:
    print(f"Warning: Drivers directory not found at {drivers_dir}")

# Attempt to include the streamlit executable if found
streamlit_path = shutil.which("streamlit")
if streamlit_path:
    binaries.append((streamlit_path, "streamlit"))
else:
    print("Warning: Streamlit executable not found in the environment. Make sure streamlit is installed.")

# You can optionally add hiddenimports if needed:
# hiddenimports += collect_all('streamlit')[2]
# hiddenimports += collect_all('webview')[2]
# etc.
# For now, let's rely on PyInstaller's auto-detection as much as possible.

a = Analysis(
    [run_with_webview_file],
    pathex=[base_path],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ChatbotApp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True  # set to True if you need a console for debugging
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="ChatbotApp"
)
