# Independent Design Checker (IDC) v0.16

IDC is a structural design review tool that reads PDF submissions and produces a structured Word report for building or temporary works review.

This `v0.16` release adds Grok/Kimi provider selection, stronger contractor submission batch review outputs, real/public sample validation, safer EXE packaging, and Docker-based intranet hosting. The desktop EXE workflow remains available for fast local testing and one-off reviews.

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

Reports are saved to `./reports` by default as `.docx` files.

## Runtime Setup

Create a `.env` file from `.env.example` and add your Grok API key:

```env
GROK_API_KEY=your-grok-api-key-here
GROK_API_URL=https://api.x.ai/v1/chat/completions
GROK_MODEL_NAME=grok-4-1-fast-non-reasoning
IDC_API_PROVIDER=grok
```

You can also point to a different env file with:

```text
IDC_ENV_FILE=C:\path\to\.env
```

## Advanced Options

### Intranet Server

Use the server mode when company staff should not install desktop EXEs or OCR software locally.

IT setup:

```bat
server\install_server.bat
server\run_server.bat
```

Then staff open:

```text
http://server-name:8080
```

Server deployment details are in `docs/IT_SERVER_DEPLOYMENT.md`.

Docker deployment is also available for a one-computer intranet host:

```powershell
copy .env.example .env
docker compose up -d --build
```

Docker details are in `docs/DOCKER_DEPLOYMENT.md`.

### QA Records Batch Checker

The server also includes a QA Records Batch Checker for OP records, mill certificates, concrete cube tests, reinforcement bar certificates/test reports, and similar contractor submission documents. It accepts multiple PDFs or ZIP uploads and returns a CSV register, exception CSV, raw JSON, summary file, and operator report.

Operator workflow:

1. Open the server page and confirm API and OCR are ready.
2. Open `QA Records Batch`.
3. Choose `Grok` or `Kimi` as the API provider. Grok is the default.
4. Choose `Auto detect` for mixed files, `Force OCR` for scanned files, or `No OCR` for searchable PDFs.
5. Upload PDFs or a ZIP package.
6. Download the output ZIP and review `qa_operator_report.md` first.
7. Check `qa_exceptions.csv` before accepting the register.

Sample validation can be run from source:

```powershell
python scripts\run_contractor_submission_samples.py
```

Add `--run-ai` when the selected provider API key is configured.

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

Server version:

```powershell
pip install -r requirements_server.txt
```

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
- `server/idc_server.py`: intranet upload server
- `qa_records.py`: QA records batch classification and register extraction
- `scripts/run_contractor_submission_samples.py`: real scanned and public electronic sample validation harness
- `server/*.bat`: IT installation and server startup scripts
- `config.py`: runtime configuration
- `docs/USER_GUIDE.md`: end-user guide
- `docs/IT_SERVER_DEPLOYMENT.md`: IT deployment guide
- `docs/DOCKER_DEPLOYMENT.md`: Docker deployment guide
- `docs/WORKFLOW.md`: product workflow diagram and operating modes
- `docs/PRD.md`: product requirements, version register, and roadmap
- `API_SETUP_GUIDE.md`: Grok API setup steps
- `README_OCR.md`: OCR notes

## Security Notes

- Do not commit `.env`.
- Do not embed real API keys into code, logs, or docs.
- Put the real `.env` next to the executable only on trusted machines.
- For server deployments, bind only to the trusted intranet and use `IDC_SERVER_ACCESS_TOKEN` unless another access control layer is already enforced.
