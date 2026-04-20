# Independent Design Checker (IDC) v0.11

IDC is a structural design review tool that reads PDF submissions and produces a text report for building or temporary works review.

This `v0.11` cleanup release standardizes the project around the Grok API, removes legacy multi-provider references, and aligns the OCR workflow with `Tesseract + pytesseract`.

## Quick Start

For most users, start with the standard GUI:

```text
IDC_GUI.exe
```

Or run from source:

```powershell
python gui.py
```

Basic workflow:

1. Open `IDC_GUI`.
2. Choose the PDF file.
3. Select `Building` or `Temporary`.
4. Confirm the output folder.
5. Click `Check Design`.

Reports are saved to `./reports` by default.

## Runtime Setup

Create a `.env` file from `.env.example` and add your Grok API key:

```env
GROK_API_KEY=your-grok-api-key-here
GROK_API_URL=https://api.x.ai/v1/chat/completions
MODEL_NAME=grok-4-1-fast-non-reasoning
```

You can also point to a different env file with:

```text
IDC_ENV_FILE=C:\path\to\.env
```

## Advanced Options

### OCR GUI

Use `IDC_GUI_OCR.exe` or:

```powershell
python gui_ocr.py
```

Recommended when the PDF is scanned, image-based, or only partly searchable.

### CLI

Standard CLI:

```powershell
python main.py "C:\path\to\design.pdf" --type building
```

OCR CLI:

```powershell
python main_ocr.py "C:\path\to\design.pdf" --type building --force-ocr
```

## Installation

Standard version:

```powershell
pip install -r requirements.txt
```

OCR version:

```powershell
pip install -r requirements_ocr.txt
```

OCR runtime also requires Tesseract:

[UB Mannheim Tesseract build](https://github.com/UB-Mannheim/tesseract/wiki)

## Build Executables

Build all executables:

```powershell
python build_exe.py --all
```

Build only the standard version:

```powershell
python build_exe.py --standard
```

Build only OCR executables:

```powershell
python build_exe.py --ocr
```

## Project Structure

- `gui.py`: standard desktop GUI
- `gui_ocr.py`: OCR desktop GUI
- `main.py`: standard CLI engine
- `main_ocr.py`: OCR CLI engine
- `config.py`: runtime configuration
- `docs/USER_GUIDE.md`: end-user guide
- `API_SETUP_GUIDE.md`: Grok API setup steps
- `README_OCR.md`: OCR notes

## Security Notes

- Do not commit `.env`.
- Do not embed real API keys into code, logs, or docs.
- Put the real `.env` next to the executable only on trusted machines.
