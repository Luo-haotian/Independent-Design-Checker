"""Intranet web server for IDC uploads and server-side OCR processing."""

from __future__ import annotations

import hmac
import os
import secrets
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, redirect, render_template_string, request, send_file, session, url_for
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import (  # noqa: E402
    API_PROVIDER,
    available_providers,
    get_default_model,
    get_provider_label,
    is_provider_configured,
)
from idc.persistence import ReviewStore  # noqa: E402
from idc.profiles import REVIEW_PROFILES  # noqa: E402
from idc.retention import cleanup_expired_files  # noqa: E402
from idc.submission import format_page_ranges  # noqa: E402
from main_ocr import TESSERACT_AVAILABLE, CheckerOCR  # noqa: E402
from qa_records import run_qa_batch  # noqa: E402

UPLOAD_DIR = Path(os.environ.get("IDC_SERVER_UPLOAD_DIR", BASE_DIR / "server_uploads")).resolve()
REPORT_DIR = Path(os.environ.get("IDC_SERVER_REPORT_DIR", BASE_DIR / "server_reports")).resolve()
MAX_UPLOAD_MB = int(os.environ.get("IDC_SERVER_MAX_UPLOAD_MB", "200"))
ACCESS_TOKEN = os.environ.get("IDC_SERVER_ACCESS_TOKEN", "").strip()
MAX_WORKERS = max(1, int(os.environ.get("IDC_SERVER_WORKERS", "1")))
VALID_STRUCT_TYPES = {"building", "temporary"}
VALID_OCR_MODES = {"auto", "force", "no-ocr"}
VALID_QA_EXTENSIONS = {".pdf", ".zip"}
VALID_API_PROVIDERS = set(available_providers())
DATA_DIR = Path(os.environ.get("IDC_DATA_DIR", BASE_DIR / "idc_data")).resolve()

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
app.config["SECRET_KEY"] = os.environ.get("IDC_SERVER_SECRET_KEY") or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("IDC_SESSION_COOKIE_SECURE", "0") == "1",
)
store = ReviewStore(DATA_DIR / "reviews.sqlite3")
cleanup_expired_files([UPLOAD_DIR, REPORT_DIR])

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
.result-main { max-width: 1200px; }
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
.meta div { display: grid; grid-template-columns: minmax(90px, auto) minmax(0, 1fr); align-items: start; gap: 14px; border-bottom: 1px solid #eef1f5; padding-bottom: 8px; font-size: 14px; }
.meta span:first-child { color: var(--muted); }
.meta strong { min-width: 0; text-align: right; overflow-wrap: anywhere; word-break: break-word; }
.settings-path { font: 600 12px/1.4 Consolas, "Courier New", monospace; }
.status { font-weight: 700; }
.queued { color: var(--warn); }
.running { color: var(--brand); }
.completed { color: var(--ok); }
.failed { color: var(--bad); }
.log { white-space: pre-wrap; background: #111827; color: #e5e7eb; border-radius: 8px; padding: 14px; min-height: 180px; overflow: auto; font: 13px/1.5 Consolas, monospace; }
.actions { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
.note { font-size: 13px; color: var(--muted); }
.profile-card { margin-top: 20px; padding: 16px; border: 1px solid #c8d7e8; border-radius: 8px; background: #f7faff; }
.profile-card h3 { margin: 0 0 7px; font-size: 15px; color: var(--brand); }
.profile-card p { margin-bottom: 9px; font-size: 13px; }
.profile-card ul { margin: 6px 0 0; padding-left: 19px; color: var(--muted); font-size: 13px; line-height: 1.45; }
.comment-preview { margin-top: 24px; }
.comment-preview-header { display: flex; justify-content: space-between; gap: 16px; align-items: end; margin-bottom: 10px; }
.comment-preview-header h2 { margin-bottom: 2px; }
.comment-preview-header p { margin: 0; font-size: 13px; }
.comment-table-wrap { width: 100%; overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; }
.comment-table { width: 100%; min-width: 900px; border-collapse: collapse; table-layout: fixed; font-size: 13px; line-height: 1.42; }
.comment-table th { padding: 10px; background: var(--brand); color: #fff; text-align: left; vertical-align: top; }
.comment-table td { padding: 11px 10px; border-top: 1px solid var(--line); vertical-align: top; overflow-wrap: anywhere; word-break: break-word; }
.comment-table tbody tr:nth-child(even) { background: #f8fafc; }
.comment-table .comment-no { text-align: center; font-weight: 700; }
.comment-table .comment-note { margin-top: 7px; color: var(--muted); font-size: 12px; }
.assessment { display: inline-block; margin-top: 7px; border-radius: 999px; padding: 3px 7px; font-size: 11px; font-weight: 700; letter-spacing: .01em; }
.assessment-requires-correction { background: #fee4e2; color: var(--bad); }
.assessment-information-required { background: #fff3d6; color: #7a4b00; }
.assessment-pending-confirmation { background: #eaf0f8; color: var(--brand); }
.confidence { display: block; margin-top: 6px; color: var(--muted); font-size: 12px; }
.empty-comments { border: 1px dashed var(--line); border-radius: 8px; padding: 16px; background: #f8fafc; color: var(--muted); }
@media (max-width: 780px) {
  .layout, .row { grid-template-columns: 1fr; }
  main, .topbar { padding-left: 16px; padding-right: 16px; }
  .meta div { grid-template-columns: 1fr; gap: 4px; }
  .meta strong { text-align: left; }
  .comment-preview-header { display: block; }
}
</style>
"""


def _token_from_request() -> str:
    return (request.headers.get("X-IDC-Token") or "").strip()


def _require_token() -> None:
    header_ok = bool(ACCESS_TOKEN and hmac.compare_digest(_token_from_request(), ACCESS_TOKEN))
    if ACCESS_TOKEN and not (header_ok or session.get("idc_authenticated") is True):
        abort(403)


def _safe_token_query() -> str:
    return ""


@app.errorhandler(403)
def access_denied(error):
    if ACCESS_TOKEN and not request.headers.get("X-IDC-Token") and request.method == "GET":
        return redirect(url_for("login"))
    return error


def _csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def _require_csrf() -> None:
    expected = session.get("csrf_token", "")
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token") or ""
    if not expected or not hmac.compare_digest(str(expected), str(supplied)):
        abort(403, "Invalid CSRF token.")


@app.route("/login", methods=["GET", "POST"])
def login():
    if not ACCESS_TOKEN:
        session["idc_authenticated"] = True
        return redirect(url_for("index"))
    error = ""
    if request.method == "POST":
        if hmac.compare_digest(request.form.get("access_token", ""), ACCESS_TOKEN):
            session.clear()
            session["idc_authenticated"] = True
            _csrf_token()
            return redirect(url_for("index"))
        error = "Invalid access token."
    return render_template_string("""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>IDC Login</title>{{ css|safe }}</head><body><main><section class="panel"><h1>IDC Login</h1><p>{{ error }}</p><form method="post"><label>Access token</label><input name="access_token" type="password" required autocomplete="current-password"><div class="actions"><button type="submit">Sign in</button></div></form></section></main></body></html>""", css=BASE_CSS, error=error)


def _job_snapshot(job_id: str) -> dict[str, Any] | None:
    with jobs_lock:
        job = jobs.get(job_id)
        if job:
            return dict(job)
    return store.get_job(job_id)


def _update_job(job_id: str, **updates: Any) -> None:
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(updates)
            snapshot = dict(jobs[job_id])
        else:
            snapshot = None
    if snapshot:
        store.save_job(snapshot)


def _append_log(job_id: str, message: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id]["log"].append(f"[{stamp}] {message}")
            snapshot = dict(jobs[job_id])
        else:
            snapshot = None
    if snapshot:
        store.save_job(snapshot)


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
            provider=job["provider"],
            use_ocr=job["ocr_mode"] != "no-ocr",
        )
        force_ocr = job["ocr_mode"] == "force"
        success = checker.check(
            job["input_path"],
            job["struct_type"],
            str(REPORT_DIR),
            force_ocr=force_ocr,
            critic=job.get("critic", False),
            critic_provider=job.get("critic_provider") or None,
            jurisdiction=job.get("jurisdiction", "HK"),
            code_pack=job.get("code_pack", "auto"),
            code_as_of=job.get("code_as_of") or None,
            export_json=True,
            input_overrides=job.get("input_overrides") or None,
        )

        if success and checker.last_report_file and Path(checker.last_report_file).exists():
            if checker.last_review_run:
                store.save_run(checker.last_review_run)
            elapsed = round(time.time() - started, 1)
            structure = checker.last_review_run.submission_structure if checker.last_review_run else None
            _update_job(
                job_id,
                status="completed",
                report_path=checker.last_report_file,
                completed_at=datetime.now().isoformat(timespec="seconds"),
                elapsed_seconds=elapsed,
                review_run_id=checker.last_review_run.run_id if checker.last_review_run else "",
                json_path=checker.last_json_file or "",
                standard_package_path=checker.last_standard_package_file or "",
                calculation_pages=format_page_ranges(structure.calculation_pages) if structure else "None",
                drawing_pages=format_page_ranges(structure.drawing_pages) if structure else "None",
                supporting_pages=format_page_ranges(structure.supporting_pages) if structure else "None",
                uncertain_pages=format_page_ranges(structure.uncertain_pages) if structure else "None",
            )
            _append_log(job_id, f"Report completed in {elapsed} seconds.")
            _append_log(job_id, f"Output: {checker.last_report_file}")
            return

        _update_job(job_id, status="failed", completed_at=datetime.now().isoformat(timespec="seconds"))
        _append_log(job_id, "IDC processing failed. Check the API key, PDF readability, and OCR setup.")
    except Exception as exc:  # noqa: BLE001 - show operational errors to IT/user
        _update_job(job_id, status="failed", completed_at=datetime.now().isoformat(timespec="seconds"))
        _append_log(job_id, f"Error: {exc}")


def _run_qa_job(job_id: str) -> None:
    job = _job_snapshot(job_id)
    if not job:
        return

    started = time.time()
    _update_job(job_id, status="running", started_at=datetime.now().isoformat(timespec="seconds"))
    _append_log(job_id, "Server accepted the upload and started QA Records Batch Checker.")

    try:
        result = run_qa_batch(
            Path(job["input_dir"]),
            Path(job["output_dir"]),
            ocr_mode=job["ocr_mode"],
            model_name=job["model"] or None,
            provider=job["provider"],
            log_callback=lambda message: _append_log(job_id, message),
        )
        elapsed = round(time.time() - started, 1)
        _update_job(
            job_id,
            status="completed",
            report_path=result["package_path"],
            completed_at=datetime.now().isoformat(timespec="seconds"),
            elapsed_seconds=elapsed,
            qa_result=result,
        )
        _append_log(job_id, f"QA batch completed in {elapsed} seconds.")
        _append_log(job_id, f"Processed files: {result['processed']}; exceptions: {result['exceptions']}.")
    except Exception as exc:  # noqa: BLE001 - show operational errors to IT/user
        _update_job(job_id, status="failed", completed_at=datetime.now().isoformat(timespec="seconds"))
        _append_log(job_id, f"Error: {exc}")


@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "default_provider": API_PROVIDER,
        "api_key_configured": is_provider_configured(API_PROVIDER),
        "providers": {provider: is_provider_configured(provider) for provider in VALID_API_PROVIDERS},
        "tesseract_available": TESSERACT_AVAILABLE,
        "workers": MAX_WORKERS,
        "qa_records_checker": True,
    }


@app.get("/")
def index():
    _require_token()
    tesseract_label = "ready" if TESSERACT_AVAILABLE else "not detected"
    api_label = f"{get_provider_label(API_PROVIDER)} {'configured' if is_provider_configured(API_PROVIDER) else 'missing'}"
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
        <p style="color:#b42318;font-weight:700">The default API provider is not configured on the server. Ask IT to edit the project .env file before uploading.</p>
        {% endif %}
        <form action="{{ url_for('create_job') }}" method="post" enctype="multipart/form-data">
          <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
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
          <div class="row">
            <div><label for="jurisdiction">Jurisdiction</label><input id="jurisdiction" name="jurisdiction" value="HK" required></div>
            <div><label for="code_pack">Code selection</label><input id="code_pack" name="code_pack" value="auto" title="Use auto for report-declared codes, or enter a validated pack ID"></div>
          </div>
          <div class="row">
            <div><label for="code_as_of">Code basis date</label><input id="code_as_of" name="code_as_of" type="date"></div>
            <div><label for="reviewed_facts">Reviewed facts/evidence (JSON, optional)</label><input id="reviewed_facts" name="reviewed_facts" type="file" accept="application/json,.json"></div>
          </div>
          <label><input style="width:auto;min-height:auto" name="critic" type="checkbox" value="1"> Enable non-authoritative critic pass</label>
          <div class="row">
            <div>
              <label for="provider">API provider</label>
              <select id="provider" name="provider">
                {% for item in providers %}
                <option value="{{ item }}" {% if item == default_provider %}selected{% endif %}>{{ provider_labels[item] }}</option>
                {% endfor %}
              </select>
            </div>
            <div>
              <label for="model">Model override</label>
              <input id="model" name="model" type="text" placeholder="Use selected provider default">
            </div>
          </div>
          <div class="actions">
            <button type="submit">Upload and Start</button>
            <a class="button secondary" href="{{ url_for('qa_index') }}{{ token_query }}">QA Records Batch</a>
          </div>
        </form>
      </section>
      <aside class="panel">
        <h2>Server Settings</h2>
        <div class="meta">
          <div><span>Max upload</span><strong>{{ max_upload_mb }} MB</strong></div>
          <div><span>Workers</span><strong>{{ workers }}</strong></div>
          <div><span>Uploads</span><strong class="settings-path">{{ upload_dir }}</strong></div>
          <div><span>Reports</span><strong class="settings-path">{{ report_dir }}</strong></div>
        </div>
        <div class="profile-card" id="review-profile-card">
          <h3 id="profile-title">Review package</h3>
          <p id="profile-purpose"></p>
          <p><strong>Expected package</strong><br><span id="profile-package"></span></p>
          <strong style="font-size:13px">Review focus</strong>
          <ul id="profile-focus"></ul>
          <p class="note" style="margin-top:10px">Drawing pages are identified but are not assessed in v0.17.</p>
        </div>
      </aside>
    </div>
  </main>
  <script>
    const reviewProfiles = {{ review_profiles|tojson }};
    const reviewType = document.getElementById('struct_type');
    function renderProfile() {
      const profile = reviewProfiles[reviewType.value];
      document.getElementById('profile-title').textContent = profile.label + ' review mode';
      document.getElementById('profile-purpose').textContent = profile.purpose;
      document.getElementById('profile-package').textContent = profile.expected_package;
      document.getElementById('profile-focus').innerHTML = profile.review_focus.map(item => '<li>' + item + '</li>').join('');
    }
    reviewType.addEventListener('change', renderProfile);
    renderProfile();
  </script>
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
        api_ready=is_provider_configured(API_PROVIDER),
        default_provider=API_PROVIDER,
        providers=sorted(VALID_API_PROVIDERS),
        provider_labels={provider: get_provider_label(provider) for provider in VALID_API_PROVIDERS},
        token_query=_safe_token_query(),
        csrf_token=_csrf_token(),
        review_profiles={
            key: {
                "label": value.label,
                "purpose": value.purpose,
                "expected_package": value.expected_package,
                "review_focus": list(value.review_focus),
            }
            for key, value in REVIEW_PROFILES.items()
        },
    )


@app.get("/qa")
def qa_index():
    _require_token()
    tesseract_label = "ready" if TESSERACT_AVAILABLE else "not detected"
    api_label = f"{get_provider_label(API_PROVIDER)} {'configured' if is_provider_configured(API_PROVIDER) else 'missing'}"
    return render_template_string(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>QA Records Batch Checker</title>
  {{ css|safe }}
</head>
<body>
  <header>
    <div class="topbar">
      <div class="brand">QA Records Batch Checker</div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end">
        <div class="status-pill">API: {{ api_label }}</div>
        <div class="status-pill">OCR: {{ tesseract_label }}</div>
      </div>
    </div>
  </header>
  <main>
    <div class="layout">
      <section class="panel">
        <h1>Batch QA Register</h1>
        <p>Upload OP records, mill certificates, concrete cube tests, reinforcement tests, or a ZIP package. The server extracts fields into a CSV register and flags records that need review.</p>
        {% if not api_ready %}
        <p style="color:#b42318;font-weight:700">The default API provider is not configured on the server. Ask IT to edit the project .env file before uploading.</p>
        {% endif %}
        <form action="{{ url_for('create_qa_job') }}" method="post" enctype="multipart/form-data">
          <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
          <label for="qa_files">PDF or ZIP files</label>
          <input id="qa_files" name="qa_files" type="file" accept="application/pdf,.pdf,.zip" multiple required>
          <div class="row">
            <div>
              <label for="ocr_mode">OCR mode</label>
              <select id="ocr_mode" name="ocr_mode">
                <option value="auto">Auto detect</option>
                <option value="force">Force OCR</option>
                <option value="no-ocr">No OCR</option>
              </select>
            </div>
            <div>
              <label for="provider">API provider</label>
              <select id="provider" name="provider">
                {% for item in providers %}
                <option value="{{ item }}" {% if item == default_provider %}selected{% endif %}>{{ provider_labels[item] }}</option>
                {% endfor %}
              </select>
            </div>
          </div>
          <div class="row">
            <div>
              <label for="model">Model override</label>
              <input id="model" name="model" type="text" placeholder="Use selected provider default">
            </div>
          </div>
          <div class="actions">
            <button type="submit">Upload and Build Register</button>
            <a class="button secondary" href="/{{ token_query }}">IDC Review</a>
          </div>
        </form>
      </section>
      <aside class="panel">
        <h2>Output</h2>
        <p>The downloaded ZIP contains a QA register CSV, an exception CSV, raw JSON, and a short summary.</p>
        <div class="meta">
          <div><span>Accepted</span><strong>PDF / ZIP</strong></div>
          <div><span>Max upload</span><strong>{{ max_upload_mb }} MB</strong></div>
          <div><span>Workers</span><strong>{{ workers }}</strong></div>
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
        token_required=bool(ACCESS_TOKEN),
        tesseract_label=tesseract_label,
        api_label=api_label,
        api_ready=is_provider_configured(API_PROVIDER),
        default_provider=API_PROVIDER,
        providers=sorted(VALID_API_PROVIDERS),
        provider_labels={provider: get_provider_label(provider) for provider in VALID_API_PROVIDERS},
        token_query=_safe_token_query(),
        csrf_token=_csrf_token(),
    )


@app.post("/jobs")
def create_job():
    _require_token()
    _require_csrf()
    cleanup_expired_files([UPLOAD_DIR, REPORT_DIR])
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
    input_overrides = ""
    facts_upload = request.files.get("reviewed_facts")
    if facts_upload and facts_upload.filename:
        if not secure_filename(facts_upload.filename).lower().endswith(".json"):
            abort(400, "Reviewed facts must be JSON.")
        facts_path = job_dir / "reviewed_facts.json"
        facts_upload.save(facts_path)
        input_overrides = str(facts_path)
    struct_type = request.form.get("struct_type", "building")
    ocr_mode = request.form.get("ocr_mode", "auto")
    provider = request.form.get("provider", API_PROVIDER).strip().lower()
    if struct_type not in VALID_STRUCT_TYPES:
        abort(400, "Invalid review type.")
    if ocr_mode not in VALID_OCR_MODES:
        abort(400, "Invalid OCR mode.")
    if provider not in VALID_API_PROVIDERS:
        abort(400, "Invalid API provider.")

    job = {
        "id": job_id,
        "filename": filename,
        "input_path": str(input_path),
        "struct_type": struct_type,
        "ocr_mode": ocr_mode,
        "provider": provider,
        "model": request.form.get("model", "").strip(),
        "jurisdiction": request.form.get("jurisdiction", "HK").strip().upper(),
        "code_pack": request.form.get("code_pack", "auto").strip(),
        "code_as_of": request.form.get("code_as_of", "").strip(),
        "critic": request.form.get("critic") == "1",
        "critic_provider": request.form.get("critic_provider", "").strip().lower(),
        "input_overrides": input_overrides,
        "status": "queued",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "started_at": "",
        "completed_at": "",
        "elapsed_seconds": "",
        "report_path": "",
        "standard_package_path": "",
        "calculation_pages": "",
        "drawing_pages": "",
        "supporting_pages": "",
        "uncertain_pages": "",
        "log": ["Upload received. Waiting for worker."],
    }
    with jobs_lock:
        jobs[job_id] = job
    store.save_job(job)

    executor.submit(_run_job, job_id)
    return redirect(url_for("job_status", job_id=job_id) + _safe_token_query())


@app.post("/qa/jobs")
def create_qa_job():
    _require_token()
    _require_csrf()
    cleanup_expired_files([UPLOAD_DIR, REPORT_DIR])
    uploads = [file for file in request.files.getlist("qa_files") if file and file.filename]
    if not uploads:
        abort(400, "No QA files uploaded.")

    job_id = uuid.uuid4().hex[:12]
    input_dir = UPLOAD_DIR / f"qa_{job_id}"
    output_dir = REPORT_DIR / f"qa_{job_id}"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[str] = []
    for upload in uploads:
        filename = secure_filename(upload.filename)
        if not filename:
            continue
        suffix = Path(filename).suffix.lower()
        if suffix not in VALID_QA_EXTENSIONS:
            abort(400, "Only PDF and ZIP uploads are supported for QA records.")
        target = input_dir / filename
        upload.save(target)
        saved_files.append(filename)

    if not saved_files:
        abort(400, "No valid QA files uploaded.")

    ocr_mode = request.form.get("ocr_mode", "auto")
    provider = request.form.get("provider", API_PROVIDER).strip().lower()
    if ocr_mode not in VALID_OCR_MODES:
        abort(400, "Invalid OCR mode.")
    if provider not in VALID_API_PROVIDERS:
        abort(400, "Invalid API provider.")

    job = {
        "id": job_id,
        "kind": "qa",
        "filename": f"{len(saved_files)} QA upload(s)",
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "saved_files": saved_files,
        "ocr_mode": ocr_mode,
        "provider": provider,
        "model": request.form.get("model", "").strip(),
        "status": "queued",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "started_at": "",
        "completed_at": "",
        "elapsed_seconds": "",
        "report_path": "",
        "qa_result": {},
        "log": ["QA uploads received. Waiting for worker."],
    }
    with jobs_lock:
        jobs[job_id] = job
    store.save_job(job)

    executor.submit(_run_qa_job, job_id)
    return redirect(url_for("qa_job_status", job_id=job_id) + _safe_token_query())


@app.get("/qa/jobs/<job_id>")
def qa_job_status(job_id: str):
    _require_token()
    job = _job_snapshot(job_id)
    if not job or job.get("kind") != "qa":
        abort(404)

    token_query = _safe_token_query()
    download_url = url_for("download_report", job_id=job_id) + token_query if job.get("report_path") else ""
    refresh_tag = "" if job["status"] in {"completed", "failed"} else '<meta http-equiv="refresh" content="5">'
    qa_result = job.get("qa_result") or {}
    return render_template_string(
        """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {{ refresh_tag|safe }}
  <title>QA Job {{ job.id }}</title>
  {{ css|safe }}
</head>
<body>
  <header>
    <div class="topbar">
      <div class="brand">QA Records Batch Checker</div>
      <div class="status-pill">Job {{ job.id }}</div>
    </div>
  </header>
  <main>
    <section class="panel">
      <h1>{{ job.filename }}</h1>
      <p>Status: <span class="status {{ job.status }}">{{ job.status|upper }}</span></p>
      <div class="meta">
        <div><span>OCR mode</span><strong>{{ job.ocr_mode }}</strong></div>
        <div><span>API provider</span><strong>{{ provider_label }}</strong></div>
        <div><span>Model</span><strong>{{ job.model or default_model }}</strong></div>
        <div><span>Uploaded files</span><strong>{{ job.saved_files|length }}</strong></div>
        <div><span>Processed records</span><strong>{{ qa_result.get("processed", "-") }}</strong></div>
        <div><span>Exceptions</span><strong>{{ qa_result.get("exceptions", "-") }}</strong></div>
        <div><span>Created</span><strong>{{ job.created_at }}</strong></div>
        <div><span>Completed</span><strong>{{ job.completed_at or "-" }}</strong></div>
      </div>
      <div class="actions">
        <a class="button secondary" href="{{ url_for('qa_index') }}{{ token_query }}">New QA Batch</a>
        {% if download_url %}
        <a class="button" href="{{ download_url }}">Download QA Output ZIP</a>
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
        qa_result=qa_result,
        log_text="\n".join(job["log"]),
        download_url=download_url,
        token_query=token_query,
        provider_label=get_provider_label(job.get("provider")),
        default_model=get_default_model(job.get("provider")),
        refresh_tag=refresh_tag,
    )


def _comment_preview(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Prepare the same actionable comment set shown in the human Word report."""
    actionable = {"REQUIRES_CORRECTION", "INFORMATION_REQUIRED", "PENDING_CONFIRMATION"}
    preview: list[dict[str, Any]] = []
    for raw in (payload or {}).get("comments", []):
        assessment = str(raw.get("assessment", "")).upper()
        if assessment not in actionable:
            continue
        try:
            confidence = min(1.0, max(0.0, float(raw.get("confidence", 0.0))))
        except (TypeError, ValueError):
            confidence = 0.0
        item = dict(raw)
        item["assessment"] = assessment
        item["assessment_label"] = assessment.replace("_", " ").title()
        item["assessment_class"] = assessment.lower().replace("_", "-")
        item["confidence_label"] = "High" if confidence >= 0.8 else "Medium" if confidence >= 0.5 else "Low"
        item["confidence_percent"] = round(confidence * 100)
        preview.append(item)
    return preview


@app.get("/jobs/<job_id>")
def job_status(job_id: str):
    _require_token()
    job = _job_snapshot(job_id)
    if not job:
        abort(404)

    token_query = _safe_token_query()
    download_url = url_for("download_report", job_id=job_id) + token_query if job.get("report_path") else ""
    package_url = url_for("download_standard_package", job_id=job_id) + token_query if job.get("standard_package_path") else ""
    review_payload = store.get_payload(job["review_run_id"]) if job.get("review_run_id") else None
    preview_comments = _comment_preview(review_payload)
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
  <main class="result-main">
    <section class="panel">
      <h1>{{ job.filename }}</h1>
      <p>Status: <span class="status {{ job.status }}">{{ job.status|upper }}</span></p>
      <div class="meta">
        <div><span>Review type</span><strong>{{ job.struct_type }}</strong></div>
        <div><span>OCR mode</span><strong>{{ job.ocr_mode }}</strong></div>
        <div><span>API provider</span><strong>{{ provider_label }}</strong></div>
        <div><span>Model</span><strong>{{ job.model or default_model }}</strong></div>
        <div><span>Calculation pages reviewed</span><strong>{{ job.calculation_pages or "-" }}</strong></div>
        <div><span>Supporting pages used</span><strong>{{ job.supporting_pages or "-" }}</strong></div>
        <div><span>Drawing pages (not assessed)</span><strong>{{ job.drawing_pages or "-" }}</strong></div>
        <div><span>Pages needing confirmation</span><strong>{{ job.uncertain_pages or "-" }}</strong></div>
        <div><span>Created</span><strong>{{ job.created_at }}</strong></div>
        <div><span>Started</span><strong>{{ job.started_at or "-" }}</strong></div>
        <div><span>Completed</span><strong>{{ job.completed_at or "-" }}</strong></div>
      </div>
      {% if job.review_run_id %}
      <div class="comment-preview">
        <div class="comment-preview-header">
          <div>
            <h2>IDC Review Comments</h2>
            <p>Review the actionable comments below before downloading the formal Word report.</p>
          </div>
          <span class="status-pill">{{ preview_comments|length }} actionable</span>
        </div>
        {% if preview_comments %}
        <div class="comment-table-wrap" role="region" aria-label="IDC review comments" tabindex="0">
          <table class="comment-table">
            <colgroup>
              <col style="width:6%"><col style="width:16%"><col style="width:22%"><col style="width:30%"><col style="width:26%">
            </colgroup>
            <thead><tr>
              <th>No.</th><th>Where</th><th>Submitted content / issue</th><th>Basis and IDC comment</th><th>Required action / assessment / confidence</th>
            </tr></thead>
            <tbody>
            {% for comment in preview_comments %}
              <tr>
                <td class="comment-no">{{ comment.comment_no }}</td>
                <td>{{ comment.location or "Location not confirmed" }}</td>
                <td>{{ comment.submitted_content or "—" }}</td>
                <td>
                  {{ comment.basis_and_comment or "—" }}
                  {% if comment.note %}<div class="comment-note"><strong>Note:</strong> {{ comment.note }}</div>{% endif %}
                </td>
                <td>
                  {{ comment.required_action or "Provide clarification for review." }}<br>
                  <span class="assessment assessment-{{ comment.assessment_class }}">{{ comment.assessment_label }}</span>
                  <span class="confidence">Evidence confidence: {{ comment.confidence_label }} ({{ comment.confidence_percent }}%)</span>
                </td>
              </tr>
            {% endfor %}
            </tbody>
          </table>
        </div>
        {% else %}
        <div class="empty-comments">No actionable or pending comments were produced for this review run.</div>
        {% endif %}
        <p class="note" style="margin-top:10px">Confidence describes the reliability of the available evidence; it is not a structural safety rating.</p>
      </div>
      {% endif %}
      <div class="actions">
        <a class="button secondary" href="/{{ token_query }}">New Upload</a>
        {% if download_url %}
        <a class="button" href="{{ download_url }}">Download Word Report</a>
        {% endif %}
        {% if package_url %}
        <a class="button secondary" href="{{ package_url }}">Download Standard Package</a>
        {% endif %}
        {% if job.review_run_id %}
        <a class="button secondary" href="{{ url_for('structured_results', job_id=job.id) }}">Download Structured JSON</a>
        {% endif %}
      </div>
      {% if job.review_run_id %}
      <form action="{{ url_for('review_decision', job_id=job.id) }}" method="post" style="margin-top:20px">
        <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
        <h2>Signed Reviewer Decision</h2>
        <div class="row"><div><label>Reviewer name</label><input name="reviewer" required></div><div><label>Decision</label><select name="decision"><option>APPROVED</option><option>REJECTED</option></select></div></div>
        <label>Reason</label><input name="reason" required>
        <div class="actions"><button type="submit">Record decision</button></div>
      </form>
      {% endif %}
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
        package_url=package_url,
        preview_comments=preview_comments,
        token_query=token_query,
        provider_label=get_provider_label(job.get("provider")),
        default_model=get_default_model(job.get("provider")),
        refresh_tag=refresh_tag,
        csrf_token=_csrf_token(),
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


@app.get("/jobs/<job_id>/standard-package")
def download_standard_package(job_id: str):
    _require_token()
    job = _job_snapshot(job_id)
    if not job or not job.get("standard_package_path"):
        abort(404)
    package_path = Path(job["standard_package_path"]).resolve()
    if not package_path.is_file() or REPORT_DIR not in package_path.parents or package_path.suffix.lower() != ".zip":
        abort(404)
    return send_file(package_path, as_attachment=True)


@app.get("/jobs/<job_id>/results.json")
def structured_results(job_id: str):
    _require_token()
    job = _job_snapshot(job_id)
    if not job or not job.get("review_run_id"):
        abort(404)
    payload = store.get_payload(job["review_run_id"])
    if payload is None:
        abort(404)
    response = jsonify(payload)
    response.headers["Content-Disposition"] = f'attachment; filename="{job_id}_review.json"'
    return response


@app.post("/jobs/<job_id>/facts/<path:fact_id>")
def edit_fact(job_id: str, fact_id: str):
    _require_token()
    _require_csrf()
    job = _job_snapshot(job_id)
    if not job or not job.get("review_run_id"):
        abort(404)
    payload = request.get_json(silent=True) or request.form
    try:
        evidence = payload.get("evidence", [])
        if isinstance(evidence, str):
            import json
            evidence = json.loads(evidence)
        store.edit_fact(job["review_run_id"], fact_id, payload.get("value"), evidence=evidence, reviewer=payload.get("reviewer", ""), reason=payload.get("reason", ""))
    except (ValueError, KeyError) as exc:
        abort(400, str(exc))
    return jsonify({"ok": True, "run_id": job["review_run_id"], "fact_id": fact_id, "results_invalidated": True})


@app.post("/jobs/<job_id>/decision")
def review_decision(job_id: str):
    _require_token()
    _require_csrf()
    job = _job_snapshot(job_id)
    if not job or not job.get("review_run_id"):
        abort(404)
    payload = request.get_json(silent=True) or request.form
    try:
        store.decide(job["review_run_id"], payload.get("decision", ""), reviewer=payload.get("reviewer", ""), reason=payload.get("reason", ""))
    except (ValueError, KeyError) as exc:
        abort(400, str(exc))
    if request.is_json:
        return jsonify({"ok": True, "decision": payload.get("decision", "").upper()})
    return redirect(url_for("job_status", job_id=job_id))


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
