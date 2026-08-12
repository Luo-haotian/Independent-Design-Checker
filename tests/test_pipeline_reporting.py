from __future__ import annotations

import json
from pathlib import Path

import pymupdf as fitz

from idc.ingestion import ingest_pdf
from idc.pipeline import create_review_run, deterministic_summary, export_review_json
from report_generator import generate_report_docx


def make_inputs(path: Path):
    values = {
        "span_mm": 6000, "width_mm": 300, "overall_depth_mm": 550, "effective_depth_mm": 500,
        "concrete_strength_mpa": 40, "steel_strength_mpa": 500, "link_strength_mpa": 500,
        "design_moment_knm": 250, "design_shear_kn": 160, "tension_steel_mm2": 1800,
        "design_action_basis": "ULS", "link_area_mm2": 201, "link_spacing_mm": 200,
        "section_type": "rectangular", "prestressed": False, "axial_force_kn": 0, "torsion_knm": 0,
    }
    evidence = {name: [{"source_file": "sanitized.pdf", "page": 1, "quote": name}] for name in values}
    path.write_text(json.dumps({"beam_id": "B1", **values, "evidence": evidence}), encoding="utf-8")


def test_json_and_word_contain_same_deterministic_record(tmp_path):
    pdf = tmp_path / "sanitized.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Sanitized beam B1 evidence. Code of Practice for Structural Use of Concrete 2013 (2020 Edition).")
    document.save(pdf)
    document.close()
    inputs = tmp_path / "facts.json"
    make_inputs(inputs)
    run = create_review_run(ingest_pdf(pdf), input_overrides=inputs)
    json_path = export_review_json(run, tmp_path / "review.json")
    summary = deterministic_summary(run)
    docx = tmp_path / "review.docx"
    generate_report_docx(summary + "# AI Observations\n\nMocked observation.", str(pdf), "building", str(docx), "mock", "grok")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["checks"]
    assert "HK-RC-BEAM-FLX-001" in summary
    assert docx.is_file() and docx.stat().st_size > 0


def test_no_overrides_produces_no_false_pass(tmp_path):
    pdf = tmp_path / "sanitized.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "No reviewed structural facts")
    document.save(pdf)
    document.close()
    run = create_review_run(ingest_pdf(pdf))
    assert run.checks == []
    assert "No deterministic PASS or FAIL was produced" in deterministic_summary(run)


def test_generic_reviewed_facts_are_preserved_without_member_adapter(tmp_path):
    pdf = tmp_path / "sanitized.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Design basis includes Code of Practice on Wind Effects in Hong Kong 2019")
    document.save(pdf)
    document.close()
    facts = tmp_path / "facts.json"
    facts.write_text(
        json.dumps(
            {
                "facts": [
                    {
                        "name": "wind_code",
                        "value": "HK Wind Code 2019",
                        "evidence": [{"source_file": "sanitized.pdf", "page": 1}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    run = create_review_run(ingest_pdf(pdf), input_overrides=facts)
    assert run.facts[0].name == "wind_code"
    assert run.checks[0].status.value == "OUT_OF_SCOPE"
    assert not any(item.status.value in {"PASS", "FAIL"} for item in run.checks)


def test_bs_report_does_not_fall_back_to_hk_concrete_rules(tmp_path):
    pdf = tmp_path / "bs.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Concrete design is based on BS 8110:1997")
    document.save(pdf)
    document.close()
    inputs = tmp_path / "facts.json"
    make_inputs(inputs)
    run = create_review_run(ingest_pdf(pdf), input_overrides=inputs)
    assert "BS 8110" in run.code_basis.declared_codes
    assert run.code_basis.deterministic_rule_pack_id is None
    assert [item.rule_id for item in run.checks] == ["IDC-CODE-BASIS-001"]
