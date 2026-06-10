# IDC Docker Deployment Guide

Use Docker when one computer should host IDC for other staff on the company intranet.

## What This Provides

- Browser access to IDC Server at port `8080`.
- Server-side OCR with Tesseract.
- Server-side QA Records Batch Checker.
- Persistent Docker volumes for uploads and generated reports.

## Target Computer Requirements

- Windows 10/11 or Windows Server with Docker Desktop installed.
- Network access from that computer to the selected API provider.
- A valid Grok API key, or Kimi/Moonshot key if Kimi is selected.
- Intranet firewall rule allowing other staff to reach port `8080`.

## One-Time Setup

From the project folder:

```powershell
copy .env.example .env
notepad .env
```

Minimum Grok setup:

```env
IDC_API_PROVIDER=grok
GROK_API_KEY=your-real-grok-key
GROK_API_URL=https://api.x.ai/v1/chat/completions
GROK_MODEL_NAME=grok-4-1-fast-non-reasoning
IDC_SERVER_ACCESS_TOKEN=change-this-token
```

Optional Kimi setup:

```env
KIMI_API_KEY=your-real-kimi-key
KIMI_API_URL=https://api.moonshot.cn/v1/chat/completions
KIMI_MODEL_NAME=kimi-k2.5
```

## Start IDC

```powershell
docker compose up -d --build
```

Open on the host computer:

```text
http://localhost:8080
```

Other staff can open:

```text
http://HOST-COMPUTER-IP:8080
```

If `IDC_SERVER_ACCESS_TOKEN` is set, give staff the token through an internal secure channel.

## Stop Or Update

Stop:

```powershell
docker compose down
```

Update after pulling a new release:

```powershell
docker compose up -d --build
```

## Data

Uploads and reports are stored in Docker volumes:

- `idc_uploads`
- `idc_reports`

They may contain confidential submissions. Apply the company retention and backup policy.

## Health Check

Open:

```text
http://localhost:8080/healthz
```

The JSON should show `ok: true`, OCR availability, and whether Grok/Kimi keys are configured.
