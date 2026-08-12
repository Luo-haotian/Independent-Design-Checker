"""Deterministic Hong Kong reinforced-concrete beam checks."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .codepacks import CodePack
from .evidence import evidence_gate
from .models import CheckResult, CheckStatus, ExtractedFact, SourceEvidence


@dataclass(slots=True)
class BeamCheckInput:
    beam_id: str
    source_file: str
    span_mm: float | None = None
    width_mm: float | None = None
    overall_depth_mm: float | None = None
    effective_depth_mm: float | None = None
    concrete_strength_mpa: float | None = None
    steel_strength_mpa: float | None = None
    link_strength_mpa: float | None = None
    design_moment_knm: float | None = None
    design_shear_kn: float | None = None
    tension_steel_mm2: float | None = None
    link_area_mm2: float | None = None
    link_spacing_mm: float | None = None
    section_type: str = "rectangular"
    prestressed: bool = False
    axial_force_kn: float = 0.0
    torsion_knm: float = 0.0
    evidence: dict[str, list[SourceEvidence]] = field(default_factory=dict)
    conflict_fields: set[str] = field(default_factory=set)

    def facts(self) -> list[ExtractedFact]:
        values = {
            "span_mm": self.span_mm,
            "width_mm": self.width_mm,
            "overall_depth_mm": self.overall_depth_mm,
            "effective_depth_mm": self.effective_depth_mm,
            "concrete_strength_mpa": self.concrete_strength_mpa,
            "steel_strength_mpa": self.steel_strength_mpa,
            "link_strength_mpa": self.link_strength_mpa,
            "design_moment_knm": self.design_moment_knm,
            "design_shear_kn": self.design_shear_kn,
            "tension_steel_mm2": self.tension_steel_mm2,
            "link_area_mm2": self.link_area_mm2,
            "link_spacing_mm": self.link_spacing_mm,
        }
        units = {
            "span_mm": "mm",
            "width_mm": "mm",
            "overall_depth_mm": "mm",
            "effective_depth_mm": "mm",
            "concrete_strength_mpa": "MPa",
            "steel_strength_mpa": "MPa",
            "link_strength_mpa": "MPa",
            "design_moment_knm": "kN m",
            "design_shear_kn": "kN",
            "tension_steel_mm2": "mm2",
            "link_area_mm2": "mm2",
            "link_spacing_mm": "mm",
        }
        return [
            ExtractedFact(
                fact_id=f"{self.beam_id}:{name}",
                name=name,
                value=value,
                unit=units[name],
                evidence=self.evidence.get(name, []),
                confidence=min((item.confidence for item in self.evidence.get(name, [])), default=0.0),
                conflict=name in self.conflict_fields,
            )
            for name, value in values.items()
        ]


FLEXURE_FACTS = (
    "width_mm",
    "overall_depth_mm",
    "effective_depth_mm",
    "concrete_strength_mpa",
    "steel_strength_mpa",
    "design_moment_knm",
    "tension_steel_mm2",
)
SHEAR_FACTS = (
    "width_mm",
    "effective_depth_mm",
    "concrete_strength_mpa",
    "link_strength_mpa",
    "design_shear_kn",
    "tension_steel_mm2",
    "link_area_mm2",
    "link_spacing_mm",
)


def _all_evidence(beam: BeamCheckInput) -> list[SourceEvidence]:
    return [item for values in beam.evidence.values() for item in values]


def _value(value: float | None, unit: str) -> dict[str, Any]:
    return {"value": value, "unit": unit}


def _applicability(beam: BeamCheckInput, pack: CodePack) -> CheckResult:
    rule = pack.rules["rules"]["HK-RC-BEAM-APP-001"]
    limitations: list[str] = []
    if beam.section_type.lower() != "rectangular":
        limitations.append("Only rectangular sections are implemented in v0.17.")
    if beam.prestressed:
        limitations.append("Prestressed beams are outside the v0.17 rule scope.")
    if abs(beam.axial_force_kn) > 1e-9:
        limitations.append("Beam axial force is outside the v0.17 rule scope.")
    if abs(beam.torsion_knm) > 1e-9:
        limitations.append("Torsion is outside the v0.17 rule scope.")
    ratio = None
    if beam.span_mm and beam.overall_depth_mm and beam.overall_depth_mm > 0:
        ratio = beam.span_mm / beam.overall_depth_mm
        if ratio <= float(rule["normal_depth_span_ratio_limit"]):
            limitations.append("The span-to-overall-depth ratio triggers the deep-beam workflow.")

    return CheckResult(
        rule_id="HK-RC-BEAM-APP-001",
        title=rule["title"],
        status=CheckStatus.OUT_OF_SCOPE if limitations else CheckStatus.PASS,
        citations=rule["citations"],
        formula="effective span / overall depth > configured normal-beam threshold",
        formula_version=rule["formula_version"],
        inputs={
            "section_type": beam.section_type,
            "prestressed": beam.prestressed,
            "axial_force_kn": beam.axial_force_kn,
            "torsion_knm": beam.torsion_knm,
            "span_to_depth_ratio": ratio,
        },
        evidence=_all_evidence(beam),
        limitations=limitations,
        message="Beam is within the v0.17 deterministic scope." if not limitations else "Beam requires an unimplemented specialist workflow.",
    )


def _validate_positive(beam: BeamCheckInput, names: tuple[str, ...]) -> str | None:
    for name in names:
        value = getattr(beam, name)
        if value is not None and value <= 0:
            return f"{name} must be greater than zero."
    return None


def _flexure_checks(beam: BeamCheckInput, pack: CodePack) -> list[CheckResult]:
    facts = beam.facts()
    gate = evidence_gate(facts, FLEXURE_FACTS, rule_id="IDC-EVIDENCE-FLEXURE-001")
    results = [gate]
    if gate.status != CheckStatus.PASS:
        return results
    invalid = _validate_positive(beam, FLEXURE_FACTS)
    if invalid:
        gate.status = CheckStatus.ERROR
        gate.message = invalid
        return results

    rule = pack.rules["rules"]["HK-RC-BEAM-FLX-001"]
    reinforcement_rule = pack.rules["rules"]["HK-RC-BEAM-REINF-001"]
    b = float(beam.width_mm)
    h = float(beam.overall_depth_mm)
    d = float(beam.effective_depth_mm)
    fcu = float(beam.concrete_strength_mpa)
    fy = float(beam.steel_strength_mpa)
    moment = abs(float(beam.design_moment_knm))
    steel = float(beam.tension_steel_mm2)
    k_value = moment * 1_000_000 / (b * d * d * fcu)
    k_limit = float(rule["k_limit"])
    common_inputs = {
        "beam_id": beam.beam_id,
        "width": _value(b, "mm"),
        "overall_depth": _value(h, "mm"),
        "effective_depth": _value(d, "mm"),
        "concrete_strength": _value(fcu, "MPa"),
        "steel_strength": _value(fy, "MPa"),
        "design_moment": _value(moment, "kN m"),
        "provided_tension_steel": _value(steel, "mm2"),
        "K": k_value,
    }

    if k_value > k_limit:
        results.append(
            CheckResult(
                rule_id="HK-RC-BEAM-FLX-001",
                title=rule["title"],
                status=CheckStatus.OUT_OF_SCOPE,
                citations=rule["citations"],
                formula="K = M / (b d^2 fcu)",
                formula_version=rule["formula_version"],
                inputs=common_inputs,
                demand=moment,
                unit="kN m",
                evidence=_all_evidence(beam),
                limitations=["K exceeds the configured singly reinforced section limit; compression reinforcement design is not implemented."],
                message=f"K={k_value:.4f} exceeds K_limit={k_limit:.4f}.",
            )
        )
    else:
        lever_arm = min(
            float(rule["lever_arm_limit"]) * d,
            d * (0.5 + math.sqrt(0.25 - k_value / 0.9)),
        )
        required_steel = moment * 1_000_000 / (float(rule["steel_design_factor"]) * fy * lever_arm)
        neutral_axis = float(rule["steel_design_factor"]) * fy * steel / (
            float(rule["stress_block_force_factor"]) * fcu * b
        )
        capacity_lever_arm = min(
            float(rule["lever_arm_limit"]) * d,
            d - float(rule["stress_block_lever_factor"]) * neutral_axis,
        )
        capacity = max(0.0, float(rule["steel_design_factor"]) * fy * steel * capacity_lever_arm / 1_000_000)
        utilisation = moment / capacity if capacity > 0 else None
        passed = steel + 1e-9 >= required_steel and capacity + 1e-9 >= moment
        results.append(
            CheckResult(
                rule_id="HK-RC-BEAM-FLX-001",
                title=rule["title"],
                status=CheckStatus.PASS if passed else CheckStatus.FAIL,
                citations=rule["citations"],
                formula="K=M/(b d^2 fcu); z=min(0.95d, d(0.5+sqrt(0.25-K/0.9))); As,req=M/(0.87 fy z)",
                formula_version=rule["formula_version"],
                inputs={**common_inputs, "lever_arm": _value(lever_arm, "mm"), "required_tension_steel": _value(required_steel, "mm2")},
                demand=moment,
                capacity=capacity,
                utilisation=utilisation,
                unit="kN m",
                evidence=_all_evidence(beam),
                message=f"Provided As={steel:.1f} mm2; required As={required_steel:.1f} mm2.",
            )
        )

    ratio = steel / (b * h)
    minimum = float(reinforcement_rule["minimum_tension_ratio"])
    maximum = float(reinforcement_rule["maximum_total_ratio"])
    results.append(
        CheckResult(
            rule_id="HK-RC-BEAM-REINF-001",
            title=reinforcement_rule["title"],
            status=CheckStatus.PASS if minimum <= ratio <= maximum else CheckStatus.FAIL,
            citations=reinforcement_rule["citations"],
            formula="rho = As / (b h)",
            formula_version=reinforcement_rule["formula_version"],
            inputs={**common_inputs, "reinforcement_ratio": ratio, "minimum_ratio": minimum, "maximum_ratio": maximum},
            demand=ratio,
            capacity=maximum,
            utilisation=ratio / maximum,
            unit="ratio",
            evidence=_all_evidence(beam),
            message=f"Tension reinforcement ratio={ratio:.5f}; permitted range={minimum:.5f} to {maximum:.5f}.",
        )
    )
    return results


def _shear_checks(beam: BeamCheckInput, pack: CodePack) -> list[CheckResult]:
    facts = beam.facts()
    gate = evidence_gate(facts, SHEAR_FACTS, rule_id="IDC-EVIDENCE-SHEAR-001")
    results = [gate]
    if gate.status != CheckStatus.PASS:
        return results
    invalid = _validate_positive(beam, SHEAR_FACTS)
    if invalid:
        gate.status = CheckStatus.ERROR
        gate.message = invalid
        return results

    rule = pack.rules["rules"]["HK-RC-BEAM-SHR-001"]
    b = float(beam.width_mm)
    d = float(beam.effective_depth_mm)
    fcu = min(float(beam.concrete_strength_mpa), float(rule["concrete_strength_cap_mpa"]))
    fyv = float(beam.link_strength_mpa)
    shear = abs(float(beam.design_shear_kn))
    steel = float(beam.tension_steel_mm2)
    link_area = float(beam.link_area_mm2)
    spacing = float(beam.link_spacing_mm)
    shear_stress = shear * 1000 / (b * d)
    rho_percent = min(
        float(rule["reinforcement_ratio_max_percent"]),
        max(float(rule["reinforcement_ratio_min_percent"]), 100 * steel / (b * d)),
    )
    depth_factor = max(1.0, (float(rule["depth_reference_mm"]) / d) ** 0.25)
    concrete_shear = (
        float(rule["concrete_shear_coefficient"])
        / float(rule["concrete_material_factor"])
        * rho_percent ** (1 / 3)
        * depth_factor
        * (fcu / float(rule["concrete_strength_reference_mpa"])) ** (1 / 3)
    )
    maximum_shear = min(
        float(rule["maximum_shear_stress_cap_mpa"]),
        float(rule["maximum_shear_stress_coefficient"]) * math.sqrt(fcu),
    )
    provided_links = link_area / spacing
    demand_links = max(0.0, b * (shear_stress - concrete_shear) / (float(rule["steel_design_factor"]) * fyv))
    minimum_links = float(rule["minimum_link_stress_mpa"]) * b / (float(rule["steel_design_factor"]) * fyv)
    required_links = max(demand_links, minimum_links)
    link_capacity_stress = concrete_shear + float(rule["steel_design_factor"]) * fyv * provided_links / b
    capacity = link_capacity_stress * b * d / 1000
    spacing_limit = min(
        float(rule["maximum_link_spacing_mm"]),
        float(rule["maximum_link_spacing_depth_factor"]) * d,
    )
    common_inputs = {
        "beam_id": beam.beam_id,
        "width": _value(b, "mm"),
        "effective_depth": _value(d, "mm"),
        "concrete_strength_capped": _value(fcu, "MPa"),
        "link_strength": _value(fyv, "MPa"),
        "design_shear": _value(shear, "kN"),
        "shear_stress": _value(shear_stress, "MPa"),
        "concrete_shear_strength": _value(concrete_shear, "MPa"),
    }
    max_status = CheckStatus.PASS if shear_stress <= maximum_shear else CheckStatus.FAIL
    results.append(
        CheckResult(
            rule_id="HK-RC-BEAM-SHR-001A",
            title="Maximum beam shear stress",
            status=max_status,
            citations=rule["citations"],
            formula="v=V/(b d); vmax=min(0.8 sqrt(fcu), 7 MPa)",
            formula_version=rule["formula_version"],
            inputs={**common_inputs, "maximum_shear_stress": _value(maximum_shear, "MPa")},
            demand=shear_stress,
            capacity=maximum_shear,
            utilisation=shear_stress / maximum_shear,
            unit="MPa",
            evidence=_all_evidence(beam),
            message=f"v={shear_stress:.3f} MPa; configured vmax={maximum_shear:.3f} MPa.",
        )
    )
    links_pass = provided_links + 1e-12 >= required_links and spacing <= spacing_limit and max_status == CheckStatus.PASS
    results.append(
        CheckResult(
            rule_id="HK-RC-BEAM-SHR-001B",
            title=rule["title"],
            status=CheckStatus.PASS if links_pass else CheckStatus.FAIL,
            citations=rule["citations"],
            formula="Asv/s >= max[b(v-vc)/(0.87fyv), 0.4b/(0.87fyv)]; s <= min(0.75d, 300mm)",
            formula_version=rule["formula_version"],
            inputs={
                **common_inputs,
                "provided_Asv_per_s": _value(provided_links, "mm2/mm"),
                "required_Asv_per_s": _value(required_links, "mm2/mm"),
                "provided_spacing": _value(spacing, "mm"),
                "spacing_limit": _value(spacing_limit, "mm"),
            },
            demand=shear,
            capacity=capacity,
            utilisation=shear / capacity if capacity > 0 else None,
            unit="kN",
            evidence=_all_evidence(beam),
            message=(
                f"Provided Asv/s={provided_links:.4f} mm2/mm; required={required_links:.4f} mm2/mm; "
                f"spacing={spacing:.1f} mm; limit={spacing_limit:.1f} mm."
            ),
        )
    )
    return results


def run_beam_checks(beam: BeamCheckInput, pack: CodePack) -> list[CheckResult]:
    """Run applicability, flexure, reinforcement, and shear checks."""
    applicability = _applicability(beam, pack)
    if applicability.status != CheckStatus.PASS:
        return [applicability]
    return [applicability, *_flexure_checks(beam, pack), *_shear_checks(beam, pack)]


def _parse_evidence(raw: dict[str, Any], source_file: str) -> dict[str, list[SourceEvidence]]:
    parsed: dict[str, list[SourceEvidence]] = {}
    for name, entries in raw.items():
        parsed[name] = [
            SourceEvidence(
                source_file=item.get("source_file", source_file),
                page=item.get("page"),
                quote=item.get("quote", ""),
                extraction_method=item.get("extraction_method", "manual"),
                confidence=float(item.get("confidence", 1.0)),
            )
            for item in entries
        ]
    return parsed


def load_beam_inputs(path: str | Path, source_file: str) -> list[BeamCheckInput]:
    """Load reviewer-provided beam facts from JSON."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict):
        records = payload.get("beams", [payload])
    else:
        records = None
    if not isinstance(records, list):
        raise ValueError("Beam input JSON must be a beam object, a list, or an object with a beams list.")
    beams: list[BeamCheckInput] = []
    for record in records:
        if "beam_id" not in record:
            raise ValueError("Every beam input requires beam_id.")
        values = dict(record)
        values["source_file"] = values.get("source_file", source_file)
        values["evidence"] = _parse_evidence(values.get("evidence", {}), values["source_file"])
        values["conflict_fields"] = set(values.get("conflict_fields", []))
        beams.append(BeamCheckInput(**values))
    return beams
