"""Resolve project code basis from report declarations before applying rules."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .codepacks import DEFAULT_CODE_PACK_ID, HK_CONCRETE_PACK_ID, CodePack, load_code_pack
from .ingestion import DocumentExtraction
from .models import CodeBasis

AUTO_CODE_PACK_ID = "auto"


@dataclass(frozen=True, slots=True)
class CodeDeclaration:
    canonical_name: str
    jurisdiction: str
    family: str
    pattern: re.Pattern[str]
    deterministic_pack_id: str | None = None


DECLARATIONS = (
    CodeDeclaration(
        "HK Code of Practice for Structural Use of Concrete 2013 (2020 Edition)",
        "HK",
        "concrete",
        re.compile(r"(?:Code of Practice for Structural Use of Concrete|Concrete Code)\s*(?:2013)?(?:\s*\(2020 Edition\))?", re.I),
        HK_CONCRETE_PACK_ID,
    ),
    CodeDeclaration("HK Code of Practice on Wind Effects 2019", "HK", "wind", re.compile(r"Code of Practice on Wind Effects(?: in Hong Kong)?\s*2019", re.I)),
    CodeDeclaration("HK Code of Practice for Dead and Imposed Loads 2011", "HK", "loading", re.compile(r"Code of Practice for Dead and Imposed Loads\s*2011", re.I)),
    CodeDeclaration("HK Code of Practice for the Structural Use of Steel 2011", "HK", "steel", re.compile(r"Code of Practice for (?:the )?Structural Use of Steel\s*2011", re.I)),
    CodeDeclaration("HK Code of Practice for Foundations 2017", "HK", "foundation", re.compile(r"Code of Practice for Foundations\s*2017", re.I)),
    CodeDeclaration("HK Code of Practice for Precast Concrete Construction 2016", "HK", "precast", re.compile(r"Code of Practice for Precast Concrete Construction\s*2016", re.I)),
    CodeDeclaration("BS 8110", "BS", "concrete", re.compile(r"\bBS\s*8110(?:[-:]\d+)?(?:\s*:\s*\d{4})?", re.I)),
    CodeDeclaration("Eurocode 2 / BS EN 1992", "BS/EN", "concrete", re.compile(r"\b(?:BS\s+EN\s+1992|EN\s+1992|Eurocode\s*2)\b", re.I)),
    CodeDeclaration("BS 5950", "BS", "steel", re.compile(r"\bBS\s*5950(?:[-:]\d+)?(?:\s*:\s*\d{4})?", re.I)),
    CodeDeclaration("GB 50010", "GB", "concrete", re.compile(r"\bGB\s*50010(?:[-:]\d{4})?", re.I)),
    CodeDeclaration("GB 50009", "GB", "loading", re.compile(r"\bGB\s*50009(?:[-:]\d{4})?", re.I)),
    CodeDeclaration("GB 50017", "GB", "steel", re.compile(r"\bGB\s*50017(?:[-:]\d{4})?", re.I)),
)
GENERIC_CODE_PATTERN = re.compile(r"\b(?:BS(?:\s+EN)?|EN|GB(?:/T)?)\s*\d{3,5}(?:[-:]\d+)*(?:\s*:\s*\d{4})?", re.I)
HK_GENERIC_CODE_PATTERN = re.compile(
    r"\bCode of Practice (?:for|on) [^\n.;]{3,120}?(?:19|20)\d{2}(?:\s*\([^\n)]{1,40}\))?",
    re.I,
)
OTHER_STANDARD_PATTERN = re.compile(r"\b(?:ACI\s*\d{3}(?:\.\d+)?|AS/NZS\s*\d{3,5}(?:\.\d+)?|IBC\s*\d{4})\b", re.I)


def detect_code_declarations(text: str) -> list[dict[str, str | None]]:
    """Return canonical and verbatim code declarations in first-appearance order."""
    found: list[tuple[int, dict[str, str | None]]] = []
    covered_spans: list[tuple[int, int]] = []
    for declaration in DECLARATIONS:
        match = declaration.pattern.search(text)
        if match:
            covered_spans.append(match.span())
            found.append(
                (
                    match.start(),
                    {
                        "canonical_name": declaration.canonical_name,
                        "reported_text": re.sub(r"\s+", " ", match.group(0)).strip(),
                        "jurisdiction": declaration.jurisdiction,
                        "family": declaration.family,
                        "deterministic_pack_id": declaration.deterministic_pack_id,
                    },
                )
            )
    for match in GENERIC_CODE_PATTERN.finditer(text):
        if any(start <= match.start() < end for start, end in covered_spans):
            continue
        reported = re.sub(r"\s+", " ", match.group(0)).strip()
        found.append(
            (
                match.start(),
                {
                    "canonical_name": reported.upper(),
                    "reported_text": reported,
                    "jurisdiction": "GB" if reported.upper().startswith("GB") else "BS/EN",
                    "family": "unclassified",
                    "deterministic_pack_id": None,
                },
            )
        )
    for match in HK_GENERIC_CODE_PATTERN.finditer(text):
        if any(declaration.pattern.search(match.group(0)) for declaration in DECLARATIONS):
            continue
        reported = re.sub(r"\s+", " ", match.group(0)).strip()
        found.append(
            (
                match.start(),
                {
                    "canonical_name": reported,
                    "reported_text": reported,
                    "jurisdiction": "HK",
                    "family": "unclassified",
                    "deterministic_pack_id": None,
                },
            )
        )
    for match in OTHER_STANDARD_PATTERN.finditer(text):
        reported = re.sub(r"\s+", " ", match.group(0)).strip()
        found.append(
            (
                match.start(),
                {
                    "canonical_name": reported.upper(),
                    "reported_text": reported,
                    "jurisdiction": "OTHER",
                    "family": "unclassified",
                    "deterministic_pack_id": None,
                },
            )
        )
    unique: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for _position, item in sorted(found, key=lambda pair: pair[0]):
        key = str(item["canonical_name"]).casefold()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def resolve_code_basis(
    extraction: DocumentExtraction,
    *,
    jurisdiction: str = "HK",
    requested_pack_id: str = AUTO_CODE_PACK_ID,
    code_as_of: str | None = None,
) -> tuple[CodeBasis, CodePack | None]:
    """Prefer report declarations; return an engine pack only when unambiguous."""
    declarations = detect_code_declarations(extraction.full_text)
    declared_names = [str(item["canonical_name"]) for item in declarations]

    if requested_pack_id not in {AUTO_CODE_PACK_ID, DEFAULT_CODE_PACK_ID}:
        selected = load_code_pack(requested_pack_id, jurisdiction=jurisdiction)
        basis = selected.code_basis(code_as_of)
        basis.selection_mode = "reviewer-pinned"
        basis.declared_codes = declared_names
        if selected.id == HK_CONCRETE_PACK_ID:
            return basis, selected
        basis.deterministic_rule_pack_id = None
        basis.unresolved_codes.append("The selected pack is validated, but no deterministic adapter for it is installed in v0.17.")
        return basis, None

    if jurisdiction.upper() == "HK":
        profile = load_code_pack(DEFAULT_CODE_PACK_ID, jurisdiction="HK")
        basis = profile.code_basis(code_as_of)
    else:
        basis = CodeBasis(
            jurisdiction=jurisdiction.upper(),
            authority="Project-declared authorities",
            code_pack_id="report-declared-generic",
            edition="Report-declared code basis; reviewer confirmation required",
            as_of_date=code_as_of,
            rule_set_version="1.0.0",
        )
    basis.selection_mode = "report-declared"
    basis.declared_codes = declared_names
    basis.unresolved_codes = []
    if not declarations:
        basis.unresolved_codes.append("No explicit design code was detected; reviewer confirmation is required.")
        return basis, None

    concrete = [item for item in declarations if item["family"] == "concrete"]
    supported = [item for item in concrete if item["deterministic_pack_id"] == HK_CONCRETE_PACK_ID]
    alternatives = [item for item in concrete if item["deterministic_pack_id"] != HK_CONCRETE_PACK_ID]
    if supported and alternatives:
        basis.unresolved_codes.append("Multiple concrete design bases were detected; pin the applicable member code before deterministic checking.")
        return basis, None
    if supported:
        selected = load_code_pack(HK_CONCRETE_PACK_ID, jurisdiction="HK")
        basis.authority = selected.manifest["authority"]
        basis.edition = selected.manifest["edition"]
        basis.amendments = [item["title"] for item in selected.manifest["amendments"]]
        basis.rule_set_version = selected.manifest["rule_set_version"]
        basis.deterministic_rule_pack_id = selected.id
        basis.engineering_approved = bool(selected.manifest.get("engineering_approved", False))
        return basis, selected
    basis.unresolved_codes.append("No implemented deterministic rule pack matches the report-declared member design code.")
    return basis, None
