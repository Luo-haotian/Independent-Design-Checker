"""Structured model-comment parsing, deduplication, and code citation validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .code_library import edition_is_explicit, lookup_clause, match_library
from .models import CommentAssessment, ReviewComment, SourceEvidence


@dataclass(slots=True)
class ParsedReview:
    executive_summary: str
    comments: list[ReviewComment]
    raw_response: str


def _json_object(text: str) -> dict[str, Any] | None:
    candidates = [text.strip()]
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.I | re.S)
    if fenced:
        candidates.insert(0, fenced.group(1))
    first, last = text.find("{"), text.rfind("}")
    if first >= 0 and last > first:
        candidates.append(text[first : last + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, dict):
            return value
    return None


def _assessment(value: object) -> CommentAssessment:
    normalized = str(value or "INFORMATION_REQUIRED").strip().upper().replace(" ", "_")
    try:
        return CommentAssessment(normalized)
    except ValueError:
        return CommentAssessment.INFORMATION_REQUIRED


def _pages(value: object, fallback_pages: list[int]) -> list[int]:
    if not isinstance(value, list):
        return fallback_pages[:1]
    return sorted({int(page) for page in value if isinstance(page, int) and not isinstance(page, bool) and page > 0}) or fallback_pages[:1]


def parse_model_review(text: str, chunk_pages: list[int]) -> ParsedReview:
    payload = _json_object(text)
    if payload:
        comments: list[ReviewComment] = []
        for index, item in enumerate(payload.get("comments") or [], start=1):
            if not isinstance(item, dict):
                continue
            pages = _pages(item.get("pages"), chunk_pages)
            confidence = item.get("confidence", 0.5)
            try:
                confidence = max(0.0, min(1.0, float(confidence)))
            except (TypeError, ValueError):
                confidence = 0.5
            evidence = [SourceEvidence(source_file="submitted PDF", page=page, confidence=confidence) for page in pages]
            note_parts = [str(item.get("note") or "").strip()]
            code_name = str(item.get("code_name") or "").strip()
            code_clause = str(item.get("code_clause") or "").strip()
            if code_name or code_clause:
                note_parts.append(f"Candidate code: {code_name or 'not stated'}; clause: {code_clause or 'not stated'}")
            comments.append(
                ReviewComment(
                    comment_no=index,
                    location=str(item.get("location") or f"PDF page {', '.join(map(str, pages))}").strip(),
                    submitted_content=str(item.get("submitted_content") or "Submitted calculation item requires review.").strip(),
                    basis_and_comment=str(item.get("basis_and_comment") or "The supporting basis is not clear from the submitted calculation.").strip(),
                    required_action=str(item.get("required_action") or "Provide clarification and supporting calculation evidence.").strip(),
                    assessment=_assessment(item.get("assessment")),
                    confidence=round(confidence, 2),
                    note=" | ".join(part for part in note_parts if part),
                    evidence=evidence,
                )
            )
        return ParsedReview(str(payload.get("executive_summary") or "").strip(), comments, text)

    # Safe fallback: preserve useful prose as one pending item instead of pretending it was structured.
    compact = " ".join(text.split())[:1800]
    page_text = ", ".join(map(str, chunk_pages)) or "unknown"
    fallback = ReviewComment(
        comment_no=1,
        location=f"PDF pages {page_text}",
        submitted_content="The model response could not be parsed into the required comment schema.",
        basis_and_comment=compact or "No structured review response was returned.",
        required_action="Reviewer to confirm this observation against the submitted calculation.",
        assessment=CommentAssessment.PENDING_CONFIRMATION,
        confidence=0.25,
        note="Unstructured model response retained for maintenance review.",
        evidence=[SourceEvidence(source_file="submitted PDF", page=page, confidence=0.25) for page in chunk_pages],
    )
    return ParsedReview("Calculation review requires reviewer confirmation.", [fallback], text)


def _candidate_from_note(comment: ReviewComment) -> tuple[str, str]:
    match = re.search(r"Candidate code:\s*(.*?);\s*clause:\s*(.*?)(?:\s*\||$)", comment.note, re.I)
    if not match:
        return "", ""
    code_name = match.group(1).strip()
    clause = match.group(2).strip()
    return ("" if code_name == "not stated" else code_name, "" if clause == "not stated" else clause)


def _declared_candidate(code_name: str, declarations: list[dict[str, str | None]]) -> dict[str, str | None] | None:
    candidate = " ".join(code_name.lower().split())
    candidate_key = re.sub(r"\W+", "", candidate)
    spec = match_library(code_name)
    for item in declarations:
        canonical = str(item.get("canonical_name") or "").lower()
        reported = str(item.get("reported_text") or "").lower()
        canonical_key = re.sub(r"\W+", "", canonical)
        reported_key = re.sub(r"\W+", "", reported)
        if candidate_key and (
            candidate_key in canonical_key
            or canonical_key in candidate_key
            or candidate_key in reported_key
            or reported_key in candidate_key
        ):
            return item
        if spec and str(item.get("family") or "") == spec.family:
            return item
    return None


def validate_comment_codes(comments: list[ReviewComment], declarations: list[dict[str, str | None]]) -> list[ReviewComment]:
    validated: list[ReviewComment] = []
    for comment in comments:
        code_name, clause = _candidate_from_note(comment)
        if not code_name:
            if comment.assessment == CommentAssessment.ACCEPTABLE:
                comment.assessment = CommentAssessment.INFORMATION_REQUIRED
            if "evidence-based" not in comment.basis_and_comment.lower():
                comment.basis_and_comment += " No applicable design code and clause were identified in the submitted calculation for this check."
                comment.required_action += " State the applicable design code, edition and clause."
            validated.append(comment)
            continue

        declaration = _declared_candidate(code_name, declarations)
        if not declaration:
            evidence = lookup_clause(code_name, clause, edition_confirmed=False)
            comment.code_evidence.append(evidence)
            comment.assessment = CommentAssessment.INFORMATION_REQUIRED
            comment.basis_and_comment += " The candidate code was not identified in the submitted report and cannot be adopted by default."
            comment.required_action += " Confirm the applicable report-declared code and clause."
            validated.append(comment)
            continue

        spec = match_library(code_name)
        if not spec:
            evidence = lookup_clause(code_name, clause, edition_confirmed=False)
            comment.code_evidence.append(evidence)
            comment.assessment = CommentAssessment.INFORMATION_REQUIRED
            comment.basis_and_comment += " The report declares this external code, but it is not available in the local HK reference library for clause validation."
            comment.required_action += " Provide the governing code excerpt and confirm the clause application."
            validated.append(comment)
            continue
        confirmed = bool(spec and edition_is_explicit(str(declaration.get("reported_text") or ""), spec))
        evidence = lookup_clause(code_name, clause, edition_confirmed=confirmed)
        comment.code_evidence.append(evidence)
        if evidence.verified:
            citation = f"{evidence.code_name}, {evidence.edition}, clause {evidence.clause}, code page {evidence.printed_page}"
            comment.basis_and_comment += f" Local reference verified: {citation}."
            if not evidence.edition_confirmed:
                comment.assessment = CommentAssessment.PENDING_CONFIRMATION
                comment.required_action += " Confirm the code edition and amendment status used by the designer."
        else:
            comment.assessment = CommentAssessment.INFORMATION_REQUIRED
            comment.basis_and_comment += f" Candidate citation could not be validated locally: {evidence.note}"
            comment.required_action += " Provide the governing code excerpt or correct clause reference."
        validated.append(comment)
    return validated


def merge_comments(groups: list[list[ReviewComment]]) -> list[ReviewComment]:
    output: list[ReviewComment] = []
    seen: set[str] = set()
    for comments in groups:
        for comment in comments:
            key = re.sub(r"\W+", " ", f"{comment.location} {comment.submitted_content} {comment.required_action}".lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            output.append(comment)
    for index, comment in enumerate(output, start=1):
        comment.comment_no = index
    return output
