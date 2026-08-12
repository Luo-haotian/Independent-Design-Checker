# IDC v0.16 IT Server Deployment Guide

This guide is for installing IDC on a company intranet server so staff can upload PDF submissions in a browser. PDF parsing, OCR, API analysis, and Word report generation run on the server. Grok is the default API provider; Kimi/Moonshot can be enabled as an OpenAI-compatible provider.

## Server Requirements

- Windows Server or Windows 10/11 host on the company intranet
- Python 3.10 or later
- Tesseract OCR installed on the server
- Network access from the server to the configured API endpoint
- A server-side `.env` file containing at least `GROK_API_KEY`, or Kimi credentials when Kimi is selected

Tesseract default path:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

If Tesseract is installed elsewhere, set `IDC_TESSERACT_CMD` in `.env`.

## Install

Run from the project root:

```bat
server\install_server.bat
```

The script creates `.venv-server`, installs `requirements_server.txt`, and creates `.env` from `.env.example` when `.env` does not exist.

Edit `.env` before production use:

```env
GROK_API_KEY=your-real-key
GROK_API_URL=https://api.x.ai/v1/chat/completions
GROK_MODEL_NAME=grok-4-1-fast-non-reasoning
IDC_API_PROVIDER=grok

# Optional Kimi/Moonshot provider
# KIMI_API_KEY=your-real-kimi-key
# MOONSHOT_API_KEY=your-real-kimi-key
# KIMI_API_URL=https://api.moonshot.cn/v1/chat/completions
# KIMI_MODEL_NAME=kimi-k2.5

IDC_SERVER_HOST=0.0.0.0
IDC_SERVER_PORT=8080
IDC_SERVER_ACCESS_TOKEN=change-this-token
IDC_SERVER_MAX_UPLOAD_MB=200
IDC_SERVER_WORKERS=1
IDC_TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
IDC_OCR_LANG=chi_sim+eng
```

## Start

```bat
server\run_server.bat
```

Staff can open:

```text
http://server-name:8080
```

The QA records batch page is available from the main page through `QA Records Batch`, or directly at:

```text
http://server-name:8080/qa
```

Keep `IDC_SERVER_ACCESS_TOKEN` enabled unless the intranet is already protected by a stronger access control layer.

## Docker Option

If the host computer has Docker Desktop, IDC can also run as a container:

```powershell
copy .env.example .env
notepad .env
docker compose up -d --build
```

See `docs/DOCKER_DEPLOYMENT.md` for the one-computer intranet deployment workflow.

## API Provider Selection

The upload pages include an API provider dropdown:

- `Grok` is the default and uses `GROK_API_KEY`, `GROK_API_URL`, and `GROK_MODEL_NAME`.
- `Kimi` uses `KIMI_API_KEY` or `MOONSHOT_API_KEY`, plus `KIMI_API_URL` and `KIMI_MODEL_NAME`.

Kimi/Moonshot is OpenAI-compatible, so no separate SDK is required. The server sends the same chat-completions request shape to the selected provider.

## Optional Startup Task

Run as Administrator:

```bat
server\install_windows_task.bat
```

Then start the task:

```bat
schtasks /Run /TN "IDC Server"
```

## Firewall

Open inbound TCP for the configured port, for example `8080`, only on the trusted intranet profile. Do not expose this service directly to the public internet.

## Data Locations

Defaults:

```text
server_uploads
server_reports
```

Override with:

```env
IDC_SERVER_UPLOAD_DIR=D:\IDC\uploads
IDC_SERVER_REPORT_DIR=D:\IDC\reports
```

These folders may contain confidential submissions and generated reports. Put them on a protected server volume and include them in the company's retention policy.

## Operational Notes

- `IDC_SERVER_WORKERS=1` is recommended initially because OCR is CPU-heavy and each report can trigger a long API call.
- Increase workers only after confirming server CPU, memory, and API rate limits.
- If OCR is unavailable, the upload still runs text-layer extraction when possible, but scanned PDFs will not produce useful content.
- The `/healthz` endpoint returns a simple JSON health check including OCR availability.
- QA Records Batch Checker outputs CSV, JSON, summary, and operator report files in the configured report directory. Treat these outputs as confidential project records.

## Sample Validation

Run the sample harness from the project root:

```powershell
python scripts\run_contractor_submission_samples.py
```

This profiles the real scanned Batch 15/16 reinforcement submission samples and downloads public electronic mill certificate / concrete cube examples. Add `--run-ai` only after the selected provider API key is configured:

```powershell
python scripts\run_contractor_submission_samples.py --provider grok --run-ai
python scripts\run_contractor_submission_samples.py --provider kimi --run-ai
```
# v0.17 Required Controls

Set `IDC_SERVER_ACCESS_TOKEN`, a long random `IDC_SERVER_SECRET_KEY`, `IDC_DATA_DIR`, `IDC_CODE_LIBRARY`, and `IDC_RETENTION_DAYS=30`. Put official code PDFs in the read-only code library and verify filenames/hashes against the selected manifest. Users sign in at `/login`; tokens must not be embedded in bookmarks or links.

Back up the SQLite file in `IDC_DATA_DIR` because it contains persistent findings, edits, decisions, and audit events. Raw upload/report directories are temporary and are cleaned by retention policy.
