# IDC User Guide v0.16

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

Upload the PDF, choose `Building` or `Temporary`, select the API provider, select an OCR mode, and wait for the Word report download link. In this mode, OCR and report generation run on the server, so you do not need to install IDC or Tesseract on your own computer.

API provider:

- `Grok`: default provider.
- `Kimi`: optional provider. IT must configure `KIMI_API_KEY` or `MOONSHOT_API_KEY` first.

## QA Records Batch Checker

Use this server feature when you need to batch register OP records, mill certificates, concrete cube test reports, reinforcement bar certificates/test reports, or similar contractor submission QA records.

Basic steps:

1. Open the intranet server page and confirm the API and OCR status labels are ready.
2. Click `QA Records Batch`.
3. Select the API provider. Use `Grok` unless IT asks you to test `Kimi`.
4. Select the OCR mode:
   - `Auto detect` for mixed scanned/searchable files.
   - `Force OCR` for scanned contractor submissions.
   - `No OCR` for clean searchable PDFs.
5. Upload multiple PDFs or one ZIP package containing PDFs.
6. Wait for the batch job to finish.
7. Download the QA output ZIP.
8. Open `qa_operator_report.md` first, then check the exception CSV.

The ZIP contains:

- `qa_register.csv`: extracted register table
- `qa_exceptions.csv`: records requiring human review
- `qa_raw_results.json`: raw extracted data for audit/debug
- `qa_summary.txt`: short processing summary
- `qa_operator_report.md`: plain-language operator report with next actions

Always check the CSV register against the source documents before using it as an official project record.

For scanned submissions, manually verify heat numbers, batch numbers, bar marks, cube IDs, sample IDs, grades, dates, and result values against the source PDF.

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
- `.env` exists and contains a valid key for the selected API provider
- the network is available

For OCR issues, also check that Tesseract is installed.

For server mode, contact IT if the upload page is unavailable, the access token is rejected, or the job remains queued for a long time.
