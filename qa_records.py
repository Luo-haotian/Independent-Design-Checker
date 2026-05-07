"""Batch QA records checker for certificates and test reports."""

from __future__ import annotations

import csv
import json
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import fitz
import requests
from PIL import Image

from config import API_KEY, API_PROVIDER, API_URL, MODEL_NAME, TEMPERATURE, check_api_key
from main_ocr import OCRExtractor


QA_RECORD_FIELDS = [
    "source_file",
    "document_type",
    "project_name",
    "supplier_or_lab",
    "certificate_or_report_no",
    "material_type",
    "grade",
    "test_date",
    "delivery_or_pour_date",
    "batch_heat_bar_cube_or_sample_id",
    "result_value",
    "pass_fail_status",
    "page_reference",
    "confidence",
    "missing_fields",
    "remarks",
]

QA_EXTRACT_PROMPT = """You are a construction QA/QC document controller and structural engineering assistant.
Extract a register row from the submitted QA record.

Supported document types:
- OP
- Mill Certificate
- Concrete Cube Test
- Reinforcement Test
- Other

Return ONLY valid JSON with this schema:
{
  "document_type": "OP | Mill Certificate | Concrete Cube Test | Reinforcement Test | Other",
  "project_name": "",
  "supplier_or_lab": "",
  "certificate_or_report_no": "",
  "material_type": "",
  "grade": "",
  "test_date": "",
  "delivery_or_pour_date": "",
  "batch_heat_bar_cube_or_sample_id": "",
  "result_value": "",
  "pass_fail_status": "Pass | Fail | Not stated | Unknown",
  "page_reference": "",
  "confidence": 0.0,
  "missing_fields": [],
  "remarks": ""
}

Rules:
- Do not invent missing values.
- Use "Unknown" or an empty string where the source is unclear.
- Put any required-but-missing register fields in missing_fields.
- If a result appears non-conforming, expired, duplicated, unclear, or incomplete, explain in remarks.
- Keep values concise and suitable for a CSV register.

Source file: {filename}
Extracted text:
{content}
"""


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(str(item).strip() for item in value if str(item).strip())
    return re.sub(r"\s+", " ", str(value)).strip()


def extract_pdf_text(pdf_path: Path, ocr_mode: str = "auto") -> tuple[str, bool, int]:
    """Extract text from a PDF with optional Tesseract OCR fallback."""
    use_ocr = ocr_mode != "no-ocr"
    force_ocr = ocr_mode == "force"
    ocr = OCRExtractor() if use_ocr else None
    used_ocr = False
    pages = 0
    parts: list[str] = []

    doc = fitz.open(pdf_path)
    try:
        pages = len(doc)
        for page_index, page in enumerate(doc, start=1):
            page_text = page.get_text()
            should_ocr = force_ocr or len(page_text.strip()) < 40
            if should_ocr and ocr and ocr.available:
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr_text = ocr.extract_text_from_image(image)
                if ocr_text.strip():
                    parts.append(f"--- Page {page_index} OCR ---\n{ocr_text}")
                    used_ocr = True
                    continue

            if page_text.strip():
                parts.append(f"--- Page {page_index} ---\n{page_text}")
    finally:
        doc.close()

    return "\n\n".join(parts), used_ocr, pages


