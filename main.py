"""IDC standard PDF checker."""

import argparse
import logging
import os
import re
import sys
from datetime import datetime
from typing import Optional

from config import (
    call_chat_completion,
    get_llm_config,
    get_provider_label,
)
from idc.artifacts import create_standard_package
from idc.code_basis import resolve_code_basis
from idc.ingestion import DocumentExtraction, ingest_pdf
from idc.llm_review import review_document
from idc.pipeline import create_review_run, export_review_json
from idc.profiles import profile_prompt
from idc.submission import normalize_submission, review_extraction

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("idc.log", encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

BUILDING_PROMPT = """You are an expert structural engineer acting as an Independent Design Checker (IDC) for a Hong Kong structural engineering submission. Analyze the provided building design and produce a formal design verification report in the style of a Hong Kong Housing Authority (HKHA) ICU submission report.

Requirements:
- Use formal engineering language consistent with HKHA ICU submission reports.
- Organize the report with clear Markdown headings (# for main sections, ## for sub-sections) based on the ACTUAL content provided. Do NOT invent sections that are not supported by the input material.
- Where applicable, reference Hong Kong design codes (e.g. Code of Practice for Structural Use of Concrete 2013, Code of Practice on Wind Effects in Hong Kong 2019, Code of Practice for Dead and Imposed Loads 2011, etc.).
- Include an Executive Summary.
- Classify any issues found as Critical, Major, or Minor.
- Provide actionable Recommendations.
- Do not issue engineering PASS/FAIL or Satisfactory/Unsatisfactory conclusions. Use "AI Observation: Appears adequate / Requires review / Insufficient information" with brief justification.
- Do not keep the report high-level only. For every major section, include specific IDC reviewer comments on adequacy, assumptions, missing information, and follow-up actions.
- Even where the design appears generally acceptable, provide multiple concrete review comments rather than only saying it is satisfactory.
- Use this reporting pattern for each major section where supported by the submitted material:
  ## Section Title
  **AI Observation:** Appears adequate / Requires review / Insufficient information
  **IDC Reviewer Comments:**
  - at least 3 concrete review comments
  - each comment must mention actual submitted parameters, member names, drawings, calculations, assumptions, or missing information whenever available
  - comments must say what is acceptable, what is unclear, and what follow-up is required
- Include at least 12 substantive IDC reviewer comments across the whole report.
- Prefer specific engineering observations over generic wording. Quote actual loads, sizes, spans, material grades, code clauses, or calculation references whenever those appear in the source text.
- If information is not available in the design content, state "Not covered in submitted documents" rather than inventing data.

Design Content:
{content}"""

TEMPORARY_PROMPT = """You are an expert temporary structure engineer acting as an Independent Design Checker (IDC) for a Hong Kong structural engineering submission. Analyze the provided temporary work design and produce a formal design verification report in the style of a Hong Kong Housing Authority (HKHA) ICU submission report.

Requirements:
- Use formal engineering language consistent with HKHA ICU submission reports.
- Organize the report with clear Markdown headings (# for main sections, ## for sub-sections) based on the ACTUAL content provided. Do NOT invent sections that are not supported by the input material.
- Where applicable, reference Hong Kong design codes.
- Include an Executive Summary.
- Classify any issues found as Critical, Major, or Minor.
- Provide actionable Recommendations.
- Do not issue engineering PASS/FAIL or Satisfactory/Unsatisfactory conclusions. Use "AI Observation: Appears adequate / Requires review / Insufficient information" with brief justification.
- Do not keep the report high-level only. For every major section, include specific IDC reviewer comments on adequacy, assumptions, missing information, and follow-up actions.
- Even where the design appears generally acceptable, provide multiple concrete review comments rather than only saying it is satisfactory.
- Cover the temporary works review in a practical IDC sequence where supported by the submission: Executive Summary, Reference Codes, Design Parameters and Assumptions, Loading, Member Checks, Stability/Bracing, Bearing/Support/Connection Checks, Construction or usage limitations, Recommendations, and Conclusion.
- Use this reporting pattern for each major section:
  ## Section Title
  **AI Observation:** Appears adequate / Requires review / Insufficient information
  **IDC Reviewer Comments:**
  - at least 3 concrete review comments
  - each comment must mention actual submitted parameters, member names, drawings, calculations, assumptions, or missing information whenever available
  - comments must say what is acceptable, what is unclear, and what follow-up is required
- Include at least 15 substantive IDC reviewer comments across the whole report.
- For temporary works, explicitly comment on loading assumptions, member adequacy, lateral stability/bracing, support/bearing conditions, connection details, and operational limitations whenever the submission gives enough information.
- Prefer specific engineering observations over generic wording. Quote actual loads, sizes, spans, material grades, code clauses, or calculation references whenever those appear in the source text.
- If information is not available in the design content, state "Not covered in submitted documents" rather than inventing data.

Design Content:
{content}"""


def estimate_tokens(text_length: int) -> int:
    """Estimate token usage for English-heavy prompts and reports."""
    return max(1, int(text_length / 4))


def get_safe_length(text: str, max_tokens: int, prompt: str) -> int:
    """Reserve output space and return a safe input size."""
    system_tokens = estimate_tokens(len(prompt.replace("{content}", "")))
    available = max_tokens - system_tokens - 4000
    if available <= 1000:
        return 0
    return min(len(text), available * 4)


def extract_report_metadata(source_text: str, pdf_path: str) -> dict[str, str]:
    """Extract best-effort project metadata from the source PDF text."""
    cleaned = source_text.replace("\r", "")
    lines = [line.strip() for line in cleaned.splitlines()]

    project_title = ""
    checked_item = ""
    job_reference = os.path.splitext(os.path.basename(pdf_path))[0]

    for index, line in enumerate(lines):
        if line.lower().startswith("project:"):
            for candidate in lines[index + 1 : index + 5]:
                if candidate and not candidate.lower().startswith(("items:", "calc.", "sheet:", "ref")):
                    project_title = candidate
                    break
            if project_title:
                break

    submission_match = re.search(
        r"This submission is for\s+(.+?)(?:\.\s| in the captioned project|$)",
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if submission_match:
        checked_item = re.sub(r"\s+", " ", submission_match.group(1)).strip()
        checked_item = re.sub(r"^the\s+", "", checked_item, flags=re.IGNORECASE)

    calc_match = re.search(r"\b([A-Z0-9]{2,}(?:-[A-Z0-9]{2,})+)\b", cleaned)
    if calc_match:
        job_reference = calc_match.group(1).strip()
    else:
        for index, line in enumerate(lines):
            if line.lower().startswith("calc. no."):
                for candidate in lines[index + 1 : index + 4]:
                    if re.fullmatch(r"[A-Z0-9]{2,}(?:-[A-Z0-9]{2,})+", candidate):
                        job_reference = candidate
                        break
                break

    if not checked_item:
        for candidate in lines:
            if candidate.lower().startswith("design of "):
                checked_item = candidate
                break

    if not project_title:
        project_title = checked_item or job_reference

    return {
        "project_title": project_title,
        "checked_item": checked_item,
        "job_reference": job_reference,
    }


class Checker:
    """Standard checker for text-based PDFs."""

    def __init__(self, model_name: str | None = None, provider: str | None = None):
        self.llm_config = get_llm_config(provider, model_name)
        self.model = self.llm_config.model
        self.provider = self.llm_config.provider
        self.max_context = self.llm_config.max_context
        self.max_output = self.llm_config.max_output
        self.last_report_file: str | None = None
        self.last_extraction: DocumentExtraction | None = None
        self.last_ai_observations: list[str] = []
        self.last_review_run = None
        self.last_json_file: str | None = None
        self.last_standard_package_file: str | None = None
        self.last_normalized_submission = None
        self.last_comments = []
        self.last_executive_summary = ""

        logger.info("Using %s API", get_provider_label(self.provider))
        logger.info("Model: %s", self.model)

    def extract(self, pdf_path: str) -> tuple[Optional[str], int]:
        """Compatibility wrapper around page-preserving extraction."""
        try:
            self.last_extraction = ingest_pdf(pdf_path)
            return self.last_extraction.full_text, self.last_extraction.embedded_images
        except Exception as exc:
            logger.error("Extraction error: %s", exc)
            return None, 0

    def call_api(self, prompt: str) -> Optional[str]:
        """Call the Grok API."""
        try:
            estimated = estimate_tokens(len(prompt))
            print(f"Provider: {self.provider.upper()}")
            print(f"Model: {self.model}")
            print(f"Max context: {self.max_context:,} tokens")
            print(f"Estimated: {estimated:,} tokens")

            if estimated > self.max_context:
                print(f"ERROR: Input is too large ({estimated:,} > {self.max_context:,})")
                return None

            print(f"Calling {get_provider_label(self.provider)} API...")
            message, result = call_chat_completion(
                prompt,
                provider=self.provider,
                model_name=self.model,
                max_tokens=self.max_output,
            )
            if "usage" in result:
                print(f"Tokens used: {result['usage'].get('total_tokens', 0):,}")
            return message
        except Exception as exc:
            print(f"API error: {exc}")
            return None

    def analyze(self, content: str, struct_type: str) -> Optional[str]:
        """Compatibility path for callers that provide text instead of pages."""
        prompt = BUILDING_PROMPT if struct_type == "building" else TEMPORARY_PROMPT
        safe_len = get_safe_length(content, self.max_context, prompt)
        if safe_len <= 0:
            print("ERROR: Content is too large for the selected model.")
            return None

        truncated = content[:safe_len]
        if len(content) > safe_len:
            print(f"Truncated input: {len(content):,} -> {safe_len:,} chars")

        return self.call_api(prompt.format(content=truncated))

    def analyze_document(
        self,
        extraction: DocumentExtraction,
        struct_type: str,
        *,
        critic: bool = False,
        critic_provider: str | None = None,
    ) -> Optional[str]:
        """Classify the submission, then review calculation/supporting pages only."""
        self.last_normalized_submission = normalize_submission(extraction, struct_type)
        calculation_extraction = review_extraction(extraction, self.last_normalized_submission)
        prompt = profile_prompt(struct_type)
        max_chars = get_safe_length(calculation_extraction.full_text, self.max_context, prompt)
        critic_call = None
        if critic:
            selected_provider = critic_provider or self.provider

            def critic_call(critic_prompt: str) -> str | None:
                message, _result = call_chat_completion(
                    critic_prompt,
                    provider=selected_provider,
                    max_tokens=self.max_output,
                )
                return message

        result, observations, covered, missing, executive_summary, comments = review_document(
            calculation_extraction,
            prompt,
            self.call_api,
            max_input_chars=max_chars,
            critic=critic,
            call_critic=critic_call,
            declared_code_text=extraction.full_text,
        )
        self.last_ai_observations = observations
        self.last_comments = comments
        self.last_executive_summary = executive_summary
        if missing:
            logger.warning("Unprocessed or unreadable PDF pages: %s", missing)
        logger.info("Calculation-focused PDF pages: %s", covered)
        return result

    def check(
        self,
        pdf_path: str,
        struct_type: str = "building",
        output_dir: str | None = None,
        *,
        critic: bool = False,
        critic_provider: str | None = None,
        jurisdiction: str = "HK",
        code_pack: str = "auto",
        code_as_of: str | None = None,
        export_json: bool = False,
        input_overrides: str | None = None,
    ) -> bool:
        """Run the full standard analysis flow."""
        self.last_report_file = None
        self.last_standard_package_file = None
        print(f"\nAnalyzing: {pdf_path}")
        if not os.path.exists(pdf_path):
            print(f"ERROR: File not found: {pdf_path}")
            return False

        content, images = self.extract(pdf_path)
        extraction = self.last_extraction
        if not content or not content.strip() or not extraction:
            print("ERROR: Could not extract readable text from the PDF.")
            return False

        try:
            resolve_code_basis(extraction, jurisdiction=jurisdiction, requested_pack_id=code_pack, code_as_of=code_as_of)
        except (FileNotFoundError, ValueError) as exc:
            print(f"ERROR: Code basis is invalid: {exc}")
            return False

        print(f"Content: {len(content):,} chars, {images} images")
        print(f"Estimated: ~{estimate_tokens(len(content)):,} tokens")
        metadata = extract_report_metadata(content, pdf_path)

        print(f"Pages: {extraction.page_count}; readable: {len(extraction.processed_pages)}")
        result = self.analyze_document(
            extraction,
            struct_type,
            critic=critic,
            critic_provider=critic_provider,
        )
        if not result:
            return False

        report_dir = output_dir or os.path.dirname(pdf_path) or "."
        os.makedirs(report_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        report_file = os.path.join(report_dir, f"{base_name}_report.docx")

        try:
            review_run = create_review_run(
                extraction,
                jurisdiction=jurisdiction,
                code_pack_id=code_pack,
                code_as_of=code_as_of,
                input_overrides=input_overrides,
                ai_observations=self.last_ai_observations,
                submission_structure=self.last_normalized_submission,
                comments=self.last_comments,
                executive_summary=self.last_executive_summary,
                provider=self.provider,
                model=self.model,
            )
        except (FileNotFoundError, ValueError, TypeError) as exc:
            print(f"ERROR: Code basis or deterministic input is invalid: {exc}")
            return False
        self.last_review_run = review_run
        package_path = os.path.join(report_dir, f"{base_name}_standard_package.zip")
        create_standard_package(review_run, extraction, package_path)
        self.last_standard_package_file = package_path
        print(f"[OK] Standard package saved: {package_path}")
        if export_json:
            json_path = os.path.join(report_dir, f"{base_name}_review.json")
            export_review_json(review_run, json_path)
            self.last_json_file = json_path
            print(f"[OK] Structured result saved: {json_path}")

        try:
            from report_generator import generate_report_docx

            generate_report_docx(
                content=result,
                pdf_path=pdf_path,
                struct_type=struct_type,
                output_path=report_file,
                model=self.model,
                provider=self.provider,
                project_title=metadata["project_title"],
                checked_item=metadata["checked_item"],
                job_reference=metadata["job_reference"],
                review_run=review_run,
            )
            self.last_report_file = report_file
            print(f"\n[OK] Report saved: {report_file}")
            print(f"\nPreview:\n{result[:600]}...")
            return True
        except Exception as exc:
            logger.error("Report generation error: %s", exc)
            # Fallback to plain text if docx generation fails
            fallback_file = os.path.join(report_dir, f"{base_name}_report.txt")
            with open(fallback_file, "w", encoding="utf-8") as report:
                report.write(
                    f"""STRUCTURAL DESIGN VERIFICATION REPORT
======================================
File: {pdf_path}
Type: {struct_type.title()}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Provider: {self.provider.upper()}
Model: {self.model}

{result}

---
Generated by IDC
"""
                )
            self.last_report_file = fallback_file
            print(f"\n[WARNING] DOCX generation failed ({exc}). Fallback report saved: {fallback_file}")
            return True


def main():
    parser = argparse.ArgumentParser(description="IDC - Structural Design Checker")
    parser.add_argument("pdf_file", help="PDF file to analyze")
    parser.add_argument("--type", choices=["building", "temporary"], default="building")
    parser.add_argument("--output-dir", default="./reports")
    parser.add_argument("--model", default=None)
    parser.add_argument("--provider", choices=["grok", "kimi"], default=None)
    parser.add_argument("--jurisdiction", default="HK")
    parser.add_argument("--code-pack", default="auto", help="auto prefers report-declared codes; or pin an exact pack ID")
    parser.add_argument("--code-as-of", default=None, help="Pinned code-basis date (YYYY-MM-DD)")
    parser.add_argument("--export-json", action="store_true", help="Write a structured review JSON file")
    parser.add_argument("--input-overrides", default=None, help="Reviewer-confirmed facts/evidence JSON")
    parser.add_argument("--critic", action="store_true", help="Enable a non-authoritative second AI review")
    parser.add_argument("--critic-provider", choices=["grok", "kimi"], default=None)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    try:
        checker = Checker(model_name=args.model, provider=args.provider)
        success = checker.check(
            args.pdf_file,
            args.type,
            args.output_dir,
            critic=args.critic,
            critic_provider=args.critic_provider,
            jurisdiction=args.jurisdiction,
            code_pack=args.code_pack,
            code_as_of=args.code_as_of,
            export_json=args.export_json,
            input_overrides=args.input_overrides,
        )
        sys.exit(0 if success else 1)
    except Exception as exc:
        print(f"Error: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
