"""Build small text-only runtime indexes from the local HK COP OCR sources."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "HK COP OCR"
OUTPUT_ROOT = ROOT / "code_reference_indexes"

SPECS = (
    (
        "concrete",
        "hkcop_concrete_2013_unlocked_structured",
        "HK Code of Practice for Structural Use of Concrete 2013",
        "2020 Edition",
        ["structural use of concrete", "concrete code 2013", "hk cop concrete 2013"],
    ),
    (
        "foundation",
        "hkcop_foundation_2017_unlocked_structured",
        "HK Code of Practice for Foundations 2017",
        "2024 Edition",
        ["code of practice for foundations", "foundation code 2017", "hk foundation code"],
    ),
    (
        "steel",
        "hkcop_steel_2011_structured",
        "HK Code of Practice for the Structural Use of Steel 2011",
        "2023 Edition",
        ["structural use of steel", "steel code 2011", "hk cop steel 2011"],
    ),
)


def _walk(items: list[dict], output: dict[str, dict]) -> None:
    for item in items:
        number = str(item.get("number", "")).strip()
        if number:
            output[number] = {"title": str(item.get("title", "")), "printed_page": item.get("page")}
        _walk(item.get("children") or [], output)


def _markdown_for_clause(text: str, clause: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    pattern = re.compile(rf"(?mi)^#+\s*\**\s*{re.escape(clause)}(?:\s|\**|$)")
    match = pattern.search(text)
    if not match:
        return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("!["))[:4000].strip()
    remainder = text[match.start() :]
    next_heading = re.search(rf"(?mi)^#+\s*\**\s*(?!{re.escape(clause)}(?:\s|\**|$))\d+(?:\.\d+)+", remainder[1:])
    end = (next_heading.start() + 1) if next_heading else min(len(remainder), 8000)
    return remainder[:end].strip()


def build() -> list[Path]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for family, folder, canonical, edition, aliases in SPECS:
        source_dir = SOURCE_ROOT / folder
        structured = json.loads((source_dir / "structured.json").read_text(encoding="utf-8"))
        sections: dict[str, dict] = {}
        _walk(structured["section_tree"], sections)
        clauses = []
        for clause, source_pages in structured["clauses_with_body_pages"].items():
            section = sections.get(clause)
            if not section or not source_pages:
                continue
            source_page = int(source_pages[0])
            page_file = source_dir / "pages" / f"page_{source_page:04d}.md"
            markdown = _markdown_for_clause(page_file.read_text(encoding="utf-8", errors="replace"), clause) if page_file.is_file() else ""
            clauses.append(
                {
                    "clause": clause,
                    "title": section["title"],
                    "printed_page": section["printed_page"],
                    "source_pdf_page": source_page,
                    "markdown": markdown,
                }
            )
        payload = {
            "family": family,
            "canonical_name": canonical,
            "edition": edition,
            "aliases": aliases,
            "source_folder": folder,
            "clauses": clauses,
        }
        target = OUTPUT_ROOT / f"hk_{family}.json"
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        outputs.append(target)
    return outputs


if __name__ == "__main__":
    for item in build():
        print(item)
