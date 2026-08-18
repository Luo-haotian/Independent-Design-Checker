"""Calculation-first page classification and normalized submission helpers."""

from __future__ import annotations

import re
from dataclasses import replace

from .ingestion import DocumentExtraction
from .models import NormalizedSubmission, PageClassification, PageRole
from .profiles import get_review_profile

TOC_RE = re.compile(r"\b(table\s+of\s+contents|contents)\b", re.I)
CALC_RE = re.compile(
    r"\b(design\s+calculation|calculation\s+sheet|calc\.?\s*no|design\s+loading|member\s+check|check\s+(?:of\s+)?(?:beam|column|slab|wall|pile|foundation|joist|bearer|scaffold)|utili[sz]ation|bending\s+moment|shear\s+(?:force|stress)|deflection)\b",
    re.I,
)
DRAWING_RE = re.compile(
    r"\b(drawing\s+no\.?|drawing\s+title|general\s+arrangement|layout\s+plan|floor\s+plan|elevation|section\s+[a-z0-9-]+|revisions?|scale\s*[:=]|key\s+plan|north\s+point|title\s+block)\b",
    re.I,
)
SUPPORT_RE = re.compile(
    r"\b(reference\s+codes?|codes?\s+(?:and|&)\s+standards?|material\s+properties|data\s+sheet|manufacturer|certificate|weight\s+reference|rebar\s+weight|appendix|design\s+parameters?)\b",
    re.I,
)
COVER_RE = re.compile(
    r"\b(submittal\s+form|submitted\s+by|target\s+approval|psp\s*/\s*idc|remarks\s*/\s*comments|approval\s+signature|document\s+control)\b",
    re.I,
)
RANGE_RE = re.compile(
    r"(?P<label>calculations?|design\s+calculations?|drawings?|appendix|supporting\s+information)\D{0,40}(?P<start>\d{1,4})\s*(?:[-–—]|to)\s*(?P<end>\d{1,4})",
    re.I,
)


def _title(text: str) -> str:
    for line in text.splitlines():
        value = " ".join(line.split()).strip(" -")
        if 4 <= len(value) <= 140:
            return value
    return ""


def _toc_hints(extraction: DocumentExtraction) -> dict[int, tuple[PageRole, str]]:
    hints: dict[int, tuple[PageRole, str]] = {}
    for page in extraction.pages:
        if not TOC_RE.search(page.text):
            continue
        for match in RANGE_RE.finditer(page.text):
            label = match.group("label").lower()
            role = PageRole.CALCULATION if "calcul" in label else PageRole.DRAWING if "drawing" in label else PageRole.SUPPORTING
            start, end = int(match.group("start")), int(match.group("end"))
            if 1 <= start <= end <= extraction.page_count:
                for number in range(start, end + 1):
                    hints[number] = (role, f"table of contents states {label} pages {start}-{end}")
    return hints


def _classify_page(page, toc_hint: tuple[PageRole, str] | None) -> PageClassification:
    text = " ".join(page.text.split())
    lower = text.lower()
    reasons: list[str] = []
    scores = {role: 0.0 for role in PageRole}

    if toc_hint:
        scores[toc_hint[0]] += 0.78
        reasons.append(toc_hint[1])
    if TOC_RE.search(text):
        scores[PageRole.TOC] += 0.95
        reasons.append("contents heading detected")
    if COVER_RE.search(text):
        scores[PageRole.COVER] += 0.9
        reasons.append("submission/approval form language detected")
    calculation_hits = len(CALC_RE.findall(text))
    if calculation_hits:
        scores[PageRole.CALCULATION] += min(0.96, 0.55 + calculation_hits * 0.09)
        reasons.append(f"{calculation_hits} calculation signal(s) detected")
    drawing_hits = len(DRAWING_RE.findall(text))
    if drawing_hits:
        scores[PageRole.DRAWING] += min(0.94, 0.48 + drawing_hits * 0.08)
        reasons.append(f"{drawing_hits} drawing/title-block signal(s) detected")
    if page.width and page.height and page.width > page.height * 1.12:
        scores[PageRole.DRAWING] += 0.35
        reasons.append("landscape sheet geometry")
    support_hits = len(SUPPORT_RE.findall(text))
    if support_hits:
        scores[PageRole.SUPPORTING] += min(0.9, 0.55 + support_hits * 0.08)
        reasons.append(f"{support_hits} supporting/reference signal(s) detected")
    if page.embedded_images and len(text) < 250 and scores[PageRole.DRAWING] > 0:
        scores[PageRole.DRAWING] += 0.12
        reasons.append("image-heavy sheet")

    # A calculation sheet may contain a sketch; repeated calculation signals win.
    if calculation_hits >= 2:
        scores[PageRole.CALCULATION] += 0.18
    if "rebar weight reference" in lower:
        scores[PageRole.SUPPORTING] += 0.35
        scores[PageRole.CALCULATION] -= 0.15

    best_role = max(scores, key=scores.get)
    confidence = max(0.0, min(1.0, scores[best_role]))
    ordered = sorted(scores.values(), reverse=True)
    if not text.strip():
        if page.page_number == 1:
            best_role, confidence = PageRole.COVER, 0.35
            reasons.append("unreadable first page treated as administrative cover")
        else:
            best_role, confidence = PageRole.UNKNOWN, 0.0
            reasons.append("no readable text")
    elif confidence < 0.55 or (len(ordered) > 1 and ordered[0] - ordered[1] < 0.12):
        best_role = PageRole.UNKNOWN
        confidence = max(0.25, min(0.54, confidence))
        reasons.append("page role is ambiguous")

    return PageClassification(
        page=page.page_number,
        role=best_role,
        title=_title(page.text),
        confidence=round(confidence, 2),
        reasons=reasons,
    )


