"""Shared review profiles used by every IDC entry point."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReviewProfile:
    id: str
    label: str
    purpose: str
    expected_package: str
    review_focus: tuple[str, ...]
    minimum_comments: int


REVIEW_PROFILES = {
    "building": ReviewProfile(
        id="building",
        label="Building",
        purpose="Permanent building structural calculation review.",
        expected_package="Design basis, loads and combinations, analysis, foundations, concrete/steel member calculations and serviceability checks.",
        review_focus=(
            "design basis and declared codes",
            "loads and combinations",
            "global analysis and stability",
            "foundation, concrete and steel member calculations",
            "serviceability and calculation-to-drawing interfaces",
        ),
        minimum_comments=12,
    ),
    "temporary": ReviewProfile(
        id="temporary",
        label="Temporary",
        purpose="Temporary works calculation and operational constraint review.",
        expected_package="Design stages, loads, member calculations, stability/bracing, bearings/supports, connections and usage limitations.",
        review_focus=(
            "construction and use stages",
            "temporary loading and combinations",
            "member adequacy and overall stability/bracing",
            "bearings, supports and connections",
            "construction sequence and operational limitations",
        ),
        minimum_comments=15,
    ),
}


def get_review_profile(profile_id: str) -> ReviewProfile:
    try:
        return REVIEW_PROFILES[profile_id.lower()]
    except KeyError as exc:
        raise ValueError(f"Unsupported review profile: {profile_id}") from exc


def profile_prompt(profile_id: str) -> str:
    profile = get_review_profile(profile_id)
    focus = "\n".join(f"- {item}" for item in profile.review_focus)
    return f"""You are an Independent Design Checker reviewing a {profile.label.lower()} submission.

Review only the calculation and supporting pages supplied below. Drawings have already been separated and are outside the v0.17 engineering assessment.

Review focus:
{focus}

Return one JSON object only, with this shape:
{{
  "executive_summary": "short calculation-focused summary",
  "comments": [
    {{
      "location": "PDF page and calculation section/member/formula",
      "pages": [1],
      "submitted_content": "what the submission states",
      "basis_and_comment": "evidence-based comment; cite a design code only when the submission declares it",
      "required_action": "specific response or correction",
      "assessment": "REQUIRES_CORRECTION | INFORMATION_REQUIRED | PENDING_CONFIRMATION | ACCEPTABLE",
      "confidence": 0.0,
      "note": "optional",
      "code_name": "exact report-declared code or blank",
      "code_clause": "candidate clause or blank"
    }}
  ]
}}

Rules:
- Every comment must cite original submitted PDF page numbers.
- Do not assume a Hong Kong code merely because the jurisdiction is Hong Kong.
- If a formula or design statement has no applicable code identified in the submission, use INFORMATION_REQUIRED and ask the designer to state the code and clause.
- Do not invent clauses. Candidate citations will be validated against the local reference library after your response.
- Uncertain facts must use PENDING_CONFIRMATION and cannot be called acceptable or not acceptable.
- Focus on actionable or uncertain items. Avoid repeating the same issue.

Calculation content:
{{content}}"""
