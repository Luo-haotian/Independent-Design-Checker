"""End-to-end deterministic review orchestration and structured export."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from .beam_checks import BeamCheckInput, load_beam_inputs, run_beam_checks
from .code_basis import AUTO_CODE_PACK_ID, resolve_code_basis
from .facts import load_reviewed_facts, reviewed_input_kind
from .ingestion import DocumentExtraction
from .models import CheckResult, CheckStatus, ReviewRun, ReviewStatus


def create_review_run(
    extraction: DocumentExtraction,
    *,
    jurisdiction: str = "HK",
    code_pack_id: str = AUTO_CODE_PACK_ID,
    code_as_of: str | None = None,
    input_overrides: str | Path | None = None,
    ai_observations: list[str] | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> ReviewRun:
    """Create a traceable run. Deterministic checks require reviewer-supplied facts."""
    basis, deterministic_pack = resolve_code_basis(
        extraction,
        jurisdiction=jurisdiction,
        requested_pack_id=code_pack_id,
        code_as_of=code_as_of,
    )
    run = ReviewRun(
        run_id=uuid.uuid4().hex,
        source_file=extraction.source_path,
        source_sha256=extraction.source_sha256,
        code_basis=basis,
        page_count=extraction.page_count,
        processed_pages=extraction.processed_pages,
        unprocessed_pages=extraction.unprocessed_pages,
        ai_observations=list(ai_observations or []),
        model_provider=provider,
        model_name=model,
    )
    if input_overrides:
        input_kind = reviewed_input_kind(input_overrides)
        if input_kind == "generic":
            run.facts.extend(load_reviewed_facts(input_overrides, extraction.source_path))
            run.checks.append(
                CheckResult(
                    rule_id="IDC-RULE-ADAPTER-001",
                    title="Deterministic rule adapter coverage",
                    status=CheckStatus.OUT_OF_SCOPE,
                    citations=["IDC rule-adapter registry v0.17"],
                    formula="reviewed fact type + selected code basis + installed adapter",
                    formula_version="1.0.0",
                    inputs={"declared_codes": basis.declared_codes, "fact_count": len(run.facts)},
                    limitations=["No installed deterministic adapter consumes these generic reviewed facts."],
                    message="Facts remain available for evidence review and future rule layers; no engineering PASS or FAIL was produced.",
                )
            )
            run.status = ReviewStatus.READY_FOR_REVIEW
            return run
        beams: list[BeamCheckInput] = load_beam_inputs(input_overrides, extraction.source_path)
        for beam in beams:
            run.facts.extend(beam.facts())
            if deterministic_pack:
                run.checks.extend(run_beam_checks(beam, deterministic_pack))
            else:
                run.checks.append(
                    CheckResult(
                        rule_id="IDC-CODE-BASIS-001",
                        title="Deterministic rule-pack selection",
                        status=CheckStatus.OUT_OF_SCOPE,
                        citations=["IDC code-basis governance v0.17"],
                        formula="report-declared code basis + reviewer pinning",
                        formula_version="1.0.0",
                        inputs={"beam_id": beam.beam_id, "declared_codes": basis.declared_codes},
                        limitations=list(basis.unresolved_codes),
                        message="No unambiguous implemented deterministic rule pack applies to these reviewed facts.",
                    )
                )
    run.status = ReviewStatus.READY_FOR_REVIEW
    return run


def export_review_json(run: ReviewRun, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(run.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return destination


def deterministic_summary(run: ReviewRun) -> str:
    """Render a report section that never presents AI prose as an engineering result."""
    basis = run.code_basis
    if not basis.deterministic_rule_pack_id:
        approval = "NO DETERMINISTIC RULE PACK SELECTED"
    else:
        approval = "ENGINEERING-APPROVED" if basis.engineering_approved else "PENDING RESPONSIBLE ENGINEER APPROVAL"
    lines = [
        "# Deterministic Check Record",
        "",
        f"**Code basis:** {basis.authority}, {basis.edition}",
        f"**Basis profile:** {basis.code_pack_id} ({basis.selection_mode})",
        f"**Report-declared codes:** {', '.join(basis.declared_codes) or 'none detected'}",
        f"**Deterministic rule pack:** {basis.deterministic_rule_pack_id or 'none selected'} / rules {basis.rule_set_version}",
        f"**Rule approval:** {approval}",
        f"**Source SHA-256:** {run.source_sha256}",
        f"**Page coverage:** {len(run.processed_pages)}/{run.page_count} pages; unprocessed: {run.unprocessed_pages or 'none'}",
        "",
    ]
    if basis.unresolved_codes:
        lines.extend(["**Code-basis issues:**", *[f"- {item}" for item in basis.unresolved_codes], ""])
    if not run.checks:
        lines.extend([
            "## Structured Checks",
            "",
            "No reviewer-confirmed beam facts were supplied. No deterministic PASS or FAIL was produced.",
            "Use `--input-overrides` with page evidence to run the v0.17 beam checks.",
            "",
        ])
    else:
        lines.extend(["## Structured Checks", "", "| Rule | Status | Demand | Capacity | Utilisation | Evidence pages |", "| --- | --- | ---: | ---: | ---: | --- |"])
        for item in run.checks:
            pages = sorted({e.page for e in item.evidence if e.page is not None})
            utilisation = "" if item.utilisation is None else f"{item.utilisation:.3f}"
            lines.append(f"| {item.rule_id} | {item.status.value} | {item.demand if item.demand is not None else ''} | {item.capacity if item.capacity is not None else ''} | {utilisation} | {', '.join(map(str, pages)) or 'none'} |")
        lines.append("")
    lines.extend([
        "## AI Observations",
        "",
        "The following narrative is non-deterministic and cannot override a structured result.",
        "",
    ])
    return "\n".join(lines)


def has_blocking_results(run: ReviewRun) -> bool:
    return any(item.status in {CheckStatus.FAIL, CheckStatus.CONFLICT, CheckStatus.INSUFFICIENT_EVIDENCE, CheckStatus.ERROR} for item in run.checks)