def _smooth_page_sequence(classifications: list[PageClassification], extraction: DocumentExtraction) -> None:
    by_page = {page.page_number: page for page in extraction.pages}
    for index in range(1, len(classifications) - 1):
        current = classifications[index]
        previous = classifications[index - 1]
        following = classifications[index + 1]
        source = by_page[current.page]
        landscape = bool(source.width and source.height and source.width > source.height * 1.12)
        if previous.role == following.role == PageRole.CALCULATION and not landscape:
            if current.role in {PageRole.UNKNOWN, PageRole.DRAWING, PageRole.SUPPORTING} and current.confidence < 0.8:
                current.role = PageRole.CALCULATION
                current.confidence = max(current.confidence, 0.78)
                current.reasons.append("page is between consecutive calculation sheets")
        if landscape and DRAWING_RE.search(source.text) and current.role in {PageRole.UNKNOWN, PageRole.COVER}:
            current.role = PageRole.DRAWING
            current.confidence = max(current.confidence, 0.82)
            current.reasons.append("landscape drawing sheet with title-block signals")


def normalize_submission(extraction: DocumentExtraction, review_profile: str) -> NormalizedSubmission:
    """Classify every page before checking and select calculation-focused review pages."""
    get_review_profile(review_profile)
    hints = _toc_hints(extraction)
    pages = [_classify_page(page, hints.get(page.page_number)) for page in extraction.pages]
    _smooth_page_sequence(pages, extraction)
    grouped = {role: [item.page for item in pages if item.role == role] for role in PageRole}
    uncertain = sorted({item.page for item in pages if item.role == PageRole.UNKNOWN or item.confidence < 0.55})
    reviewed = sorted(set(grouped[PageRole.CALCULATION] + grouped[PageRole.SUPPORTING] + grouped[PageRole.UNKNOWN]))
    deferred = sorted(set(grouped[PageRole.COVER] + grouped[PageRole.TOC] + grouped[PageRole.DRAWING]))
    warnings: list[str] = []
    if not grouped[PageRole.TOC]:
        warnings.append("No reliable table of contents was detected; page roles were inferred from page-level evidence.")
    if uncertain:
        warnings.append(f"Page role requires confirmation for pages {format_page_ranges(uncertain)}.")
    if not grouped[PageRole.CALCULATION]:
        warnings.append("No page was confidently classified as calculation; all non-drawing readable candidates remain in review scope.")
    return NormalizedSubmission(
        review_profile=review_profile,
        pages=pages,
        calculation_pages=grouped[PageRole.CALCULATION],
        drawing_pages=grouped[PageRole.DRAWING],
        supporting_pages=grouped[PageRole.SUPPORTING],
        uncertain_pages=uncertain,
        reviewed_pages=reviewed,
        deferred_pages=deferred,
        warnings=warnings,
    )


def review_extraction(extraction: DocumentExtraction, normalized: NormalizedSubmission) -> DocumentExtraction:
    selected = set(normalized.reviewed_pages)
    return replace(extraction, pages=[page for page in extraction.pages if page.page_number in selected])


def format_page_ranges(pages: list[int]) -> str:
    if not pages:
        return "None"
    values = sorted(set(pages))
    ranges: list[str] = []
    start = previous = values[0]
    for value in values[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = value
    ranges.append(str(start) if start == previous else f"{start}-{previous}")
    return ", ".join(ranges)
