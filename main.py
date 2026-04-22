"""IDC standard PDF checker."""

import argparse
import logging
import os
import re
import sys
from datetime import datetime
from typing import Optional

import fitz
import requests

from config import (
    API_KEY,
    API_PROVIDER,
    API_URL,
    MODEL_CONFIGS,
    MODEL_NAME,
    TEMPERATURE,
    check_api_key,
)

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
- For each design check, state whether it is Satisfactory or Unsatisfactory with brief justification.
- Do not keep the report high-level only. For every major section, include specific IDC reviewer comments on adequacy, assumptions, missing information, and follow-up actions.
- Even where the design appears generally acceptable, provide multiple concrete review comments rather than only saying it is satisfactory.
- Use this reporting pattern for each major section where supported by the submitted material:
  ## Section Title
  **IDC Check:** Satisfactory / Unsatisfactory
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
- For each design check, state whether it is Satisfactory or Unsatisfactory with brief justification.
- Do not keep the report high-level only. For every major section, include specific IDC reviewer comments on adequacy, assumptions, missing information, and follow-up actions.
- Even where the design appears generally acceptable, provide multiple concrete review comments rather than only saying it is satisfactory.
- Cover the temporary works review in a practical IDC sequence where supported by the submission: Executive Summary, Reference Codes, Design Parameters and Assumptions, Loading, Member Checks, Stability/Bracing, Bearing/Support/Connection Checks, Construction or usage limitations, Recommendations, and Conclusion.
- Use this reporting pattern for each major section:
  ## Section Title
  **IDC Check:** Satisfactory / Unsatisfactory
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

    def __init__(self, model_name: str | None = None):
        check_api_key()
        self.api_key = API_KEY
        self.api_url = API_URL
        self.model = model_name or MODEL_NAME
        self.provider = API_PROVIDER

        config = MODEL_CONFIGS.get(self.model, MODEL_CONFIGS[MODEL_NAME])
        self.max_context = config["max_context"]
        self.max_output = config["max_output"]
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self.last_report_file: str | None = None

        logger.info("Using %s API", self.provider.upper())
        logger.info("Model: %s", self.model)

    def extract(self, pdf_path: str) -> tuple[Optional[str], int]:
        """Extract text and count embedded images."""
        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            images = 0
            for page in doc:
                text_parts.append(page.get_text())
                images += len(page.get_images())
            doc.close()
            return "\n".join(text_parts), images
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

            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.max_output,
                "temperature": TEMPERATURE,
            }

            print(f"Calling {self.provider.upper()} API...")
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=180,
            )

            if response.status_code == 200:
                result = response.json()
                if "usage" in result:
                    print(f"Tokens used: {result['usage'].get('total_tokens', 0):,}")
                return result["choices"][0]["message"]["content"]

            if response.status_code == 401:
                print("ERROR 401: Invalid Grok API key.")
                return None

            print(f"API Error {response.status_code}: {response.text[:200]}")
            return None
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

    def check(self, pdf_path: str, struct_type: str = "building", output_dir: str | None = None) -> bool:
        """Run the full standard analysis flow."""
        self.last_report_file = None
        print(f"\nAnalyzing: {pdf_path}")
        if not os.path.exists(pdf_path):
            print(f"ERROR: File not found: {pdf_path}")
            return False

        content, images = self.extract(pdf_path)
        if not content or not content.strip():
            print("ERROR: Could not extract readable text from the PDF.")
            return False

        print(f"Content: {len(content):,} chars, {images} images")
        print(f"Estimated: ~{estimate_tokens(len(content)):,} tokens")
        metadata = extract_report_metadata(content, pdf_path)

        result = self.analyze(content, struct_type)
        if not result:
            return False

        report_dir = output_dir or os.path.dirname(pdf_path) or "."
        os.makedirs(report_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        report_file = os.path.join(report_dir, f"{base_name}_report.docx")

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
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    try:
        checker = Checker(model_name=args.model)
        success = checker.check(args.pdf_file, args.type, args.output_dir)
        sys.exit(0 if success else 1)
    except Exception as exc:
        print(f"Error: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
