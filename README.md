# Independent Design Checker

IDC v0.17 is an evidence-aware structural review application. Hong Kong is the default jurisdiction, but every project pins an explicit code pack. The application preserves the existing CLI, OCR, desktop GUI, server, QA-record batch, Grok/Kimi narrative review, Word report, Docker, and PyInstaller workflows.

## Trust Model

- Only deterministic rules can return engineering `PASS` or `FAIL`.
- AI narrative is labelled as an observation and cannot override a deterministic result.
- Missing or conflicting required facts return `INSUFFICIENT_EVIDENCE` or `CONFLICT`.
- Page evidence, source SHA-256, code basis, formulas, limitations, and audit decisions remain traceable.
- The bundled HK rules are **pending responsible structural engineer approval** and are not a certified design service.

## v0.17 Deterministic Scope

The first vertical slice covers non-prestressed, normal-depth, rectangular, singly reinforced RC beams: flexure, required/provided tension reinforcement, reinforcement limits, shear resistance, links, minimum links, and spacing. Deep, flanged, prestressed, axially loaded, and torsion-loaded beams return `OUT_OF_SCOPE`.

## Quick Start

Use Python 3.11 or 3.12:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,ocr,server]"
Copy-Item .env.example .env
```

Place official code PDFs outside the repository and set `IDC_CODE_LIBRARY`. The application verifies them against hashes in the selected pack manifest.

```powershell
python main.py design.pdf --jurisdiction HK `
  --code-pack hk-bd-concrete-2020-amd-2024-04 `
  --code-as-of 2024-04-01 --input-overrides reviewed_beam_facts.json `
  --export-json
```

The critic pass is optional and disabled by default. Enable it with `--critic`; its output remains non-authoritative.

## Beam Fact Input

Deterministic checks require reviewer-confirmed values with page evidence. See [the user guide](docs/USER_GUIDE.md) for the JSON schema. No fact is inferred into a deterministic `PASS` without evidence.

## Server

```powershell
python server\idc_server.py
```

When `IDC_SERVER_ACCESS_TOKEN` is set, users exchange it through `/login`. The token is not carried in URLs or redirects. Fact edits and signed decisions require CSRF protection, reviewer name, reason, and evidence. SQLite data is stored under `IDC_DATA_DIR`.

## Development

```powershell
python -m pytest
python -m ruff check idc tests main.py main_ocr.py qa_records.py server/idc_server.py
python build_exe.py --all --output-root C:\temp\idc-build
```

CI tests Python 3.11/3.12 on Windows and Linux. Raw uploads and generated reports expire after `IDC_RETENTION_DAYS` (default 30); hashes, facts, results, decisions, and audit events remain in SQLite.

## Documentation

- [Development roadmap](docs/DEVELOPMENT_ROADMAP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Code-pack governance](docs/CODE_PACK_GOVERNANCE.md)
- [Security and limitations](docs/SECURITY.md)
- [User guide](docs/USER_GUIDE.md)
- [Server deployment](docs/IT_SERVER_DEPLOYMENT.md)
- [Docker deployment](docs/DOCKER_DEPLOYMENT.md)

Official code PDFs, confidential submissions, company workbooks, `.env`, and generated outputs must remain outside the public repository.
