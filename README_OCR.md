# OCR Guide

Use the OCR version when the PDF is scanned, image-based, or only partly searchable.

In `v0.14`, OCR can also run on the company server through the intranet upload page. Staff upload a PDF in the browser and do not need local Tesseract or IDC EXE installation.

## Recommended Tools

- `IDC_GUI_OCR.exe` for most OCR use cases
- `IDC_CLI_OCR.exe` for batch or scripted usage

## OCR Modes

- `Auto (detect)`: best default for mixed files
- `Force OCR`: use when the whole PDF is scanned
- `No OCR`: use when the PDF already has selectable text

## GUI Workflow

1. Open `IDC_GUI_OCR.exe`.
2. Choose the PDF file.
3. Select `Building` or `Temporary`.
4. Select the OCR mode.
5. Confirm the output folder.
6. Click `Check Design`.

## CLI Examples

```powershell
IDC_CLI_OCR.exe "C:\path\to\design.pdf" --type building
IDC_CLI_OCR.exe "C:\path\to\scan.pdf" --type building --force-ocr
IDC_CLI_OCR.exe "C:\path\to\design.pdf" --type temporary --output-dir ".\reports"
IDC_CLI_OCR.exe "C:\path\to\design.pdf" --type building --no-ocr
```

## Dependencies

Install OCR Python packages:

```powershell
pip install -r requirements_ocr.txt
```

Install Tesseract separately:

[UB Mannheim Tesseract build](https://github.com/UB-Mannheim/tesseract/wiki)

Common install path:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

Custom server path:

```env
IDC_TESSERACT_CMD=D:\Apps\Tesseract-OCR\tesseract.exe
IDC_OCR_LANG=chi_sim+eng
```

## Server OCR

Install server dependencies:

```bat
server\install_server.bat
```

Start server:

```bat
server\run_server.bat
```

IT deployment details are in `docs/IT_SERVER_DEPLOYMENT.md`.

## Output

OCR reports are named like:

```text
filename_OCR_report.txt
```

The report header shows whether OCR was actually used.

## Troubleshooting

- If OCR is unavailable, install Tesseract or switch to `No OCR`.
- If recognition is weak, try `Force OCR` and use a cleaner PDF.
- If startup is slow, that is normal for the OCR build on first use.
