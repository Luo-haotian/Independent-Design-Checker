# IDC v0.14 IT Server Deployment Guide

This guide is for installing IDC on a company intranet server so staff can upload PDF submissions in a browser. PDF parsing, OCR, Grok analysis, and Word report generation run on the server.

## Server Requirements

- Windows Server or Windows 10/11 host on the company intranet
- Python 3.10 or later
- Tesseract OCR installed on the server
- Network access from the server to the configured Grok API endpoint
- A server-side `.env` file containing `GROK_API_KEY`

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
MODEL_NAME=grok-4-1-fast-non-reasoning

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

Keep `IDC_SERVER_ACCESS_TOKEN` enabled unless the intranet is already protected by a stronger access control layer.

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
