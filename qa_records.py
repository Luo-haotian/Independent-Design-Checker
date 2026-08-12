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
from PIL import Image

from config import call_chat_completion, get_default_model, get_provider_label
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
    "text_layer",
    "ocr_used",
    "low_text_pages",
    "page_count",
    "confidence_reasons",
]

QA_EXTRACT_PROMPT = """You are a construction QA/QC document controller and structural engineering assistant.
Extract a register row from the submitted QA record.

Supported document types:
- OP
- Mill Certificate
- Concrete Cube Test
- Reinforcement Certificate / Test Report
- Other

Return ONLY valid JSON with this schema:
{
  "document_type": "OP | Mill Certificate | Concrete Cube Test | Reinforcement Certificate / Test Report | Other",
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
  "remarks": "",
  "confidence_reasons": []
}

Rules:
- Do not invent missing values.
- Use "Unknown" or an empty string where the source is unclear.
- Put any required-but-missing register fields in missing_fields.
- If a result appears non-conforming, expired, duplicated, unclear, or incomplete, explain in remarks.
- For reinforcement bar submissions, prioritize heat number, cast number, bar mark, grade, diameter, test/certificate number, and pass/fail wording.
- For mill certificates, prioritize standard/grade, cast/heat/coil number, chemical/mechanical results, test date, and certificate number.
- For concrete cube reports, prioritize cast/pour date, tested date, sample/cube ID, concrete grade or mix, average compressive strength, and pass/fail or unclear status.
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


def extract_pdf_text(pdf_path: Path, ocr_mode: str = "auto") -> tuple[str, dict[str, Any]]:
    """Extract text from a PDF with optional Tesseract OCR fallback."""
    use_ocr = ocr_mode != "no-ocr"
    force_ocr = ocr_mode == "force"
    ocr = OCRExtractor() if use_ocr else None
    used_ocr = False
    pages = 0
    low_text_pages = 0
    text_layer_chars = 0
    parts: list[str] = []

    doc = fitz.open(pdf_path)
    try:
        pages = len(doc)
        for page_index, page in enumerate(doc, start=1):
            page_text = page.get_text()
            text_layer_chars += len(page_text.strip())
            should_ocr = force_ocr or len(page_text.strip()) < 40
            if len(page_text.strip()) < 40:
                low_text_pages += 1
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

    if text_layer_chars == 0:
        text_layer = "none"
    elif low_text_pages:
        text_layer = "partial"
    else:
        text_layer = "searchable"

    return "\n\n".join(parts), {
        "ocr_used": used_ocr,
        "page_count": pages,
        "low_text_pages": low_text_pages,
        "text_layer": text_layer,
        "text_layer_chars": text_layer_chars,
    }


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


def call_qa_model(filename: str, content: str, model_name: str | None = None, provider: str | None = None) -> dict[str, Any]:
    """Ask the configured model to extract one QA register row."""
    model = model_name or get_default_model(provider)
    prompt = QA_EXTRACT_PROMPT.replace("{filename}", filename).replace("{content}", content[:24000])
    message, _result = call_chat_completion(
        prompt,
        provider=provider,
        model_name=model,
        max_tokens=1600,
        timeout=180,
    )
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
    if row.get("text_layer") in {"none", "partial"} and row.get("ocr_used", "").lower() != "true":
        reasons.append("scanned or low-text PDF was not OCR processed")
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


def _format_report_table(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "| Source file | Type | OCR | Key result | Exceptions hint |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        hint = row["missing_fields"] or row["remarks"] or "None flagged"
        lines.append(
            "| "
            + " | ".join(
                _safe_text(value).replace("|", "/")
                for value in [
                    row["source_file"],
                    row["document_type"],
                    row.get("ocr_used", ""),
                    row["result_value"] or row["pass_fail_status"],
                    hint,
                ]
            )
            + " |"
        )
    return lines


def write_operator_report(
    path: Path,
    *,
    register_rows: list[dict[str, str]],
    exception_rows: list[dict[str, str]],
    ocr_mode: str,
    provider: str | None,
    model_name: str | None,
) -> None:
    """Write a plain-language operator report for the QA batch."""
    provider_label = get_provider_label(provider)
    model_label = model_name or get_default_model(provider)
    scanned_count = sum(1 for row in register_rows if row.get("text_layer") in {"none", "partial"})
    ocr_count = sum(1 for row in register_rows if row.get("ocr_used") == "True")
    doc_types = sorted({row["document_type"] or "Unknown" for row in register_rows})

    lines = [
        "# Contractor Submission Batch Review",
        "",
        "## Batch Summary",
        "",
        f"- Processed files: {len(register_rows)}",
        f"- Exception records: {len(exception_rows)}",
        f"- OCR mode selected: {ocr_mode}",
        f"- Files with low or partial text layer: {scanned_count}",
        f"- Files where OCR was used: {ocr_count}",
        f"- API provider/model: {provider_label} / {model_label}",
        f"- Document types found: {', '.join(doc_types) if doc_types else 'None'}",
        "",
        "## What The Operator Should Do",
        "",
        "1. Open `qa_register.csv` and check that every submitted PDF appears in the register.",
        "2. Open `qa_exceptions.csv` first; these rows need manual review before acceptance.",
        "3. For scanned records, compare the extracted heat, batch, bar, cube, or sample IDs against the source PDF.",
        "4. Confirm certificate/report numbers, dates, grades, and result values before using the register as an official record.",
        "5. If OCR was not used on a scanned document, rerun the batch with `Force OCR`.",
        "",
        "## Register Preview",
        "",
        *_format_report_table(register_rows),
        "",
        "## Exception Summary",
        "",
    ]
    if exception_rows:
        for issue in exception_rows:
            lines.append(f"- {issue['source_file']}: {issue['issue']}")
    else:
        lines.append("- No exception rows were generated. Still perform a spot check against source documents.")

    lines.extend(
        [
            "",
            "## Output Files",
            "",
            "- `qa_register.csv`: extracted register table",
            "- `qa_exceptions.csv`: records requiring human review",
            "- `qa_raw_results.json`: raw extraction and OCR diagnostics",
            "- `qa_summary.txt`: short machine summary",
            "- `qa_operator_report.md`: this operator-facing report",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def collect_pdf_inputs(input_dir: Path, work_dir: Path) -> list[Path]:
    """Collect PDFs from uploaded files and safely extract ZIP packages."""
    max_members = int(os.environ.get("IDC_ZIP_MAX_MEMBERS", "200"))
    max_member_bytes = int(os.environ.get("IDC_ZIP_MAX_MEMBER_MB", "100")) * 1024 * 1024
    max_total_bytes = int(os.environ.get("IDC_ZIP_MAX_TOTAL_MB", "500")) * 1024 * 1024
    max_ratio = float(os.environ.get("IDC_ZIP_MAX_RATIO", "100"))
    pdfs: list[Path] = []
    used_names: set[str] = set()
    total_uncompressed = 0
    extract_dir = work_dir / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)

    for path in input_dir.iterdir():
        if path.suffix.lower() == ".pdf":
            pdfs.append(path)
            continue
        if path.suffix.lower() != ".zip":
            continue

        with zipfile.ZipFile(path) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            if len(members) > max_members:
                raise ValueError(f"ZIP has more than {max_members} files: {path.name}")
            for member in members:
                member_name = member.filename.replace("\\", "/")
                if member.is_dir() or not member_name.lower().endswith(".pdf"):
                    continue
                if member.file_size > max_member_bytes:
                    raise ValueError(f"ZIP member exceeds the size limit: {member_name}")
                total_uncompressed += member.file_size
                if total_uncompressed > max_total_bytes:
                    raise ValueError("ZIP uncompressed PDF total exceeds the configured limit.")
                if member.compress_size == 0 and member.file_size > 0:
                    raise ValueError(f"Suspicious zero-size compressed member: {member_name}")
                if member.compress_size and member.file_size / member.compress_size > max_ratio:
                    raise ValueError(f"ZIP compression ratio exceeds the limit: {member_name}")
                target_name = Path(member_name).name
                if not target_name:
                    continue
                safe_name = f"{path.stem}_{target_name}"
                folded = safe_name.casefold()
                if folded in used_names:
                    raise ValueError(f"Duplicate archive output name: {safe_name}")
                used_names.add(folded)
                target = (extract_dir / safe_name).resolve()
                if extract_dir.resolve() not in target.parents:
                    raise ValueError(f"Unsafe ZIP member path: {member_name}")
                written = 0
                with archive.open(member) as source, open(target, "wb") as output:
                    while True:
                        block = source.read(1024 * 1024)
                        if not block:
                            break
                        written += len(block)
                        if written > max_member_bytes:
                            raise ValueError(f"Expanded ZIP member exceeds the size limit: {member_name}")
                        output.write(block)
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
    provider: str | None = None,
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
        text, ocr_meta = extract_pdf_text(pdf_path, ocr_mode=ocr_mode)
        if not text.strip():
            row = normalize_record(pdf_path.name, {"document_type": "Unknown", "missing_fields": ["readable text"], "remarks": "No readable text could be extracted."})
        else:
            extracted = call_qa_model(pdf_path.name, text, model_name=model_name, provider=provider)
            row = normalize_record(pdf_path.name, extracted)

        row["remarks"] = _safe_text(row["remarks"])
        row["text_layer"] = _safe_text(ocr_meta["text_layer"])
        row["ocr_used"] = str(bool(ocr_meta["ocr_used"]))
        row["low_text_pages"] = str(ocr_meta["low_text_pages"])
        row["page_count"] = str(ocr_meta["page_count"])
        register_rows.append(row)
        issue = exception_from_record(row)
        if issue:
            exception_rows.append(issue)
        raw_results.append(
            {
                "source_file": pdf_path.name,
                "ocr": ocr_meta,
                "register_row": row,
            }
        )

    register_path = output_dir / "qa_register.csv"
    exceptions_path = output_dir / "qa_exceptions.csv"
    raw_path = output_dir / "qa_raw_results.json"
    summary_path = output_dir / "qa_summary.txt"
    operator_report_path = output_dir / "qa_operator_report.md"
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
                    f"Provider: {get_provider_label(provider)}",
                    f"Model: {model_name or get_default_model(provider)}",
                    "",
                    "Outputs:",
                    f"- {register_path.name}",
                    f"- {exceptions_path.name}",
                    f"- {raw_path.name}",
                    f"- {operator_report_path.name}",
                ]
            )
        )
    write_operator_report(
        operator_report_path,
        register_rows=register_rows,
        exception_rows=exception_rows,
        ocr_mode=ocr_mode,
        provider=provider,
        model_name=model_name,
    )

    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for output in [register_path, exceptions_path, raw_path, summary_path, operator_report_path]:
            archive.write(output, arcname=output.name)

    return {
        "processed": len(register_rows),
        "exceptions": len(exception_rows),
        "register_path": str(register_path),
        "exceptions_path": str(exceptions_path),
        "raw_path": str(raw_path),
        "summary_path": str(summary_path),
        "operator_report_path": str(operator_report_path),
        "package_path": str(package_path),
    }
