#!/usr/bin/env python
"""
Build script for Independent Design Checker (IDC)
Creates executables using PyInstaller

IMPORTANT: Before building, make sure you have:
1. Created a .env file with your KIMI_API_KEY or GROK_API_KEY
2. Installed all requirements: pip install -r requirements.txt
3. For OCR version: pip install paddleocr paddlepaddle
"""

import PyInstaller.__main__
import os
import shutil
import sys
import argparse

def clean_build_dirs():
    """Clean previous build directories"""
    dirs_to_clean = ['./dist', './build', './spec_files']
    for d in dirs_to_clean:
        if os.path.exists(d):
            print(f"Cleaning {d}...")
            shutil.rmtree(d)
    os.makedirs('./spec_files', exist_ok=True)

def build_standard_versions():
    """Build standard CLI and GUI versions (no OCR)"""
    
    # CLI version
    cli_args = [
        'main.py',
        '--name=IDC_CLI',
        '--onefile',
        '--console',
        '--add-data=config.py;.',
        '--add-data=.env;.',
        '--hidden-import=requests',
        '--hidden-import=fitz',
        '--hidden-import=PyMuPDF',
        '--hidden-import=dotenv',
        '--distpath=./dist',
        '--workpath=./build',
        '--specpath=./spec_files',
        '--clean',
    ]
    
    # GUI version
    gui_args = [
        'gui.py',
        '--name=IDC_GUI',
        '--onefile',
        '--windowed',
        '--add-data=config.py;.',
        '--add-data=.env;.',
        '--hidden-import=requests',
        '--hidden-import=fitz',
        '--hidden-import=PyMuPDF',
        '--hidden-import=tkinter',
        '--hidden-import=dotenv',
        '--distpath=./dist',
        '--workpath=./build',
        '--specpath=./spec_files',
        '--clean',
    ]
    
    print("\n" + "="*60)
    print("Building Standard CLI version...")
    print("="*60)
    PyInstaller.__main__.run(cli_args)
    
    print("\n" + "="*60)
    print("Building Standard GUI version...")
    print("="*60)
    PyInstaller.__main__.run(gui_args)

def build_ocr_versions():
    """Build OCR-enabled CLI and GUI versions"""
    
    # OCR CLI version
    ocr_cli_args = [
        'main_ocr.py',
        '--name=IDC_CLI_OCR',
        '--onefile',
        '--console',
        '--add-data=config.py;.',
        '--add-data=.env;.',
        '--hidden-import=requests',
        '--hidden-import=fitz',
        '--hidden-import=PyMuPDF',
        '--hidden-import=dotenv',
        '--hidden-import=paddle',
        '--hidden-import=paddleocr',
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=numpy',
        '--collect-all=paddleocr',
        '--collect-all=paddle',
        '--distpath=./dist',
        '--workpath=./build',
        '--specpath=./spec_files',
        '--clean',
    ]
    
    # OCR GUI version
    ocr_gui_args = [
        'gui_ocr.py',
        '--name=IDC_GUI_OCR',
        '--onefile',
        '--windowed',
        '--add-data=config.py;.',
        '--add-data=.env;.',
        '--hidden-import=requests',
        '--hidden-import=fitz',
        '--hidden-import=PyMuPDF',
        '--hidden-import=tkinter',
        '--hidden-import=dotenv',
        '--hidden-import=paddle',
        '--hidden-import=paddleocr',
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=numpy',
        '--collect-all=paddleocr',
        '--collect-all=paddle',
        '--distpath=./dist',
        '--workpath=./build',
        '--specpath=./spec_files',
        '--clean',
    ]
    
    print("\n" + "="*60)
    print("Building OCR CLI version...")
    print("="*60)
    PyInstaller.__main__.run(ocr_cli_args)
    
    print("\n" + "="*60)
    print("Building OCR GUI version...")
    print("="*60)
    PyInstaller.__main__.run(ocr_gui_args)

