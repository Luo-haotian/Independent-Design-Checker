"""Intranet web server for IDC uploads and server-side OCR processing."""

from __future__ import annotations

import os
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from flask import Flask, abort, redirect, render_template_string, request, send_file, url_for
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from main_ocr import CheckerOCR, TESSERACT_AVAILABLE  # noqa: E402
from config import API_KEY  # noqa: E402

UPLOAD_DIR = Path(os.environ.get("IDC_SERVER_UPLOAD_DIR", BASE_DIR / "server_uploads")).resolve()
REPORT_DIR = Path(os.environ.get("IDC_SERVER_REPORT_DIR", BASE_DIR / "server_reports")).resolve()
MAX_UPLOAD_MB = int(os.environ.get("IDC_SERVER_MAX_UPLOAD_MB", "200"))
ACCESS_TOKEN = os.environ.get("IDC_SERVER_ACCESS_TOKEN", "").strip()
MAX_WORKERS = max(1, int(os.environ.get("IDC_SERVER_WORKERS", "1")))
VALID_STRUCT_TYPES = {"building", "temporary"}
VALID_OCR_MODES = {"auto", "force", "no-ocr"}

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
app.config["SECRET_KEY"] = os.environ.get("IDC_SERVER_SECRET_KEY", "idc-local-server")

executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
jobs: dict[str, dict[str, Any]] = {}
jobs_lock = threading.Lock()


BASE_CSS = """
<style>
:root {
  color-scheme: light;
  --ink: #162033;
  --muted: #667085;
  --line: #d9e0ea;
  --brand: #154d93;
  --brand-dark: #0e3567;
  --ok: #147a46;
  --warn: #9a5b00;
  --bad: #b42318;
  font-family: Arial, Helvetica, sans-serif;
}
* { box-sizing: border-box; }
body { margin: 0; background: #f5f7fb; color: var(--ink); }
header { background: #ffffff; border-bottom: 1px solid var(--line); }
.topbar { max-width: 980px; margin: 0 auto; padding: 18px 24px; display: flex; justify-content: space-between; gap: 16px; align-items: center; }
.brand { font-weight: 700; font-size: 18px; color: var(--brand); }
.status-pill { border: 1px solid var(--line); border-radius: 999px; padding: 6px 10px; color: var(--muted); font-size: 13px; background: #fff; }
main { max-width: 980px; margin: 0 auto; padding: 28px 24px 52px; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 310px; gap: 20px; align-items: start; }
.panel { background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 22px; }
h1 { margin: 0 0 6px; font-size: 26px; letter-spacing: 0; }
h2 { margin: 0 0 12px; font-size: 17px; letter-spacing: 0; }
p { margin: 0 0 16px; color: var(--muted); line-height: 1.55; }
label { display: block; margin: 14px 0 6px; font-weight: 700; font-size: 14px; }
input, select { width: 100%; min-height: 42px; border: 1px solid var(--line); border-radius: 6px; padding: 9px 10px; font: inherit; background: #fff; }
input[type=file] { padding: 8px; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
button, .button { display: inline-flex; align-items: center; justify-content: center; min-height: 42px; border: 0; border-radius: 6px; padding: 0 16px; background: var(--brand); color: #fff; font-weight: 700; text-decoration: none; cursor: pointer; }
button:hover, .button:hover { background: var(--brand-dark); }
.button.secondary { background: #eef3f9; color: var(--brand); border: 1px solid #c8d7e8; }
.meta { display: grid; gap: 10px; margin-top: 12px; }
.meta div { display: flex; justify-content: space-between; gap: 14px; border-bottom: 1px solid #eef1f5; padding-bottom: 8px; font-size: 14px; }
.meta span:first-child { color: var(--muted); }
.status { font-weight: 700; }
.queued { color: var(--warn); }
.running { color: var(--brand); }
.completed { color: var(--ok); }
.failed { color: var(--bad); }
.log { white-space: pre-wrap; background: #111827; color: #e5e7eb; border-radius: 8px; padding: 14px; min-height: 180px; overflow: auto; font: 13px/1.5 Consolas, monospace; }
.actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
.note { font-size: 13px; color: var(--muted); }
@media (max-width: 780px) {
  .layout, .row { grid-template-columns: 1fr; }
  main, .topbar { padding-left: 16px; padding-right: 16px; }
}
</style>
"""


def _token_from_request() -> str:
    return (
        request.headers.get("X-IDC-Token")
        or request.args.get("token")
        or request.form.get("token")
        or ""
    ).strip()


def _require_token() -> None:
    if ACCESS_TOKEN and _token_from_request() != ACCESS_TOKEN:
        abort(403)


def _safe_token_query() -> str:
    token = _token_from_request()
    if ACCESS_TOKEN and token:
        return "?" + urlencode({"token": token})
    return ""


