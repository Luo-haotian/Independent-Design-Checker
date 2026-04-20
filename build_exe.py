#!/usr/bin/env python
"""Build IDC executables with PyInstaller."""

import argparse
import os
import shutil

import PyInstaller.__main__


DIST_DIR = "./dist"
BUILD_DIR = "./build"
SPEC_DIR = "./spec_files"


def clean_build_dirs():
    """Remove previous build output."""
    for path in [DIST_DIR, BUILD_DIR, SPEC_DIR]:
        if os.path.exists(path):
            print(f"Cleaning {path}...")
            shutil.rmtree(path)
    os.makedirs(SPEC_DIR, exist_ok=True)


def copy_runtime_files():
    """Copy user-facing runtime templates into dist."""
    os.makedirs(DIST_DIR, exist_ok=True)
    if os.path.exists(".env.example"):
        shutil.copy2(".env.example", os.path.join(DIST_DIR, ".env.example"))


def build_standard_versions():
    """Build the standard CLI and GUI executables."""
    common_args = [
        "--add-data=config.py;.",
        "--add-data=.env.example;.",
        "--hidden-import=requests",
        "--hidden-import=fitz",
        "--hidden-import=PyMuPDF",
        "--distpath=./dist",
        "--workpath=./build",
        "--specpath=./spec_files",
        "--clean",
    ]

    cli_args = [
        "main.py",
        "--name=IDC_CLI",
        "--onefile",
        "--console",
        *common_args,
    ]
    gui_args = [
        "gui.py",
        "--name=IDC_GUI",
        "--onefile",
        "--windowed",
        "--hidden-import=tkinter",
        *common_args,
    ]

    print("\n" + "=" * 60)
    print("Building standard CLI version...")
    print("=" * 60)
    PyInstaller.__main__.run(cli_args)

    print("\n" + "=" * 60)
    print("Building standard GUI version...")
    print("=" * 60)
    PyInstaller.__main__.run(gui_args)


def build_ocr_versions():
    """Build the OCR-enabled CLI and GUI executables."""
    common_args = [
        "--add-data=config.py;.",
        "--add-data=.env.example;.",
        "--hidden-import=requests",
        "--hidden-import=fitz",
        "--hidden-import=PyMuPDF",
        "--hidden-import=pytesseract",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=numpy",
        "--distpath=./dist",
        "--workpath=./build",
        "--specpath=./spec_files",
        "--clean",
    ]

    cli_args = [
        "main_ocr.py",
        "--name=IDC_CLI_OCR",
        "--onefile",
        "--console",
        *common_args,
    ]
    gui_args = [
        "gui_ocr.py",
        "--name=IDC_GUI_OCR",
        "--onefile",
        "--windowed",
        "--hidden-import=tkinter",
        *common_args,
    ]

    print("\n" + "=" * 60)
    print("Building OCR CLI version...")
    print("=" * 60)
    PyInstaller.__main__.run(cli_args)

    print("\n" + "=" * 60)
    print("Building OCR GUI version...")
    print("=" * 60)
    PyInstaller.__main__.run(gui_args)


def print_usage():
    """Print a readable overview before argparse help."""
    print(
        """
IDC Build Script
================

Build options:
  python build_exe.py --all
  python build_exe.py --standard
  python build_exe.py --ocr
  python build_exe.py --clean

Output files:
  dist/IDC_CLI.exe
  dist/IDC_GUI.exe
  dist/IDC_CLI_OCR.exe
  dist/IDC_GUI_OCR.exe

Notes:
  - Standard requirements: pip install -r requirements.txt
  - OCR requirements: pip install -r requirements_ocr.txt
  - Tesseract must be installed separately for OCR runtime support.
  - Keep your real .env outside version control.
"""
    )


def main():
    parser = argparse.ArgumentParser(description="Build IDC executables")
    parser.add_argument("--all", action="store_true", help="Build standard and OCR versions")
    parser.add_argument("--standard", action="store_true", help="Build only standard versions")
    parser.add_argument("--ocr", action="store_true", help="Build only OCR versions")
    parser.add_argument("--clean", action="store_true", help="Only clean build directories")
    args = parser.parse_args()

    if not any([args.all, args.standard, args.ocr, args.clean]):
        print_usage()
        parser.print_help()
        return

    if args.clean:
        clean_build_dirs()
        print("Build directories cleaned.")
        return

    clean_build_dirs()

    print("\n" + "=" * 60)
    print("Building Independent Design Checker executables")
    print("=" * 60)

    if args.all or args.standard:
        build_standard_versions()
    if args.all or args.ocr:
        try:
            import pytesseract  # noqa: F401

            build_ocr_versions()
        except ImportError:
            print("\nWARNING: pytesseract is not installed. Skipping OCR builds.")
            print("Install OCR dependencies with: pip install -r requirements_ocr.txt")

    copy_runtime_files()

    print("\n" + "=" * 60)
    print("Build completed")
    print("=" * 60)
    print("Executables are in the dist folder.")
    print("Copy a real .env file next to the executables before runtime.")


if __name__ == "__main__":
    main()
