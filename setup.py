"""
Setup script for Independent Design Checker (IDC)
Creates an executable for the structural design verification tool
"""

from setuptools import setup
import sys

# Check if py2exe or PyInstaller is available
try:
    import pyinstaller
    USE_PYINSTALLER = True
except ImportError:
    try:
        import py2exe
        USE_PYINSTALLER = False
    except ImportError:
        print("Neither PyInstaller nor py2exe found. Installing PyInstaller...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        USE_PYINSTALLER = True

if USE_PYINSTALLER:
    # Create a build script for PyInstaller
    build_script = '''
#!/usr/bin/env python
import PyInstaller.__main__
import sys
import os

# Get the directory containing this script
script_dir = os.path.dirname(os.path.abspath(__file__))
main_py = os.path.join(script_dir, 'main.py')

# PyInstaller arguments
args = [
    main_py,
    '--name=IDC_Structural_Checker',
    '--onefile',
    '--windowed',
    '--add-data=config.py;.',
    '--hidden-import=requests',
    '--hidden-import=fitz',
    '--hidden-import=PyMuPDF',
    '--distpath=./dist',
    '--workpath=./build',
    '--specpath=./spec_files',
]

PyInstaller.__main__.run(args)
'''
    
    with open('build_exe.py', 'w') as f:
        f.write(build_script)
    
    print("Created build script: build_exe.py")
    print("To build the executable, run: python build_exe.py")

else:
    # Setup for py2exe
    setup(
        name="IDC_Structural_Checker",
        version="1.0",
        description="Independent Design Checker for Structural Submissions",
        console=[{"script": "main.py"}],
        options={
            "py2exe": {
                "includes": ["requests", "fitz", "fitz._main"],
                "bundle_files": 1,
                "compressed": True
            }
        },
        zipfile=None,
    )