def _job_snapshot(job_id: str) -> dict[str, Any] | None:
    with jobs_lock:
        job = jobs.get(job_id)
        return dict(job) if job else None


def _update_job(job_id: str, **updates: Any) -> None:
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(updates)


def _append_log(job_id: str, message: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id]["log"].append(f"[{stamp}] {message}")


def _run_job(job_id: str) -> None:
    job = _job_snapshot(job_id)
    if not job:
        return

    started = time.time()
    _update_job(job_id, status="running", started_at=datetime.now().isoformat(timespec="seconds"))
    _append_log(job_id, "Server accepted the upload and started IDC processing.")

    try:
        checker = CheckerOCR(
            model_name=job["model"] or None,
            use_ocr=job["ocr_mode"] != "no-ocr",
        )
        force_ocr = job["ocr_mode"] == "force"
        success = checker.check(
            job["input_path"],
            job["struct_type"],
            str(REPORT_DIR),
            force_ocr=force_ocr,
        )

        if success and checker.last_report_file and Path(checker.last_report_file).exists():
            elapsed = round(time.time() - started, 1)
            _update_job(
                job_id,
                status="completed",
                report_path=checker.last_report_file,
                completed_at=datetime.now().isoformat(timespec="seconds"),
                elapsed_seconds=elapsed,
            )
            _append_log(job_id, f"Report completed in {elapsed} seconds.")
            _append_log(job_id, f"Output: {checker.last_report_file}")
            return

        _update_job(job_id, status="failed", completed_at=datetime.now().isoformat(timespec="seconds"))
        _append_log(job_id, "IDC processing failed. Check the API key, PDF readability, and OCR setup.")
    except Exception as exc:  # noqa: BLE001 - show operational errors to IT/user
        _update_job(job_id, status="failed", completed_at=datetime.now().isoformat(timespec="seconds"))
        _append_log(job_id, f"Error: {exc}")


@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "api_key_configured": bool(API_KEY),
        "tesseract_available": TESSERACT_AVAILABLE,
        "workers": MAX_WORKERS,
    }


