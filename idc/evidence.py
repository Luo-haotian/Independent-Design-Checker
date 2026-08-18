"""Evidence and design-basis gates shared by deterministic checks."""

from __future__ import annotations

from collections.abc import Iterable

from .models import CheckResult, CheckStatus, ExtractedFact


def fact_map(facts: Iterable[ExtractedFact]) -> dict[str, ExtractedFact]:
    return {fact.name: fact for fact in facts}


def evidence_gate(
    facts: Iterable[ExtractedFact],
    required_names: Iterable[str],
    *,
    rule_id: str = "IDC-EVIDENCE-001",
) -> CheckResult:
    """Block deterministic PASS/FAIL when required facts are missing or conflicting."""
    mapped = fact_map(facts)
    missing = [name for name in required_names if name not in mapped or mapped[name].value in (None, "")]
    conflicts = [name for name in required_names if name in mapped and mapped[name].conflict]
    without_evidence = [
        name
        for name in required_names
        if name in mapped and mapped[name].value not in (None, "") and not mapped[name].evidence
    ]

    if conflicts:
        status = CheckStatus.CONFLICT
        message = f"Conflicting required facts: {', '.join(conflicts)}."
    elif missing or without_evidence:
        status = CheckStatus.INSUFFICIENT_EVIDENCE
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if without_evidence:
            details.append(f"no source evidence: {', '.join(without_evidence)}")
        message = "Required evidence is incomplete (" + "; ".join(details) + ")."
    else:
        status = CheckStatus.PASS
        message = "All required facts have source evidence and no conflicts."

    evidence = [item for name in required_names if name in mapped for item in mapped[name].evidence]
    return CheckResult(
        rule_id=rule_id,
        title="Required evidence gate",
        status=status,
        citations=["IDC evidence policy v0.17"],
        formula="required facts present + page evidence present + no conflicts",
        formula_version="1.0.0",
        inputs={name: mapped[name].value if name in mapped else None for name in required_names},
        evidence=evidence,
        message=message,
    )
