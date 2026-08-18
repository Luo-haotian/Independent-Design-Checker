"""Evidence-aware LLM narrative and optional critic passes."""

from __future__ import annotations

from collections.abc import Callable

from .code_basis import detect_code_declarations
from .comments import merge_comments, parse_model_review, validate_comment_codes
from .ingestion import DocumentExtraction, build_page_chunks, coverage_from_chunks
from .models import ReviewComment

PROMPT_VERSION = "idc-v0.17-calculation-comments-2"


def review_document(
    extraction: DocumentExtraction,
    base_prompt: str,
    call_model: Callable[[str], str | None],
    *,
    max_input_chars: int,
    critic: bool = False,
    call_critic: Callable[[str], str | None] | None = None,
    declared_code_text: str | None = None,
) -> tuple[str | None, list[str], list[int], list[int], str, list[ReviewComment]]:
    """Review all readable pages and disclose document coverage."""
    chunks = build_page_chunks(extraction, max_input_chars)
    covered, missing = coverage_from_chunks(extraction, chunks)
    if not chunks:
        return None, [], covered, missing, "", []

    observations: list[str] = []
    parsed_groups: list[list[ReviewComment]] = []
    summaries: list[str] = []
    for chunk in chunks:
        prompt = base_prompt.replace("{content}", chunk.content)
        prompt += (
            "\n\nReturn valid JSON only. Evidence requirement: cite submitted page numbers for every factual observation. "
            "This is an AI-assisted calculation review and must not claim a deterministic code PASS or FAIL."
        )
        report = call_model(prompt)
        if report:
            parsed = parse_model_review(report, chunk.page_numbers)
            parsed_groups.append(parsed.comments)
            if parsed.executive_summary:
                summaries.append(parsed.executive_summary)
            observations.append(report)

    if not parsed_groups:
        return None, observations, covered, missing, "", []

    comments = merge_comments(parsed_groups)
    declarations = detect_code_declarations(declared_code_text or extraction.full_text)
    comments = validate_comment_codes(comments, declarations)

    if critic and call_critic:
        critic_prompt = (
            "Act as an independent critic. Return the same JSON comment schema. Identify unsupported claims, "
            "missing page evidence, contradictions and unsafe compliance language. Do not alter deterministic results.\n\n"
            + "\n\n".join(observations)
        )
        critic_result = call_critic(critic_prompt)
        if critic_result:
            observations.append(critic_result)
            critic_comments = parse_model_review(critic_result, covered).comments
            comments = merge_comments([comments, validate_comment_codes(critic_comments, declarations)])

    executive_summary = " ".join(dict.fromkeys(summaries))
    internal_lines = ["# Calculation Review Internal Summary", "", executive_summary, "", "## Structured Comments", ""]
    for comment in comments:
        internal_lines.append(
            f"- C{comment.comment_no:03d} | {comment.assessment.value} | {comment.location} | {comment.required_action}"
        )
    return "\n".join(internal_lines), observations, covered, missing, executive_summary, comments
