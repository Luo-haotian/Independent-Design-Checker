"""
Script to rebuild the IDC GUI executable with PyInstaller
"""

import subprocess
import os
import sys
from pathlib import Path

def rebuild_gui():
    """Rebuild the GUI executable"""
    print("Rebuilding IDC GUI executable...")
    
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Create spec file for PyInstaller
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.py', '.'),
        ('main.py', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='IDC_GUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
"""
    
    # Write the spec file
    spec_file = project_dir / "IDC_GUI_fixed.spec"
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"Created spec file: {spec_file}")
    
    # Run PyInstaller
    try:
        cmd = [sys.executable, '-m', 'PyInstaller', str(spec_file)]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("PyInstaller executed successfully!")
        print(result.stdout)
        
        # Find the executable
        dist_dir = project_dir / "dist"
        exe_file = dist_dir / "IDC_GUI" / "IDC_GUI.exe"
        
        if exe_file.exists():
            print(f"New executable created: {exe_file}")
            print("Rebuild completed successfully!")
        else:
            print("Warning: Executable not found in expected location")
            
    except subprocess.CalledProcessError as e:
        print(f"Error running PyInstaller: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
    except FileNotFoundError:
        print("Error: PyInstaller not found. Please install it with: pip install pyinstaller")

if __name__ == "__main__":
    rebuild_gui()