"""IDC checker with OCR support."""

import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Optional

import fitz
import requests
from PIL import Image

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
    handlers=[logging.FileHandler("idc_ocr.log", encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

try:
    import pytesseract

    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    logger.warning("pytesseract not installed.")

BUILDING_PROMPT = """You are an expert structural engineer. Analyze this building design:

Check: Calculations, Structural System, Loading, Materials, Code Compliance, Safety

Output format:
1. Executive Summary
2. Detailed Analysis by Category
3. Calculation Verification Results
4. Issues (Critical/Major/Minor)
5. Overall Compliance Status
6. Recommendations

Design Content:
{content}"""

TEMPORARY_PROMPT = """You are an expert temporary structure engineer. Analyze this temporary work design:

Check: Calculations, Construction Loads, Safety Measures, Weather Resistance, Duration, Materials

Output format:
1. Executive Summary
2. Detailed Analysis by Category
3. Calculation Verification Results
4. Issues (Critical/Major/Minor)
5. Safety Compliance Status
6. Recommendations

Design Content:
{content}"""


def check_tesseract():
    """Check if Tesseract is installed and configure its path."""
    if not PYTESSERACT_AVAILABLE:
        return False

    possible_paths = [
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
            if not os.path.exists(path):
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


class OCRExtractor:
    """OCR helper backed by Tesseract."""

    def __init__(self):
        self.available = TESSERACT_AVAILABLE
        if self.available:
            print("Tesseract OCR initialized (lang: chi_sim+eng)")
        else:
            print("WARNING: Tesseract not available. Install from: https://github.com/UB-Mannheim/tesseract/wiki")

    def extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text from a PIL image."""
        if not self.available:
            return ""
        try:
            return pytesseract.image_to_string(image, lang="chi_sim+eng")
        except Exception as exc:
            logger.error("OCR error: %s", exc)
            return ""


class CheckerOCR:
    """Checker with OCR fallback for scanned documents."""

    def __init__(self, model_name: str | None = None, use_ocr: bool = True):
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

        self.ocr_extractor = OCRExtractor() if use_ocr else None

        logger.info("Using %s API", self.provider.upper())
        logger.info("Model: %s", self.model)
        logger.info("OCR Enabled: %s", bool(self.ocr_extractor and self.ocr_extractor.available))

    def extract(self, pdf_path: str, force_ocr: bool = False) -> tuple[Optional[str], int, bool]:
        """Extract text from PDF, using OCR when needed."""
        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            images = 0
            used_ocr = False
            total_pages = len(doc)

            print(f"Processing {total_pages} pages...")

            for page_num, page in enumerate(doc, 1):
                page_text = page.get_text()
                should_use_ocr = force_ocr or len(page_text.strip()) < 50

                if should_use_ocr and self.ocr_extractor and self.ocr_extractor.available:
                    print(f"  Page {page_num}/{total_pages}: Using OCR...")
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_text = self.ocr_extractor.extract_text_from_image(image)
                    if ocr_text.strip():
                        text_parts.append(f"--- Page {page_num} (OCR) ---\n{ocr_text}")
                        used_ocr = True
                    images += 1
                else:
                    if page_text.strip():
                        text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                    print(f"  Page {page_num}/{total_pages}: Text extracted ({len(page_text)} chars)")

                images += len(page.get_images())

            doc.close()

            if used_ocr:
                print("OCR was used for some pages.")

            text = "\n\n".join(text_parts)
            return (text if text.strip() else None), images, used_ocr
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

    def check(
        self,
        pdf_path: str,
        struct_type: str = "building",
        output_dir: str | None = None,
        force_ocr: bool = False,
    ) -> bool:
        """Run the full OCR analysis flow."""
        print(f"\nAnalyzing: {pdf_path}")
        if not os.path.exists(pdf_path):
            print(f"ERROR: File not found: {pdf_path}")
            return False

        content, images, used_ocr = self.extract(pdf_path, force_ocr)
        if not content:
            print("ERROR: Could not extract text from the PDF.")
            return False

        print(f"Content: {len(content):,} chars, {images} images")
        print(f"OCR Used: {used_ocr}")
        print(f"Estimated: ~{estimate_tokens(len(content)):,} tokens")

        result = self.analyze(content, struct_type)
        if not result:
            return False

        report_dir = output_dir or os.path.dirname(pdf_path) or "."
        os.makedirs(report_dir, exist_ok=True)
        report_file = os.path.join(
            report_dir,
            f"{os.path.splitext(os.path.basename(pdf_path))[0]}_OCR_report.txt",
        )
        ocr_note = " (OCR enabled)" if used_ocr else ""

        with open(report_file, "w", encoding="utf-8") as report:
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

        print(f"\n[OK] Report saved: {report_file}")
        print(f"\nPreview:\n{result[:600]}...")
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
    parser.add_argument("--force-ocr", action="store_true", help="Force OCR for all pages")
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR and use only text extraction")
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
        checker = CheckerOCR(model_name=args.model, use_ocr=not args.no_ocr)
        success = checker.check(
            args.pdf_file,
            args.type,
            args.output_dir,
            force_ocr=args.force_ocr,
        )
        sys.exit(0 if success else 1)
    except Exception as exc:
        print(f"Error: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
