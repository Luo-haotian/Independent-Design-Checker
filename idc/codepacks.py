"""Versioned code-pack loading and external source verification."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .models import CodeBasis

DEFAULT_CODE_PACK_ID = "hk-bd-concrete-2020-amd-2024-04"
REQUIRED_MANIFEST_FIELDS = {
    "id",
    "jurisdiction",
    "authority",
    "title",
    "edition",
    "amendments",
    "effective_from",
    "rule_set_version",
    "sources",
}


@dataclass(slots=True)
class CodePack:
    root: Path
    manifest: dict[str, Any]
    rules: dict[str, Any]

    @property
    def id(self) -> str:
        return str(self.manifest["id"])

    @property
    def jurisdiction(self) -> str:
        return str(self.manifest["jurisdiction"]).upper()

    def code_basis(self, as_of_date: str | None = None) -> CodeBasis:
        if as_of_date:
            selected_date = date.fromisoformat(as_of_date)
            effective = date.fromisoformat(self.manifest["effective_from"])
            if selected_date < effective:
                raise ValueError(f"Code pack {self.id} was not effective on {as_of_date}.")
        return CodeBasis(
            jurisdiction=self.jurisdiction,
            authority=self.manifest["authority"],
            code_pack_id=self.id,
            edition=self.manifest["edition"],
            amendments=[item["title"] for item in self.manifest["amendments"]],
            as_of_date=as_of_date,
            rule_set_version=self.manifest["rule_set_version"],
            engineering_approved=bool(self.manifest.get("engineering_approved", False)),
        )

    def verify_external_sources(self, library: str | Path | None = None) -> list[dict[str, Any]]:
        """Report local source availability without requiring PDFs at runtime."""
        root = Path(library or os.environ.get("IDC_CODE_LIBRARY", "")) if (library or os.environ.get("IDC_CODE_LIBRARY")) else None
        results: list[dict[str, Any]] = []
        for source in self.manifest["sources"]:
            result = {
                "filename": source["filename"],
                "official_url": source["official_url"],
                "available": False,
                "sha256": None,
                "hash_matches": None,
            }
            if root:
                path = root / source["filename"]
                if path.is_file():
                    hasher = hashlib.sha256()
                    with path.open("rb") as handle:
                        for block in iter(lambda: handle.read(1024 * 1024), b""):
                            hasher.update(block)
                    digest = hasher.hexdigest()
                    expected = source.get("sha256")
                    result.update(
                        available=True,
                        sha256=digest,
                        hash_matches=(digest == expected if expected else None),
                    )
            results.append(result)
        return results


def _validate_manifest(manifest: dict[str, Any], folder_name: str) -> None:
    missing = sorted(REQUIRED_MANIFEST_FIELDS - set(manifest))
    if missing:
        raise ValueError(f"Code-pack manifest is missing fields: {', '.join(missing)}")
    if manifest["id"] != folder_name:
        raise ValueError("Code-pack folder name must match manifest id.")
    if not isinstance(manifest["amendments"], list) or not isinstance(manifest["sources"], list):
        raise ValueError("Code-pack amendments and sources must be lists.")
    date.fromisoformat(manifest["effective_from"])
    for source in manifest["sources"]:
        if not {"filename", "official_url"}.issubset(source):
            raise ValueError("Every code-pack source requires filename and official_url.")
        if Path(source["filename"]).name != source["filename"] or "/" in source["filename"] or "\\" in source["filename"]:
            raise ValueError("Code-pack source filenames must not contain a path.")
        digest = source.get("sha256")
        if digest is not None and (len(digest) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in digest)):
            raise ValueError(f"Invalid SHA-256 in code-pack source {source['filename']}.")

    rules = manifest.get("supported_rule_ids", [])
    if rules and (not isinstance(rules, list) or not all(isinstance(item, str) for item in rules)):
        raise ValueError("supported_rule_ids must be a list of strings.")


def code_pack_roots(extra_roots: list[str | Path] | None = None) -> list[Path]:
    roots = [Path(__file__).resolve().parents[1] / "codepacks"]
    configured = os.environ.get("IDC_CODE_PACK_PATH", "")
    if configured:
        roots.extend(Path(item) for item in configured.split(os.pathsep) if item)
    if extra_roots:
        roots.extend(Path(item) for item in extra_roots)
    return roots


def load_code_pack(
    pack_id: str = DEFAULT_CODE_PACK_ID,
    *,
    jurisdiction: str = "HK",
    extra_roots: list[str | Path] | None = None,
) -> CodePack:
    """Load exactly the requested pack; never substitute another jurisdiction."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", pack_id):
        raise ValueError("Invalid code-pack ID.")
    requested_jurisdiction = jurisdiction.upper()
    for root in code_pack_roots(extra_roots):
        pack_root = root / pack_id
        manifest_path = pack_root / "manifest.json"
        rules_path = pack_root / "rules.json"
        if not manifest_path.is_file():
            continue
        if not rules_path.is_file():
            raise ValueError(f"Code pack {pack_id} has no rules.json file.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        _validate_manifest(manifest, pack_root.name)
        if manifest["jurisdiction"].upper() != requested_jurisdiction:
            raise ValueError(
                f"Code pack {pack_id} is for {manifest['jurisdiction']}, not {requested_jurisdiction}."
            )
        rules = json.loads(rules_path.read_text(encoding="utf-8"))
        if not isinstance(rules.get("rules"), dict):
            raise ValueError(f"Code pack {pack_id} rules.json requires a rules object.")
        declared = set(manifest.get("supported_rule_ids", []))
        actual = set(rules["rules"])
        if declared and declared != actual:
            raise ValueError(f"Code pack {pack_id} manifest rule IDs do not match rules.json.")
        return CodePack(pack_root, manifest, rules)
    raise FileNotFoundError(
        f"Code pack {pack_id!r} was not found for jurisdiction {requested_jurisdiction}. "
        "Install a validated pack or set IDC_CODE_PACK_PATH."
    )
