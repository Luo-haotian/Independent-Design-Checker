from __future__ import annotations

import json

import pytest

from idc.beam_checks import BeamCheckInput, load_beam_inputs, run_beam_checks
from idc.codepacks import load_code_pack
from idc.models import CheckStatus, SourceEvidence

BASE = {
    "span_mm": 6000, "width_mm": 300, "overall_depth_mm": 550, "effective_depth_mm": 500,
    "concrete_strength_mpa": 40, "steel_strength_mpa": 500, "link_strength_mpa": 500,
    "design_moment_knm": 250, "design_shear_kn": 160, "tension_steel_mm2": 1800,
    "design_action_basis": "ULS", "link_area_mm2": 201, "link_spacing_mm": 200,
    "section_type": "rectangular", "prestressed": False, "axial_force_kn": 0, "torsion_knm": 0,
}


def beam(**changes):
    values = {**BASE, **changes}
    evidence = {name: [SourceEvidence("sanitized.pdf", 1, name, "manual", 1.0)] for name in BASE}
    return BeamCheckInput("B1", "sanitized.pdf", evidence=evidence, **values)


def status(result, rule_id):
    return next(item.status for item in result if item.rule_id == rule_id)


def test_golden_flexure_and_shear_pass():
    result = run_beam_checks(beam(), load_code_pack())
    assert status(result, "HK-RC-BEAM-FLX-001") == CheckStatus.PASS
    assert status(result, "HK-RC-BEAM-SHR-001B") == CheckStatus.PASS


def test_flexure_fail_for_low_steel():
    result = run_beam_checks(beam(tension_steel_mm2=900), load_code_pack())
    assert status(result, "HK-RC-BEAM-FLX-001") == CheckStatus.FAIL


def test_shear_fail_for_links_and_spacing():
    result = run_beam_checks(beam(link_area_mm2=100, link_spacing_mm=400), load_code_pack())
    assert status(result, "HK-RC-BEAM-SHR-001B") == CheckStatus.FAIL


def test_missing_effective_depth_is_insufficient_evidence():
    result = run_beam_checks(beam(effective_depth_mm=None), load_code_pack())
    assert status(result, "IDC-EVIDENCE-FLEXURE-001") == CheckStatus.INSUFFICIENT_EVIDENCE


def test_conflict_cannot_pass():
    item = beam()
    item.conflict_fields.add("design_moment_knm")
    assert status(run_beam_checks(item, load_code_pack()), "IDC-EVIDENCE-FLEXURE-001") == CheckStatus.CONFLICT


def test_deep_beam_is_out_of_scope():
    result = run_beam_checks(beam(span_mm=1000), load_code_pack())
    assert result[0].status == CheckStatus.OUT_OF_SCOPE


def test_scope_defaults_cannot_pass_without_evidence():
    item = beam()
    item.evidence.pop("section_type")
    assert run_beam_checks(item, load_code_pack())[0].status == CheckStatus.INSUFFICIENT_EVIDENCE


def test_service_actions_cannot_be_used_as_design_actions():
    result = run_beam_checks(beam(design_action_basis="SLS"), load_code_pack())
    assert status(result, "IDC-EVIDENCE-FLEXURE-001") == CheckStatus.INSUFFICIENT_EVIDENCE


def test_boundary_spacing_passes():
    assert status(run_beam_checks(beam(link_spacing_mm=300), load_code_pack()), "HK-RC-BEAM-SHR-001B") == CheckStatus.PASS


def test_list_input_loader(tmp_path):
    path = tmp_path / "beams.json"
    record = {"beam_id": "B1", **BASE, "evidence": {name: [{"page": 1}] for name in BASE}}
    path.write_text(json.dumps([record]), encoding="utf-8")
    assert load_beam_inputs(path, "sanitized.pdf")[0].beam_id == "B1"


def test_input_unit_conversion(tmp_path):
    path = tmp_path / "beams.json"
    record = {"beam_id": "B1", **BASE, "width_mm": 0.3, "units": {"width_mm": "m"}, "evidence": {name: [{"page": 1}] for name in BASE}}
    path.write_text(json.dumps(record), encoding="utf-8")
    assert load_beam_inputs(path, "sanitized.pdf")[0].width_mm == pytest.approx(300)


def test_invalid_positive_input_is_error():
    assert status(run_beam_checks(beam(width_mm=0), load_code_pack()), "IDC-EVIDENCE-FLEXURE-001") == CheckStatus.ERROR


def test_invalid_evidence_page_is_rejected(tmp_path):
    path = tmp_path / "beams.json"
    record = {"beam_id": "B1", **BASE, "evidence": {name: [{"page": 0}] for name in BASE}}
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="positive integer"):
        load_beam_inputs(path, "sanitized.pdf")
