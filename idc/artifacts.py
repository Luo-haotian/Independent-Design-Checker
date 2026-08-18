"""Create the downloadable standard calculation-review package."""

from __future__ import annotations

import json
import zipfile
from dataclasses import asdict
from pathlib import Path

from .ingestion import DocumentExtraction
from .models import ReviewRun
from .submission import format_page_ranges

STANDARD_FILES = (
    "submission_map.json",
    "normalized_calculations.json",
    "normalized_calculations.md",
    "review_comments.json",
    "code_evidence.json",
    "processing_record.json",
)


def _json(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False)


def create_standard_package(run: ReviewRun, extraction: DocumentExtraction, destination: str | Path) -> Path:
    if not run.submission_structure:
        raise ValueError("A standard package requires a normalized submission structure.")
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    structure = run.submission_structure
    reviewed = set(structure.reviewed_pages)
    normalized_pages = [
        {
            "page": page.page_number,
            "extraction_method": page.extraction_method,
            "confidence": page.confidence,
            "text": page.text,
        }
        for page in extraction.pages
        if page.page_number in reviewed
    ]
    md_lines = [
        "# Normalized Calculation Submission",
        "",
        f"- Review profile: {structure.review_profile}",
        f"- Calculation pages: {format_page_ranges(structure.calculation_pages)}",
        f"- Supporting pages: {format_page_ranges(structure.supporting_pages)}",
        f"- Drawing pages: {format_page_ranges(structure.drawing_pages)} (identified; not assessed in v0.17)",
        f"- Uncertain pages: {format_page_ranges(structure.uncertain_pages)}",
        "",
    ]
    for page in normalized_pages:
        md_lines.extend([f"## Submitted PDF page {page['page']}", "", str(page["text"]).strip(), ""])

    code_evidence = []
    seen: set[tuple[str, str, str]] = set()
    for comment in run.comments:
        for evidence in comment.code_evidence:
            key = (evidence.code_name, evidence.edition, evidence.clause)
            if key not in seen:
                seen.add(key)
                code_evidence.append(asdict(evidence))
    run.code_evidence = [evidence for comment in run.comments for evidence in comment.code_evidence]
    run.artifact_manifest = {name: "standard-package" for name in STANDARD_FILES}

    contents = {
        "submission_map.json": _json(asdict(structure)),
        "normalized_calculations.json": _json({"review_profile": structure.review_profile, "pages": normalized_pages}),
        "normalized_calculations.md": "\n".join(md_lines),
        "review_comments.json": _json([asdict(comment) for comment in run.comments]),
        "code_evidence.json": _json(code_evidence),
        "processing_record.json": _json(run.to_dict()),
    }
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in STANDARD_FILES:
            archive.writestr(name, contents[name])
    return output
