"""Load generic reviewer-confirmed facts when no deterministic adapter applies."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ExtractedFact, SourceEvidence


def reviewed_input_kind(path: str | Path) -> str:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list) or (isinstance(payload, dict) and ("beams" in payload or "beam_id" in payload)):
        return "beam"
    if isinstance(payload, dict) and isinstance(payload.get("facts"), list):
        return "generic"
    raise ValueError("Reviewed input must contain a facts list or supported member records.")


def _evidence(items: Any, source_file: str) -> list[SourceEvidence]:
    if not isinstance(items, list):
        raise ValueError("Fact evidence must be a list.")
    evidence: list[SourceEvidence] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Fact evidence items must be objects.")
        page = item.get("page")
        confidence = float(item.get("confidence", 1.0))
        if page is not None and (not isinstance(page, int) or isinstance(page, bool) or page < 1):
            raise ValueError("Fact evidence pages must be positive integers.")
        if not 0 <= confidence <= 1:
            raise ValueError("Fact evidence confidence must be between 0 and 1.")
        evidence.append(
            SourceEvidence(
                source_file=str(item.get("source_file") or source_file),
                page=page,
                quote=str(item.get("quote", "")),
                extraction_method=str(item.get("extraction_method", "manual")),
                confidence=confidence,
            )
        )
    return evidence


def load_reviewed_facts(path: str | Path, source_file: str) -> list[ExtractedFact]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    records = payload.get("facts") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise ValueError("Generic reviewed input requires a facts list.")
    facts: list[ExtractedFact] = []
    for index, item in enumerate(records, start=1):
        if not isinstance(item, dict) or not str(item.get("name", "")).strip():
            raise ValueError("Every reviewed fact requires a name.")
        facts.append(
            ExtractedFact(
                fact_id=str(item.get("fact_id") or f"reviewed:{index}"),
                name=str(item["name"]),
                value=item.get("value"),
                unit=item.get("unit"),
                evidence=_evidence(item.get("evidence", []), source_file),
                confidence=float(item.get("confidence", 1.0)),
                conflict=bool(item.get("conflict", False)),
                reviewer_overridden=True,
            )
        )
    return facts
