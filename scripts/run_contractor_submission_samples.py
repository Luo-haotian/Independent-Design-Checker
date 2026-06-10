"""Run contractor submission sample checks for QA batch validation."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import get_default_model, get_provider_label, is_provider_configured  # noqa: E402
from qa_records import extract_pdf_text, run_qa_batch  # noqa: E402


REAL_SCANNED_SAMPLES = [
    BASE_DIR / "test file" / "Submission of Certificates and Test Reports of Reinforcement Bar (Batch 15).pdf",
    BASE_DIR / "test file" / "Submission of Certificates and Test Reports of Reinforcement Bar (Batch 16).pdf",
]

PUBLIC_ELECTRONIC_SAMPLES = [
    (
        "cares_mill_test_certificate.pdf",
        "https://www.carescertification.com/content/HtmlContent/b3bb2e69-676a-4349-83c6-6e003e57dd65/0e6b6fc7-eeaf-4f07-9a32-95e20acea150/250914%20CARES%20-%20MTC%20example_v00.pdf",
    ),
    (
        "goa_concrete_cube_report.pdf",
        "https://goawrd.gov.in/sites/default/files/qc_reports/cube%20report%20SDIII%20WDI%20%20%20%2009-%20.pdf",
    ),
    (
        "tofee_angang_mill_certificate.pdf",
        "https://tofee.com.cn/wp-content/uploads/2019/10/Mill-certificate-Sample.pdf",
    ),
]


def copy_real_samples(input_dir: Path) -> list[Path]:
    copied: list[Path] = []
    for source in REAL_SCANNED_SAMPLES:
        if not source.exists():
            print(f"Missing real scanned sample: {source}")
            continue
        target = input_dir / source.name
        shutil.copy2(source, target)
        copied.append(target)
    return copied


def download_public_samples(input_dir: Path) -> list[Path]:
    downloaded: list[Path] = []
    for filename, url in PUBLIC_ELECTRONIC_SAMPLES:
        target = input_dir / filename
        if target.exists() and target.stat().st_size > 0:
            downloaded.append(target)
            continue
        print(f"Downloading {filename}...")
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        target.write_bytes(response.content)
        downloaded.append(target)
    return downloaded


def write_ocr_profile(sample_paths: list[Path], output_dir: Path, ocr_mode: str) -> Path:
    profile_path = output_dir / "sample_ocr_profile.csv"
    rows: list[dict[str, str]] = []
    for sample_path in sample_paths:
        print(f"Profiling {sample_path.name}...")
        text, meta = extract_pdf_text(sample_path, ocr_mode=ocr_mode)
        rows.append(
            {
                "source_file": sample_path.name,
                "sample_kind": "real_scanned" if sample_path.name.startswith("Submission of Certificates") else "public_electronic",
                "page_count": str(meta["page_count"]),
                "text_layer": str(meta["text_layer"]),
                "low_text_pages": str(meta["low_text_pages"]),
                "ocr_used": str(meta["ocr_used"]),
                "extracted_chars": str(len(text)),
            }
        )

    with profile_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["source_file"])
        writer.writeheader()
        writer.writerows(rows)
    return profile_path


def write_sample_summary(output_dir: Path, profile_path: Path, qa_result: dict | None, provider: str, model: str | None) -> Path:
    summary_path = output_dir / "sample_test_summary.md"
    lines = [
        "# Contractor Submission Sample Test Summary",
        "",
        f"- Provider: {get_provider_label(provider)}",
        f"- Model: {model or get_default_model(provider)}",
        f"- OCR profile: `{profile_path.name}`",
        "- Real scanned samples: Batch 15 and Batch 16 reinforcement bar certificate/test report PDFs.",
        "- Public electronic samples: CARES mill certificate, Goa concrete cube report, Tofee/Angang mill certificate.",
        "",
        "## Operator Steps",
        "",
        "1. Review `sample_ocr_profile.csv` and confirm scanned files show OCR usage or low-text warnings.",
        "2. If AI extraction was enabled, open `qa_records_output.zip` and start with `qa_operator_report.md`.",
        "3. Check `qa_exceptions.csv` before accepting any register rows.",
        "4. Compare heat, batch, bar, cube, and sample IDs back to the source PDFs.",
        "",
    ]
    if qa_result:
        lines.extend(
            [
                "## QA Batch Output",
                "",
                f"- Processed: {qa_result['processed']}",
                f"- Exceptions: {qa_result['exceptions']}",
                f"- Package: `{Path(qa_result['package_path']).name}`",
            ]
        )
    else:
        lines.extend(
            [
                "## QA Batch Output",
                "",
                "- AI extraction was not run. Configure the selected provider API key and rerun with `--run-ai`.",
            ]
        )
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run IDC contractor submission sample checks.")
    parser.add_argument("--sample-root", default=str(BASE_DIR / "tmp_contractor_submission_samples"))
    parser.add_argument("--provider", choices=["grok", "kimi"], default="grok")
    parser.add_argument("--model", default=None)
    parser.add_argument("--ocr-mode", choices=["auto", "force", "no-ocr"], default="auto")
    parser.add_argument("--skip-public", action="store_true", help="Do not download public electronic samples.")
    parser.add_argument("--run-ai", action="store_true", help="Run full QA extraction using the selected API provider.")
    args = parser.parse_args()

    root = Path(args.sample_root)
    input_dir = root / "input"
    output_dir = root / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    samples = copy_real_samples(input_dir)
    if not args.skip_public:
        samples.extend(download_public_samples(input_dir))
    if not samples:
        print("No samples available.")
        return 1

    profile_path = write_ocr_profile(samples, output_dir, args.ocr_mode)
    qa_result = None
    if args.run_ai:
        if not is_provider_configured(args.provider):
            print(f"{get_provider_label(args.provider)} API key is not configured; skipping AI extraction.")
        else:
            qa_result = run_qa_batch(
                input_dir,
                output_dir,
                ocr_mode=args.ocr_mode,
                provider=args.provider,
                model_name=args.model,
                log_callback=print,
            )
    summary_path = write_sample_summary(output_dir, profile_path, qa_result, args.provider, args.model)
    print(f"OCR profile: {profile_path}")
    print(f"Summary: {summary_path}")
    if qa_result:
        print(f"QA package: {qa_result['package_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
