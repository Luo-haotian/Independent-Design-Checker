from __future__ import annotations

import json

import fitz
import pytest

from idc.codepacks import load_code_pack
from idc.ingestion import build_page_chunks, coverage_from_chunks, ingest_pdf


def test_hk_is_default_and_not_engineering_approved():
    pack = load_code_pack()
    assert pack.jurisdiction == "HK"
    assert pack.code_basis().engineering_approved is False


def test_no_jurisdiction_fallback():
    with pytest.raises(ValueError):
        load_code_pack(jurisdiction="US")


def test_code_pack_path_traversal_is_rejected():
    with pytest.raises(ValueError, match="Invalid code-pack ID"):
        load_code_pack("../hk-bd-concrete-2020-amd-2024-04")


def test_custom_non_hk_pack_loads_exactly(tmp_path):
    root = tmp_path / "packs"
    folder = root / "us-test"
    folder.mkdir(parents=True)
    manifest = {
        "id": "us-test", "jurisdiction": "US", "authority": "Test Authority", "title": "Sanitized",
        "edition": "1", "amendments": [], "effective_from": "2020-01-01", "rule_set_version": "1",
        "sources": [], "supported_rule_ids": ["TEST-1"],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (folder / "rules.json").write_text(json.dumps({"rules": {"TEST-1": {}}}), encoding="utf-8")
    assert load_code_pack("us-test", jurisdiction="US", extra_roots=[root]).id == "us-test"
    with pytest.raises(ValueError):
        load_code_pack("us-test", jurisdiction="HK", extra_roots=[root])


def test_page_coverage_is_complete(tmp_path):
    path = tmp_path / "three-pages.pdf"
    document = fitz.open()
    for index in range(1, 4):
        page = document.new_page()
        page.insert_text((72, 72), f"Sanitized evidence page {index} " * 20)
    document.save(path)
    document.close()
    extracted = ingest_pdf(path)
    chunks = build_page_chunks(extracted, max_chars=1100)
    covered, missing = coverage_from_chunks(extracted, chunks)
    assert covered == [1, 2, 3]
    assert missing == []
    assert all(chunk.page_numbers for chunk in chunks)
