# OCR Guide

Use the OCR version when the PDF is scanned, image-based, or only partly searchable.

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
