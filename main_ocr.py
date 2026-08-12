"""IDC checker with OCR support."""

import argparse
import logging
import os
import re
import sys
from datetime import datetime
from typing import Optional

from PIL import Image

from config import (
    call_chat_completion,
    get_llm_config,
    get_provider_label,
)
from idc.code_basis import resolve_code_basis
from idc.ingestion import DocumentExtraction, ingest_pdf
from idc.llm_review import review_document
from idc.pipeline import create_review_run, deterministic_summary, export_review_json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("idc_ocr.log", encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

try:
    import pytesseract

    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    logger.warning("pytesseract not installed.")

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


def check_tesseract():
    """Check if Tesseract is installed and configure its path."""
    if not PYTESSERACT_AVAILABLE:
        return False

    configured_path = os.environ.get("IDC_TESSERACT_CMD") or os.environ.get("TESSERACT_CMD")
    possible_paths = [
        configured_path,
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        rf"C:\Users\{os.environ.get('USERNAME', '')}\AppData\Local\Tesseract-OCR\tesseract.exe",
    ]

    try:
        version = pytesseract.get_tesseract_version()
        logger.info("Tesseract found in PATH, version: %s", version)
        return True
    except Exception:
        for path in possible_paths:
            if not path or not os.path.exists(path):
                continue
            pytesseract.pytesseract.tesseract_cmd = path
            try:
                version = pytesseract.get_tesseract_version()
                logger.info("Tesseract found at: %s, version: %s", path, version)
                return True
            except Exception:
                continue

    logger.warning("Tesseract not found in PATH or common locations")
    return False


TESSERACT_AVAILABLE = check_tesseract()


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


class OCRExtractor:
    """OCR helper backed by Tesseract."""

    def __init__(self):
        self.available = TESSERACT_AVAILABLE
        self.language = os.environ.get("IDC_OCR_LANG", "chi_sim+eng")
        if self.available:
            print(f"Tesseract OCR initialized (lang: {self.language})")
        else:
            print("WARNING: Tesseract not available. Install from: https://github.com/UB-Mannheim/tesseract/wiki")

    def extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text from a PIL image."""
        if not self.available:
            return ""
        try:
            return pytesseract.image_to_string(image, lang=self.language)
        except Exception as exc:
            logger.error("OCR error: %s", exc)
            return ""


class CheckerOCR:
    """Checker with OCR fallback for scanned documents."""

    def __init__(self, model_name: str | None = None, provider: str | None = None, use_ocr: bool = True):
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

        self.ocr_extractor = OCRExtractor() if use_ocr else None

        logger.info("Using %s API", get_provider_label(self.provider))
        logger.info("Model: %s", self.model)
        logger.info("OCR Enabled: %s", bool(self.ocr_extractor and self.ocr_extractor.available))

    def extract(self, pdf_path: str, force_ocr: bool = False) -> tuple[Optional[str], int, bool]:
        """Compatibility wrapper around page-preserving OCR extraction."""
        try:
            self.last_extraction = ingest_pdf(
                pdf_path,
                ocr=self.ocr_extractor,
                force_ocr=force_ocr,
            )
            if self.last_extraction.used_ocr:
                print("OCR was used for some pages.")
            return (
                self.last_extraction.full_text or None,
                self.last_extraction.embedded_images,
                self.last_extraction.used_ocr,
            )
        except Exception as exc:
            logger.error("Extraction error: %s", exc)
            return None, 0, False

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
        """Build the prompt and request the analysis."""
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
        """Review all readable pages and retain coverage disclosure."""
        prompt = BUILDING_PROMPT if struct_type == "building" else TEMPORARY_PROMPT
        max_chars = get_safe_length(extraction.full_text, self.max_context, prompt)
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

        result, observations, covered, missing = review_document(
            extraction,
            prompt,
            self.call_api,
            max_input_chars=max_chars,
            critic=critic,
            call_critic=critic_call,
        )
        self.last_ai_observations = observations
        if missing:
            logger.warning("Unprocessed or unreadable PDF pages: %s", missing)
        logger.info("Reviewed PDF pages: %s", covered)
        return result

    def check(
        self,
        pdf_path: str,
        struct_type: str = "building",
        output_dir: str | None = None,
        force_ocr: bool = False,
        critic: bool = False,
        critic_provider: str | None = None,
        jurisdiction: str = "HK",
        code_pack: str = "auto",
        code_as_of: str | None = None,
        export_json: bool = False,
        input_overrides: str | None = None,
    ) -> bool:
        """Run the full OCR analysis flow."""
        self.last_report_file = None
        print(f"\nAnalyzing: {pdf_path}")
        if not os.path.exists(pdf_path):
            print(f"ERROR: File not found: {pdf_path}")
            return False

        content, images, used_ocr = self.extract(pdf_path, force_ocr)
        extraction = self.last_extraction
        if not content or not extraction:
            print("ERROR: Could not extract text from the PDF.")
            return False

        try:
            resolve_code_basis(extraction, jurisdiction=jurisdiction, requested_pack_id=code_pack, code_as_of=code_as_of)
        except (FileNotFoundError, ValueError) as exc:
            print(f"ERROR: Code basis is invalid: {exc}")
            return False

        print(f"Content: {len(content):,} chars, {images} images")
        print(f"OCR Used: {used_ocr}")
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
        report_file = os.path.join(report_dir, f"{base_name}_OCR_report.docx")

        try:
            review_run = create_review_run(
                extraction,
                jurisdiction=jurisdiction,
                code_pack_id=code_pack,
                code_as_of=code_as_of,
                input_overrides=input_overrides,
                ai_observations=self.last_ai_observations,
                provider=self.provider,
                model=self.model,
            )
        except (FileNotFoundError, ValueError, TypeError) as exc:
            print(f"ERROR: Code basis or deterministic input is invalid: {exc}")
            return False
        self.last_review_run = review_run
        result = deterministic_summary(review_run) + result
        if export_json:
            json_path = os.path.join(report_dir, f"{base_name}_OCR_review.json")
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
                used_ocr=used_ocr,
                project_title=metadata["project_title"],
                checked_item=metadata["checked_item"],
                job_reference=metadata["job_reference"],
            )
            self.last_report_file = report_file
            print(f"\n[OK] Report saved: {report_file}")
            print(f"\nPreview:\n{result[:600]}...")
            return True
        except Exception as exc:
            logger.error("Report generation error: %s", exc)
            # Fallback to plain text if docx generation fails
            fallback_file = os.path.join(report_dir, f"{base_name}_OCR_report.txt")
            ocr_note = " (OCR enabled)" if used_ocr else ""
            with open(fallback_file, "w", encoding="utf-8") as report:
                report.write(
                    f"""STRUCTURAL DESIGN VERIFICATION REPORT{ocr_note}
==================================================
File: {pdf_path}
Type: {struct_type.title()}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Provider: {self.provider.upper()}
Model: {self.model}
OCR Used: {used_ocr}

{result}

---
Generated by IDC with OCR Support
"""
                )
            self.last_report_file = fallback_file
            print(f"\n[WARNING] DOCX generation failed ({exc}). Fallback report saved: {fallback_file}")
            return True


def main():
    parser = argparse.ArgumentParser(
        description="IDC - Structural Design Checker with OCR Support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  IDC_CLI_OCR.exe "design.pdf" --type building
  IDC_CLI_OCR.exe "scanned.pdf" --type building --force-ocr
  IDC_CLI_OCR.exe "design.pdf" --type temporary --output-dir ./reports

OCR requires Tesseract:
  https://github.com/UB-Mannheim/tesseract/wiki
        """,
    )
    parser.add_argument("pdf_file", help="PDF file to analyze")
    parser.add_argument("--type", choices=["building", "temporary"], default="building")
    parser.add_argument("--output-dir", default="./reports")
    parser.add_argument("--model", default=None, help="Model to use (overrides config)")
    parser.add_argument("--provider", choices=["grok", "kimi"], default=None, help="API provider to use")
    parser.add_argument("--force-ocr", action="store_true", help="Force OCR for all pages")
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR and use only text extraction")
    parser.add_argument("--jurisdiction", default="HK")
    parser.add_argument("--code-pack", default="auto", help="auto prefers report-declared codes; or pin an exact pack ID")
    parser.add_argument("--code-as-of", default=None, help="Pinned code-basis date (YYYY-MM-DD)")
    parser.add_argument("--export-json", action="store_true", help="Write a structured review JSON file")
    parser.add_argument("--input-overrides", default=None, help="Reviewer-confirmed facts/evidence JSON")
    parser.add_argument("--critic", action="store_true", help="Enable a non-authoritative second AI review")
    parser.add_argument("--critic-provider", choices=["grok", "kimi"], default=None)
    args = parser.parse_args()

    if not TESSERACT_AVAILABLE and not args.no_ocr:
        print("=" * 60)
        print("WARNING: OCR is not available.")
        print("=" * 60)
        print("Install Tesseract to enable OCR:")
        print("  https://github.com/UB-Mannheim/tesseract/wiki")
        print("\nContinuing with text-layer extraction only...\n")

    os.makedirs(args.output_dir, exist_ok=True)

    try:
        checker = CheckerOCR(model_name=args.model, provider=args.provider, use_ocr=not args.no_ocr)
        success = checker.check(
            args.pdf_file,
            args.type,
            args.output_dir,
            force_ocr=args.force_ocr,
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
