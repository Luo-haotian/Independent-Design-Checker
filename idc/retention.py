"""Retention cleanup for raw uploads and generated reports."""

from __future__ import annotations

import os
import time
from pathlib import Path


def cleanup_expired_files(roots: list[str | Path], retention_days: int | None = None, *, now: float | None = None) -> list[Path]:
    days = retention_days if retention_days is not None else int(os.environ.get("IDC_RETENTION_DAYS", "30"))
    if days < 1:
        raise ValueError("IDC_RETENTION_DAYS must be at least 1.")
    cutoff = (now if now is not None else time.time()) - days * 86400
    removed: list[Path] = []
    for raw_root in roots:
        root = Path(raw_root).resolve()
        if not root.is_dir():
            continue
        for candidate in root.rglob("*"):
            resolved = candidate.resolve()
            if root not in resolved.parents or not candidate.is_file() or candidate.is_symlink():
                continue
            if candidate.stat().st_mtime < cutoff:
                candidate.unlink()
                removed.append(candidate)
        for directory in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            if not any(directory.iterdir()):
                directory.rmdir()
    return removed
