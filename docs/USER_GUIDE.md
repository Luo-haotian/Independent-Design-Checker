# IDC User Guide v0.14

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

IDC reads the PDF and writes a Word report that usually includes:

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

## Company Server Mode

If your company IT team has deployed the IDC server, open the intranet address they provide, for example:

```text
http://server-name:8080
```

Upload the PDF, choose `Building` or `Temporary`, select an OCR mode, and wait for the Word report download link. In this mode, OCR and report generation run on the server, so you do not need to install IDC or Tesseract on your own computer.

## QA Records Batch Checker

Use this server feature when you need to batch register OP records, mill certificates, concrete cube test reports, reinforcement test reports, or similar QA records.

Basic steps:

1. Open the intranet server page.
2. Click `QA Records Batch`.
3. Upload multiple PDFs or one ZIP package containing PDFs.
4. Select the OCR mode.
5. Wait for the batch job to finish.
6. Download the QA output ZIP.

The ZIP contains:

- `qa_register.csv`: extracted register table
- `qa_exceptions.csv`: records requiring human review
- `qa_raw_results.json`: raw extracted data for audit/debug
- `qa_summary.txt`: short processing summary

Always check the CSV register against the source documents before using it as an official project record.

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

For server mode, contact IT if the upload page is unavailable, the access token is rejected, or the job remains queued for a long time.