def _extract_json_object(raw: str) -> dict[str, Any]:
    """Parse a model JSON response, tolerating fenced output."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def call_qa_model(filename: str, content: str, model_name: str | None = None) -> dict[str, Any]:
    """Ask the configured model to extract one QA register row."""
    check_api_key()
    model = model_name or MODEL_NAME
    prompt = QA_EXTRACT_PROMPT.format(filename=filename, content=content[:24000])
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1600,
        "temperature": TEMPERATURE,
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    response = requests.post(API_URL, headers=headers, json=payload, timeout=180)
    if response.status_code != 200:
        raise RuntimeError(f"{API_PROVIDER.upper()} API error {response.status_code}: {response.text[:240]}")
    message = response.json()["choices"][0]["message"]["content"]
    return _extract_json_object(message)


def normalize_record(source_file: str, extracted: dict[str, Any]) -> dict[str, str]:
    """Normalize one extracted model result to the CSV register schema."""
    row = {field: "" for field in QA_RECORD_FIELDS}
    row["source_file"] = source_file
    for field in QA_RECORD_FIELDS:
        if field == "source_file":
            continue
        row[field] = _safe_text(extracted.get(field))
    if not row["confidence"]:
        row["confidence"] = "0"
    return row


def exception_from_record(row: dict[str, str]) -> dict[str, str] | None:
    """Create an exception row when a record needs human attention."""
    reasons: list[str] = []
    if row["document_type"] in {"", "Other", "Unknown"}:
        reasons.append("document type is unclear")
    if row["missing_fields"]:
        reasons.append(f"missing fields: {row['missing_fields']}")
    if row["pass_fail_status"].lower() in {"fail", "failed", "unsatisfactory"}:
        reasons.append("result appears to fail")
    if row["remarks"]:
        lowered = row["remarks"].lower()
        keywords = ["missing", "unclear", "non-conforming", "expired", "duplicate", "fail", "not stated"]
        if any(keyword in lowered for keyword in keywords):
            reasons.append(row["remarks"])

    if not reasons:
        return None
    return {
        "source_file": row["source_file"],
        "document_type": row["document_type"],
        "issue": "; ".join(dict.fromkeys(reasons)),
        "recommended_action": "Review the source document and confirm the register entry before acceptance.",
    }


def collect_pdf_inputs(input_dir: Path, work_dir: Path) -> list[Path]:
    """Collect PDFs from uploaded files and safely extract ZIP packages."""
    pdfs: list[Path] = []
    extract_dir = work_dir / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)

    for path in input_dir.iterdir():
        if path.suffix.lower() == ".pdf":
            pdfs.append(path)
            continue
        if path.suffix.lower() != ".zip":
            continue

        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                member_name = member.filename.replace("\\", "/")
                if member.is_dir() or not member_name.lower().endswith(".pdf"):
                    continue
                target_name = Path(member_name).name
                if not target_name:
                    continue
                target = extract_dir / f"{path.stem}_{target_name}"
                with archive.open(member) as source, open(target, "wb") as output:
                    output.write(source.read())
                pdfs.append(target)

    return sorted(pdfs, key=lambda item: item.name.lower())


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    """Write CSV output with a UTF-8 BOM for Excel compatibility."""
    with open(path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_qa_batch(
    input_dir: Path,
    output_dir: Path,
    *,
    ocr_mode: str = "auto",
    model_name: str | None = None,
    log_callback=None,
) -> dict[str, Any]:
    """Process uploaded QA records and produce register, exception, and raw JSON outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pdfs = collect_pdf_inputs(input_dir, output_dir)
    if not pdfs:
        raise ValueError("No PDF files were found in the upload.")

    register_rows: list[dict[str, str]] = []
    exception_rows: list[dict[str, str]] = []
    raw_results: list[dict[str, Any]] = []

    for index, pdf_path in enumerate(pdfs, start=1):
        if log_callback:
            log_callback(f"Processing QA record {index}/{len(pdfs)}: {pdf_path.name}")
        text, used_ocr, page_count = extract_pdf_text(pdf_path, ocr_mode=ocr_mode)
        if not text.strip():
            row = normalize_record(pdf_path.name, {"document_type": "Unknown", "missing_fields": ["readable text"], "remarks": "No readable text could be extracted."})
        else:
            extracted = call_qa_model(pdf_path.name, text, model_name=model_name)
            row = normalize_record(pdf_path.name, extracted)

        row["remarks"] = _safe_text(row["remarks"])
        register_rows.append(row)
        issue = exception_from_record(row)
        if issue:
            exception_rows.append(issue)
        raw_results.append(
            {
                "source_file": pdf_path.name,
                "used_ocr": used_ocr,
                "page_count": page_count,
                "register_row": row,
            }
        )

    register_path = output_dir / "qa_register.csv"
    exceptions_path = output_dir / "qa_exceptions.csv"
    raw_path = output_dir / "qa_raw_results.json"
    summary_path = output_dir / "qa_summary.txt"
    package_path = output_dir / "qa_records_output.zip"

    write_csv(register_path, register_rows, QA_RECORD_FIELDS)
    write_csv(exceptions_path, exception_rows, ["source_file", "document_type", "issue", "recommended_action"])
    with open(raw_path, "w", encoding="utf-8") as handle:
        json.dump(raw_results, handle, indent=2, ensure_ascii=False)
    with open(summary_path, "w", encoding="utf-8") as handle:
        handle.write(
            "\n".join(
                [
                    "QA Records Batch Checker Summary",
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    f"Processed files: {len(register_rows)}",
                    f"Exceptions: {len(exception_rows)}",
                    f"OCR mode: {ocr_mode}",
                    "",
                    "Outputs:",
                    f"- {register_path.name}",
                    f"- {exceptions_path.name}",
                    f"- {raw_path.name}",
                ]
            )
        )

    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for output in [register_path, exceptions_path, raw_path, summary_path]:
            archive.write(output, arcname=output.name)

    return {
        "processed": len(register_rows),
        "exceptions": len(exception_rows),
        "register_path": str(register_path),
        "exceptions_path": str(exceptions_path),
        "raw_path": str(raw_path),
        "summary_path": str(summary_path),
        "package_path": str(package_path),
    }