def print_usage():
    """Print usage information"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║           IDC Build Script - Usage Guide                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  BUILD OPTIONS:                                              ║
║  ─────────────                                               ║
║  python build_exe.py --all         Build all versions        ║
║  python build_exe.py --standard    Build standard only       ║
║  python build_exe.py --ocr         Build OCR versions only   ║
║                                                              ║
║  OUTPUT FILES (in ./dist folder):                            ║
║  ─────────────                                               ║
║  Standard Versions:                                          ║
║    • IDC_CLI.exe       - Command line interface              ║
║    • IDC_GUI.exe       - Graphical interface                 ║
║                                                              ║
║  OCR-Enabled Versions:                                       ║
║    • IDC_CLI_OCR.exe   - CLI with OCR support                ║
║    • IDC_GUI_OCR.exe   - GUI with OCR support                ║
║                                                              ║
║  WHEN TO USE OCR VERSIONS:                                   ║
║  ─────────────────────────                                   ║
║  • Scanned PDF documents                                     ║
║  • Images embedded in PDFs                                   ║
║  • Documents with no selectable text                         ║
║                                                              ║
║  REQUIREMENTS:                                               ║
║  ────────────                                                ║
║  Standard:  pip install -r requirements.txt                  ║
║  OCR:       pip install paddleocr paddlepaddle             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")

def main():
    parser = argparse.ArgumentParser(
        description='Build IDC executables',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--all', action='store_true', 
                       help='Build all versions (standard + OCR)')
    parser.add_argument('--standard', action='store_true',
                       help='Build standard versions only')
    parser.add_argument('--ocr', action='store_true',
                       help='Build OCR versions only')
    parser.add_argument('--clean', action='store_true',
                       help='Clean build directories only')
    
    args = parser.parse_args()
    
    # If no arguments, show help
    if not any([args.all, args.standard, args.ocr, args.clean]):
        print_usage()
        parser.print_help()
        return
    
    # Clean only
    if args.clean:
        clean_build_dirs()
        print("Build directories cleaned.")
        return
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("\nWARNING: .env file not found!")
        print("Creating .env file template...")
        with open('.env', 'w') as f:
            f.write("# Choose API Provider: 'grok' or 'kimi'\n")
            f.write("API_PROVIDER=grok\n\n")
            f.write("# Grok API (x.ai)\n")
            f.write("GROK_API_KEY=your_grok_api_key_here\n")
            f.write("GROK_API_URL=https://api.x.ai/v1/chat/completions\n\n")
            f.write("# KIMI API (Moonshot)\n")
            f.write("KIMI_API_KEY=your_kimi_api_key_here\n")
            f.write("KIMI_API_URL=https://api.moonshot.cn/v1/chat/completions\n\n")
            f.write("# Default model\n")
            f.write("MODEL_NAME=grok-2-1212\n")
        print("Please edit .env file and add your API key.")
        response = input("\nDo you want to continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Clean and build
    clean_build_dirs()
    
    print("\n" + "="*60)
    print("Building Independent Design Checker Executables")
    print("="*60)
    
    if args.all or args.standard:
        build_standard_versions()
    
    if args.all or args.ocr:
        try:
            import paddleocr
            build_ocr_versions()
        except ImportError:
            print("\nWARNING: PaddleOCR not installed. Skipping OCR builds.")
            print("To build OCR versions, install: pip install paddleocr paddlepaddle")
    
    print("\n" + "="*60)
    print("Build Completed!")
    print("="*60)
    print("\nExecutables are located in the 'dist' folder:")
    
    if args.all or args.standard:
        print("\n  [Standard Versions]")
        print("    • IDC_CLI.exe       - Command-line interface")
        print("    • IDC_GUI.exe       - Graphical user interface")
    
    if args.all or args.ocr:
        print("\n  [OCR-Enabled Versions]")
        print("    • IDC_CLI_OCR.exe   - CLI with OCR support")
        print("    • IDC_GUI_OCR.exe   - GUI with OCR support")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    main()
