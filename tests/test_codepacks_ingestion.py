from __future__ import annotations

import json

import pymupdf as fitz
import pytest

from idc.code_basis import detect_code_declarations, resolve_code_basis
from idc.codepacks import DEFAULT_CODE_PACK_ID, HK_CONCRETE_PACK_ID, load_code_pack
from idc.ingestion import build_page_chunks, coverage_from_chunks, ingest_pdf


def test_hk_default_is_general_report_declared_profile():
    pack = load_code_pack()
    assert pack.jurisdiction == "HK"
    assert pack.id == DEFAULT_CODE_PACK_ID
    assert pack.id != HK_CONCRETE_PACK_ID
    assert pack.rules["rules"] == {}
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


def test_mixed_report_codes_are_preserved_in_order():
    text = "Design to BS 8110:1997, Code of Practice on Wind Effects in Hong Kong 2019 and GB 50009-2012."
    declarations = detect_code_declarations(text)
    assert [item["canonical_name"] for item in declarations] == ["BS 8110", "HK Code of Practice on Wind Effects 2019", "GB 50009"]


def test_other_hk_and_international_codes_are_not_lost():
    text = "Code of Practice for Fire Safety in Buildings 2011 (2024 Edition), ACI 318 and AS/NZS 1170.2"
    names = [item["canonical_name"] for item in detect_code_declarations(text)]
    assert names == ["Code of Practice for Fire Safety in Buildings 2011 (2024 Edition)", "ACI 318", "AS/NZS 1170.2"]


def test_mixed_concrete_codes_do_not_silently_choose_hk(tmp_path):
    path = tmp_path / "mixed.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Code of Practice for Structural Use of Concrete 2013 (2020 Edition) and BS 8110:1997")
    document.save(path)
    document.close()
    basis, engine = resolve_code_basis(ingest_pdf(path))
    assert engine is None
    assert len(basis.declared_codes) == 2
    assert "Multiple concrete design bases" in basis.unresolved_codes[0]


def test_single_report_declared_hk_concrete_enables_implemented_adapter(tmp_path):
    path = tmp_path / "hk.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Code of Practice for Structural Use of Concrete 2013 (2020 Edition)")
    document.save(path)
    document.close()
    basis, engine = resolve_code_basis(ingest_pdf(path))
    assert engine and engine.id == HK_CONCRETE_PACK_ID
    assert basis.code_pack_id == DEFAULT_CODE_PACK_ID
    assert basis.deterministic_rule_pack_id == HK_CONCRETE_PACK_ID


def test_non_hk_auto_basis_preserves_report_code_without_hk_fallback(tmp_path):
    path = tmp_path / "gb.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Concrete design code GB 50010-2010")
    document.save(path)
    document.close()
    basis, engine = resolve_code_basis(ingest_pdf(path), jurisdiction="GB")
    assert basis.jurisdiction == "GB"
    assert basis.code_pack_id == "report-declared-generic"
    assert basis.declared_codes == ["GB 50010"]
    assert engine is None
