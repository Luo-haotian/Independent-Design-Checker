"""Read-only clause indexes for the three locally supplied HK codes."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .models import CodeEvidence


@dataclass(frozen=True, slots=True)
class LibrarySpec:
    family: str
    folder: str
    canonical_name: str
    edition: str
    aliases: tuple[str, ...]


LIBRARIES = (
    LibrarySpec(
        "concrete",
        "hkcop_concrete_2013_unlocked_structured",
        "HK Code of Practice for Structural Use of Concrete 2013",
        "2020 Edition",
        ("structural use of concrete", "concrete code 2013", "hk cop concrete 2013"),
    ),
    LibrarySpec(
        "foundation",
        "hkcop_foundation_2017_unlocked_structured",
        "HK Code of Practice for Foundations 2017",
        "2024 Edition",
        ("code of practice for foundations", "foundation code 2017", "hk foundation code"),
    ),
    LibrarySpec(
        "steel",
        "hkcop_steel_2011_structured",
        "HK Code of Practice for the Structural Use of Steel 2011",
        "2023 Edition",
        ("structural use of steel", "steel code 2011", "hk cop steel 2011"),
    ),
)
CLAUSE_RE = re.compile(r"(?:clause|cl\.?|section)?\s*(\d+(?:\.\d+){1,5})", re.I)


def _candidate_roots() -> list[Path]:
    roots: list[Path] = []
    configured = os.environ.get("IDC_CODE_LIBRARY", "").strip()
    if configured:
        roots.append(Path(configured))
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        roots.append(Path(sys._MEIPASS) / "HK COP OCR")
    roots.append(Path(__file__).resolve().parent.parent / "HK COP OCR")
    return roots


def _index_roots() -> list[Path]:
    roots: list[Path] = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        roots.append(Path(sys._MEIPASS) / "code_reference_indexes")
    roots.append(Path(__file__).resolve().parent.parent / "code_reference_indexes")
    return roots


def _runtime_index(spec: LibrarySpec) -> Path | None:
    for root in _index_roots():
        candidate = root / f"hk_{spec.family}.json"
        if candidate.is_file():
            return candidate
    return None


def code_library_root() -> Path | None:
    for root in _candidate_roots():
        if all((root / spec.folder / "structured.json").is_file() for spec in LIBRARIES):
            return root
    return None


def match_library(code_name: str) -> LibrarySpec | None:
    value = " ".join(code_name.lower().split())
    for spec in LIBRARIES:
        if any(alias in value for alias in spec.aliases):
            return spec
    return None


def edition_is_explicit(reported_text: str, spec: LibrarySpec) -> bool:
    year = re.search(r"(20\d{2})", spec.edition)
    return bool(year and re.search(rf"\b{year.group(1)}\b", reported_text))


def _walk_sections(items: list[dict], output: dict[str, tuple[str, int | None]]) -> None:
    for item in items:
        number = str(item.get("number", "")).strip()
        if number:
            output[number] = (str(item.get("title", "")), item.get("page"))
        _walk_sections(item.get("children") or [], output)


@lru_cache(maxsize=3)
def _load_index(folder: str) -> tuple[dict[str, list[int]], dict[str, tuple[str, int | None]], Path]:
    spec = next(item for item in LIBRARIES if item.folder == folder)
    runtime = _runtime_index(spec)
    if runtime:
        payload = json.loads(runtime.read_text(encoding="utf-8"))
        body_pages = {item["clause"]: [int(item["source_pdf_page"])] for item in payload["clauses"]}
        sections = {item["clause"]: (item["title"], item["printed_page"]) for item in payload["clauses"]}
        return body_pages, sections, runtime.parent
    root = code_library_root()
    if not root:
        raise FileNotFoundError("HK COP OCR code library is not available.")
    library_dir = root / folder
    payload = json.loads((library_dir / "structured.json").read_text(encoding="utf-8"))
    body_pages = {str(key): [int(page) for page in value] for key, value in payload["clauses_with_body_pages"].items()}
    sections: dict[str, tuple[str, int | None]] = {}
    _walk_sections(payload["section_tree"], sections)
    return body_pages, sections, library_dir


def _runtime_clause(spec: LibrarySpec, clause: str) -> dict | None:
    path = _runtime_index(spec)
    if not path:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return next((item for item in payload["clauses"] if item["clause"] == clause), None)


def _clean_excerpt(text: str, clause: str, limit: int = 650) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    position = re.search(rf"\b{re.escape(clause)}\b", text)
    if position:
        text = text[position.start() :]
    return text[:limit].strip()


def lookup_clause(code_name: str, clause_text: str, *, edition_confirmed: bool) -> CodeEvidence:
    spec = match_library(code_name)
    if not spec:
        return CodeEvidence(
            code_name=code_name or "No applicable code stated",
            edition="",
            clause=clause_text,
            verified=False,
            edition_confirmed=False,
            note="The report-declared code is not available in the local HK reference library.",
        )
    match = CLAUSE_RE.search(clause_text or "")
    if not match:
        return CodeEvidence(
            code_name=spec.canonical_name,
            edition=spec.edition,
            clause=clause_text,
            verified=False,
            edition_confirmed=edition_confirmed,
            note="No specific clause was supplied for validation.",
        )
    clause = match.group(1)
    try:
        body_pages, sections, library_dir = _load_index(spec.folder)
    except FileNotFoundError as exc:
        return CodeEvidence(
            code_name=spec.canonical_name,
            edition=spec.edition,
            clause=clause,
            verified=False,
            edition_confirmed=edition_confirmed,
            note=str(exc),
        )
    source_pages = body_pages.get(clause)
    section = sections.get(clause)
    if not source_pages or not section:
        return CodeEvidence(
            code_name=spec.canonical_name,
            edition=spec.edition,
            clause=clause,
            verified=False,
            edition_confirmed=edition_confirmed,
            note="The candidate clause was not found in the local structured index.",
        )
    source_page = source_pages[0]
    runtime_clause = _runtime_clause(spec, clause)
    if runtime_clause:
        excerpt = _clean_excerpt(str(runtime_clause.get("markdown") or ""), clause)
    else:
        page_path = library_dir / "pages" / f"page_{source_page:04d}.md"
        excerpt = _clean_excerpt(page_path.read_text(encoding="utf-8", errors="replace"), clause) if page_path.is_file() else ""
    edition_note = "" if edition_confirmed else "Submission does not confirm the local library edition/amendment status."
    return CodeEvidence(
        code_name=spec.canonical_name,
        edition=spec.edition,
        clause=clause,
        printed_page=section[1],
        source_pdf_page=source_page,
        excerpt=excerpt,
        verified=True,
        edition_confirmed=edition_confirmed,
        note=edition_note,
    )


def library_inventory() -> list[dict[str, object]]:
    root = code_library_root()
    output: list[dict[str, object]] = []
    for spec in LIBRARIES:
        available = bool(_runtime_index(spec) or (root and (root / spec.folder / "structured.json").is_file()))
        clause_count = 0
        if available:
            clause_count = len(_load_index(spec.folder)[0])
        output.append(
            {
                "family": spec.family,
                "canonical_name": spec.canonical_name,
                "edition": spec.edition,
                "folder": spec.folder,
                "available": available,
                "clause_count": clause_count,
            }
        )
    return output
