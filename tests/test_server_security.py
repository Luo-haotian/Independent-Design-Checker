from __future__ import annotations

import server.idc_server as web


def test_query_token_is_not_accepted_or_redirected(monkeypatch):
    monkeypatch.setattr(web, "ACCESS_TOKEN", "secret-token")
    web.app.config.update(TESTING=True)
    client = web.app.test_client()
    response = client.get("/?token=secret-token")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert "secret-token" not in response.headers["Location"]


def test_login_uses_session_and_post_requires_csrf(monkeypatch):
    monkeypatch.setattr(web, "ACCESS_TOKEN", "secret-token")
    web.app.config.update(TESTING=True)
    client = web.app.test_client()
    login = client.post("/login", data={"access_token": "secret-token"})
    assert login.status_code == 302
    assert "secret-token" not in login.headers["Location"]
    forbidden = client.post("/jobs", data={})
    assert forbidden.status_code == 403


def test_server_home_explains_review_profiles(monkeypatch):
    monkeypatch.setattr(web, "ACCESS_TOKEN", "")
    web.app.config.update(TESTING=True)
    response = web.app.test_client().get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Building review mode" in html or "reviewProfiles" in html
    assert "Temporary works calculation and operational constraint review" in html
    assert "Drawing pages are identified but are not assessed in v0.17" in html
    assert 'class="settings-path"' in html
    assert "overflow-wrap: anywhere" in html


def test_completed_job_shows_actionable_comment_table_before_word_download(monkeypatch):
    monkeypatch.setattr(web, "ACCESS_TOKEN", "")
    monkeypatch.setattr(
        web.store,
        "get_payload",
        lambda _run_id: {
            "comments": [
                {
                    "comment_no": 1,
                    "location": "PDF p.4 — beam design",
                    "submitted_content": "Concrete beam capacity equation",
                    "basis_and_comment": "The applicable design code and clause are not stated.",
                    "required_action": "Identify the code, edition, and clause.",
                    "assessment": "INFORMATION_REQUIRED",
                    "confidence": 0.86,
                    "note": "Confirm before closing the review.",
                },
                {
                    "comment_no": 2,
                    "location": "PDF p.5",
                    "submitted_content": "Verified item that should stay out of the preview",
                    "basis_and_comment": "Verified.",
                    "required_action": "None.",
                    "assessment": "ACCEPTABLE",
                    "confidence": 0.95,
                },
            ]
        },
    )
    job = {
        "id": "preview-job",
        "filename": "submission.pdf",
        "status": "completed",
        "struct_type": "building",
        "ocr_mode": "auto",
        "provider": "grok",
        "model": "",
        "calculation_pages": "2–9",
        "supporting_pages": "11–12",
        "drawing_pages": "10",
        "uncertain_pages": "-",
        "created_at": "2026-08-12T10:00:00Z",
        "started_at": "2026-08-12T10:00:01Z",
        "completed_at": "2026-08-12T10:01:00Z",
        "report_path": "C:/reports/result.docx",
        "standard_package_path": "C:/reports/result.zip",
        "review_run_id": "run-preview",
        "log": ["Completed"],
    }
    with web.jobs_lock:
        web.jobs[job["id"]] = job
    web.app.config.update(TESTING=True)
    response = web.app.test_client().get(f"/jobs/{job['id']}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "IDC Review Comments" in html
    assert "PDF p.4 — beam design" in html
    assert "Evidence confidence: High (86%)" in html
    assert "Verified item that should stay out of the preview" not in html
    assert html.index("IDC Review Comments") < html.index("Download Word Report")


def test_standard_package_download_is_confined_to_report_directory(monkeypatch, tmp_path):
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    package = report_dir / "standard.zip"
    package.write_bytes(b"PK\x05\x06" + b"\x00" * 18)
    monkeypatch.setattr(web, "ACCESS_TOKEN", "")
    monkeypatch.setattr(web, "REPORT_DIR", report_dir.resolve())
    web.app.config.update(TESTING=True)
    with web.jobs_lock:
        web.jobs["safejob"] = {"id": "safejob", "standard_package_path": str(package)}
        web.jobs["unsafejob"] = {"id": "unsafejob", "standard_package_path": str(tmp_path / "outside.zip")}
    (tmp_path / "outside.zip").write_bytes(package.read_bytes())
    client = web.app.test_client()
    assert client.get("/jobs/safejob/standard-package").status_code == 200
    assert client.get("/jobs/unsafejob/standard-package").status_code == 404
