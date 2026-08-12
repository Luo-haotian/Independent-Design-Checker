"""Explicit unit conversions accepted by reviewer-confirmed input files."""

from __future__ import annotations

TARGET_UNITS = {
    "span_mm": "mm", "width_mm": "mm", "overall_depth_mm": "mm", "effective_depth_mm": "mm",
    "concrete_strength_mpa": "MPa", "steel_strength_mpa": "MPa", "link_strength_mpa": "MPa",
    "design_moment_knm": "kN m", "design_shear_kn": "kN", "tension_steel_mm2": "mm2",
    "link_area_mm2": "mm2", "link_spacing_mm": "mm", "axial_force_kn": "kN", "torsion_knm": "kN m",
}

FACTORS = {
    ("m", "mm"): 1000.0, ("cm", "mm"): 10.0, ("mm", "mm"): 1.0,
    ("Pa", "MPa"): 1e-6, ("kPa", "MPa"): 1e-3, ("MPa", "MPa"): 1.0,
    ("N", "kN"): 1e-3, ("kN", "kN"): 1.0,
    ("N m", "kN m"): 1e-3, ("kN m", "kN m"): 1.0,
    ("m2", "mm2"): 1e6, ("cm2", "mm2"): 100.0, ("mm2", "mm2"): 1.0,
}


def convert_value(value: float, source_unit: str, target_unit: str) -> float:
    try:
        factor = FACTORS[(source_unit.strip(), target_unit)]
    except KeyError as exc:
        raise ValueError(f"Unsupported unit conversion: {source_unit} to {target_unit}.") from exc
    return float(value) * factor


def normalize_input_units(values: dict) -> dict:
    normalized = dict(values)
    units = normalized.pop("units", {})
    if not isinstance(units, dict):
        raise ValueError("units must be an object keyed by input field.")
    for field, source_unit in units.items():
        if field not in TARGET_UNITS:
            raise ValueError(f"Unknown unit field: {field}.")
        if normalized.get(field) is not None:
            normalized[field] = convert_value(normalized[field], str(source_unit), TARGET_UNITS[field])
    return normalized
