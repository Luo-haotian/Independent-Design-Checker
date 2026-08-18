from __future__ import annotations

import os
import time
import zipfile
from pathlib import Path

import pytest

from idc.codepacks import load_code_pack
from idc.models import ExtractedFact, ReviewRun, ReviewStatus, SourceEvidence
from idc.persistence import ReviewStore
from idc.retention import cleanup_expired_files
from qa_records import collect_pdf_inputs


def sample_run():
    return ReviewRun("run1", "sanitized.pdf", "a" * 64, load_code_pack().code_basis(), status=ReviewStatus.READY_FOR_REVIEW, facts=[ExtractedFact("B1:width_mm", "width_mm", 300, "mm", [SourceEvidence("sanitized.pdf", 1)])])


def test_restart_persistence_and_signed_audit(tmp_path):
    path = tmp_path / "reviews.sqlite3"
    ReviewStore(path).save_run(sample_run())
    restarted = ReviewStore(path)
    assert restarted.get_payload("run1")["source_sha256"] == "a" * 64
    restarted.edit_fact("run1", "B1:width_mm", 310, evidence=[{"source_file": "sanitized.pdf", "page": 2}], reviewer="A Reviewer", reason="Confirmed revision")
    payload = restarted.get_payload("run1")
    assert payload["status"] == "DRAFT"
    assert payload["facts"][0]["value"] == 310
    assert payload["checks"] == []
    with pytest.raises(ValueError, match="rerun checks"):
        restarted.decide("run1", "APPROVED", reviewer="A Reviewer", reason="Reviewed evidence")
    assert len(payload["audit_events"]) == 1


def test_job_restart_persistence(tmp_path):
    path = tmp_path / "reviews.sqlite3"
    ReviewStore(path).save_job({"id": "job1", "status": "queued", "log": []})
    assert ReviewStore(path).get_job("job1")["status"] == "queued"


def test_signed_decision_for_ready_run(tmp_path):
    store = ReviewStore(tmp_path / "reviews.sqlite3")
    store.save_run(sample_run())
    store.decide("run1", "APPROVED", reviewer="A Reviewer", reason="Reviewed evidence")
    assert store.get_payload("run1")["status"] == "APPROVED"


@pytest.mark.parametrize("reviewer,reason", [("", "because"), ("A", "")])
def test_unsigned_decision_rejected(tmp_path, reviewer, reason):
    store = ReviewStore(tmp_path / "db.sqlite3")
    store.save_run(sample_run())
    with pytest.raises(ValueError):
        store.decide("run1", "APPROVED", reviewer=reviewer, reason=reason)


def test_retention_removes_raw_file_but_not_database(tmp_path):
    raw = tmp_path / "uploads"
    raw.mkdir()
    old = raw / "old.pdf"
    old.write_bytes(b"old")
    timestamp = time.time() - 31 * 86400
    os.utime(old, (timestamp, timestamp))
    db = tmp_path / "reviews.sqlite3"
    db.write_bytes(b"audit")
    removed = cleanup_expired_files([raw], 30)
    assert old in removed and not old.exists() and db.exists()


def write_zip(path: Path, members: list[tuple[str, bytes]]):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in members:
            archive.writestr(name, content)


def test_zip_paths_are_flattened(tmp_path):
    inputs, work = tmp_path / "in", tmp_path / "work"
    inputs.mkdir()
    work.mkdir()
    write_zip(inputs / "batch.zip", [("../../sample.pdf", b"%PDF-sanitized")])
    result = collect_pdf_inputs(inputs, work)
    assert result[0].parent == (work / "extracted").resolve()


def test_duplicate_archive_names_rejected(tmp_path):
    inputs, work = tmp_path / "in", tmp_path / "work"
    inputs.mkdir()
    work.mkdir()
    write_zip(inputs / "batch.zip", [("a/sample.pdf", b"1"), ("b/sample.pdf", b"2")])
    with pytest.raises(ValueError, match="Duplicate"):
        collect_pdf_inputs(inputs, work)


def test_zip_bomb_ratio_rejected(tmp_path, monkeypatch):
    inputs, work = tmp_path / "in", tmp_path / "work"
    inputs.mkdir()
    work.mkdir()
    monkeypatch.setenv("IDC_ZIP_MAX_RATIO", "2")
    write_zip(inputs / "batch.zip", [("sample.pdf", b"A" * 10000)])
    with pytest.raises(ValueError, match="ratio"):
        collect_pdf_inputs(inputs, work)
