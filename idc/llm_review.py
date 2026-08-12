"""Evidence-aware LLM narrative and optional critic passes."""

from __future__ import annotations

from collections.abc import Callable

from .ingestion import DocumentExtraction, build_page_chunks, coverage_from_chunks

PROMPT_VERSION = "idc-v0.17-page-evidence-1"


def review_document(
    extraction: DocumentExtraction,
    base_prompt: str,
    call_model: Callable[[str], str | None],
    *,
    max_input_chars: int,
    critic: bool = False,
    call_critic: Callable[[str], str | None] | None = None,
) -> tuple[str | None, list[str], list[int], list[int]]:
    """Review all readable pages and disclose document coverage."""
    chunks = build_page_chunks(extraction, max_input_chars)
    covered, missing = coverage_from_chunks(extraction, chunks)
    if not chunks:
        return None, [], covered, missing

    observations: list[str] = []
    chunk_reports: list[str] = []
    for chunk in chunks:
        prompt = base_prompt.format(content=chunk.content)
        prompt += (
            "\n\nEvidence requirement: cite submitted page numbers for every factual observation. "
            "This is an AI-assisted narrative review and must not claim a deterministic code PASS or FAIL."
        )
        report = call_model(prompt)
        if report:
            chunk_reports.append(f"## Review chunk {chunk.index} - pages {chunk.page_numbers}\n\n{report}")

    if not chunk_reports:
        return None, observations, covered, missing

    coverage_note = (
        "# Document Coverage\n\n"
        f"- Source SHA-256: `{extraction.source_sha256}`\n"
        f"- Processed pages: {covered}\n"
        f"- Unprocessed or unreadable pages: {missing or 'None'}\n"
        f"- Prompt version: `{PROMPT_VERSION}`\n\n"
    )
    combined = coverage_note + "\n\n".join(chunk_reports)

    if critic and call_critic:
        critic_prompt = (
            "Act as an independent critic. Review the following AI observations for unsupported claims, "
            "missing page evidence, contradictions, and unsafe compliance language. Do not alter deterministic results.\n\n"
            + combined
        )
        critic_result = call_critic(critic_prompt)
        if critic_result:
            observations.append(critic_result)
            combined += "\n\n# Optional AI Critic Observations\n\n" + critic_result

    return combined, observations, covered, missing