@app.get("/")
def index():
    tesseract_label = "ready" if TESSERACT_AVAILABLE else "not detected"
    api_label = "configured" if API_KEY else "missing"
    return render_template_string(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IDC Server Upload</title>
  {{ css|safe }}
</head>
<body>
  <header>
    <div class="topbar">
      <div class="brand">Independent Design Checker</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end">
        <div class="status-pill">API: {{ api_label }}</div>
        <div class="status-pill">OCR: {{ tesseract_label }}</div>
      </div>
    </div>
  </header>
  <main>
    <div class="layout">
      <section class="panel">
        <h1>Server IDC Review</h1>
        <p>Upload a PDF submission. Extraction, OCR, API analysis, and Word report generation run on this server.</p>
        {% if not api_ready %}
        <p style="color:#b42318;font-weight:700">GROK_API_KEY is not configured on the server. Ask IT to edit the project .env file before uploading.</p>
        {% endif %}
        <form action="{{ url_for('create_job') }}" method="post" enctype="multipart/form-data">
          {% if token_required %}
          <label for="token">Access token</label>
          <input id="token" name="token" type="password" autocomplete="current-password" required>
          {% endif %}
          <label for="pdf_file">PDF file</label>
          <input id="pdf_file" name="pdf_file" type="file" accept="application/pdf,.pdf" required>
          <div class="row">
            <div>
              <label for="struct_type">Review type</label>
              <select id="struct_type" name="struct_type">
                <option value="building">Building</option>
                <option value="temporary">Temporary</option>
              </select>
            </div>
            <div>
              <label for="ocr_mode">OCR mode</label>
              <select id="ocr_mode" name="ocr_mode">
                <option value="auto">Auto detect</option>
                <option value="force">Force OCR</option>
                <option value="no-ocr">No OCR</option>
              </select>
            </div>
          </div>
          <label for="model">Model override</label>
          <input id="model" name="model" type="text" placeholder="Use server default">
          <div class="actions">
            <button type="submit">Upload and Start</button>
          </div>
        </form>
      </section>
      <aside class="panel">
        <h2>Server Settings</h2>
        <div class="meta">
          <div><span>Max upload</span><strong>{{ max_upload_mb }} MB</strong></div>
          <div><span>Workers</span><strong>{{ workers }}</strong></div>
          <div><span>Uploads</span><strong>{{ upload_dir }}</strong></div>
          <div><span>Reports</span><strong>{{ report_dir }}</strong></div>
        </div>
      </aside>
    </div>
  </main>
</body>
</html>
        """,
        css=BASE_CSS,
        max_upload_mb=MAX_UPLOAD_MB,
        workers=MAX_WORKERS,
        upload_dir=str(UPLOAD_DIR),
        report_dir=str(REPORT_DIR),
        token_required=bool(ACCESS_TOKEN),
        tesseract_label=tesseract_label,
        api_label=api_label,
        api_ready=bool(API_KEY),
    )


@app.post("/jobs")
def create_job():
    _require_token()
    uploaded = request.files.get("pdf_file")
    if not uploaded or not uploaded.filename:
        abort(400, "No PDF file uploaded.")

    filename = secure_filename(uploaded.filename)
    if not filename.lower().endswith(".pdf"):
        abort(400, "Only PDF uploads are supported.")

    job_id = uuid.uuid4().hex[:12]
    job_dir = UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    input_path = job_dir / filename
    uploaded.save(input_path)
    struct_type = request.form.get("struct_type", "building")
    ocr_mode = request.form.get("ocr_mode", "auto")
    if struct_type not in VALID_STRUCT_TYPES:
        abort(400, "Invalid review type.")
    if ocr_mode not in VALID_OCR_MODES:
        abort(400, "Invalid OCR mode.")

    job = {
        "id": job_id,
        "filename": filename,
        "input_path": str(input_path),
        "struct_type": struct_type,
        "ocr_mode": ocr_mode,
        "model": request.form.get("model", "").strip(),
        "status": "queued",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "started_at": "",
        "completed_at": "",
        "elapsed_seconds": "",
        "report_path": "",
        "log": ["Upload received. Waiting for worker."],
    }
    with jobs_lock:
        jobs[job_id] = job

    executor.submit(_run_job, job_id)
    return redirect(url_for("job_status", job_id=job_id) + _safe_token_query())


@app.get("/jobs/<job_id>")
def job_status(job_id: str):
    _require_token()
    job = _job_snapshot(job_id)
    if not job:
        abort(404)

    token_query = _safe_token_query()
    download_url = url_for("download_report", job_id=job_id) + token_query if job.get("report_path") else ""
    refresh_tag = "" if job["status"] in {"completed", "failed"} else '<meta http-equiv="refresh" content="5">'
    return render_template_string(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {{ refresh_tag|safe }}
  <title>IDC Job {{ job.id }}</title>
  {{ css|safe }}
</head>
<body>
  <header>
    <div class="topbar">
      <div class="brand">Independent Design Checker</div>
      <div class="status-pill">Job {{ job.id }}</div>
    </div>
  </header>
  <main>
    <section class="panel">
      <h1>{{ job.filename }}</h1>
      <p>Status: <span class="status {{ job.status }}">{{ job.status|upper }}</span></p>
      <div class="meta">
        <div><span>Review type</span><strong>{{ job.struct_type }}</strong></div>
        <div><span>OCR mode</span><strong>{{ job.ocr_mode }}</strong></div>
        <div><span>Created</span><strong>{{ job.created_at }}</strong></div>
        <div><span>Started</span><strong>{{ job.started_at or "-" }}</strong></div>
        <div><span>Completed</span><strong>{{ job.completed_at or "-" }}</strong></div>
      </div>
      <div class="actions">
        <a class="button secondary" href="/{{ token_query }}">New Upload</a>
        {% if download_url %}
        <a class="button" href="{{ download_url }}">Download Report</a>
        {% endif %}
      </div>
    </section>
    <section class="panel" style="margin-top:20px">
      <h2>Processing Log</h2>
      <div class="log">{{ log_text }}</div>
      {% if job.status not in ["completed", "failed"] %}
      <p class="note" style="margin-top:12px">This page refreshes every 5 seconds while the job is running.</p>
      {% endif %}
    </section>
  </main>
</body>
</html>
        """,
        css=BASE_CSS,
        job=job,
        log_text="\n".join(job["log"]),
        download_url=download_url,
        token_query=token_query,
        refresh_tag=refresh_tag,
    )


@app.get("/jobs/<job_id>/download")
def download_report(job_id: str):
    _require_token()
    job = _job_snapshot(job_id)
    if not job or not job.get("report_path"):
        abort(404)

    report_path = Path(job["report_path"]).resolve()
    if not report_path.exists() or REPORT_DIR not in report_path.parents:
        abort(404)
    return send_file(report_path, as_attachment=True)


def run() -> None:
    host = os.environ.get("IDC_SERVER_HOST", "127.0.0.1")
    port = int(os.environ.get("IDC_SERVER_PORT", "8080"))
    use_waitress = os.environ.get("IDC_SERVER_USE_WAITRESS", "1") != "0"

    if use_waitress:
        try:
            from waitress import serve

            print(f"IDC server listening on http://{host}:{port}")
            serve(app, host=host, port=port, threads=MAX_WORKERS + 2)
            return
        except ImportError:
            print("waitress is not installed. Falling back to Flask development server.")

    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run()
