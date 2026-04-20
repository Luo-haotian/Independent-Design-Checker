"""IDC standard PDF checker."""

import argparse
import logging
import os
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

        result = self.analyze(content, struct_type)
        if not result:
            return False

        report_dir = output_dir or os.path.dirname(pdf_path) or "."
        os.makedirs(report_dir, exist_ok=True)
        report_file = os.path.join(
            report_dir,
            f"{os.path.splitext(os.path.basename(pdf_path))[0]}_report.txt",
        )

        with open(report_file, "w", encoding="utf-8") as report:
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

        print(f"\n[OK] Report saved: {report_file}")
        print(f"\nPreview:\n{result[:600]}...")
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
