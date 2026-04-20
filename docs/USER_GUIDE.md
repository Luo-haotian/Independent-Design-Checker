# IDC User Guide v0.11

## Quick Start

For most users, start with:

```text
IDC_GUI.exe
```

Or from source:

```powershell
python gui.py
```

Basic steps:

1. Open `IDC_GUI`.
2. Choose the PDF file.
3. Select `Building` or `Temporary`.
4. Confirm the output folder.
5. Click `Check Design`.

That is the default workflow.

## What The Tool Produces

IDC reads the PDF and writes a text report that usually includes:

- executive summary
- technical review comments
- identified issues
- recommendations

The default output location is:

```text
.\reports
```

## Which Type To Choose

- `Building`: permanent building structure submissions
- `Temporary`: temporary works, falsework, supports, scaffolding, crane ties, and similar files

## Advanced Option: OCR

Use OCR when the PDF is scanned or image-based.

Recommended tool:

```text
IDC_GUI_OCR.exe
```

OCR modes:

- `Auto (detect)` for mixed documents
- `Force OCR` for fully scanned PDFs
- `No OCR` for text-based PDFs

## Advanced Option: CLI

Standard CLI:

```powershell
python main.py "C:\path\to\design.pdf" --type building
```

OCR CLI:

```powershell
python main_ocr.py "C:\path\to\design.pdf" --type building --force-ocr
```

## Common Issues

If the run fails, check:

- the PDF path is correct
- the PDF can be opened normally
- `.env` exists and contains a valid `GROK_API_KEY`
- the network is available

For OCR issues, also check that Tesseract is installed.
