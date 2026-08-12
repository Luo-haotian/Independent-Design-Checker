"""Public domain contracts for evidence, checks, and review runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICT = "CONFLICT"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ERROR = "ERROR"


class ReviewStatus(str, Enum):
    DRAFT = "DRAFT"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(slots=True)
class SourceEvidence:
    source_file: str
    page: int | None = None
    quote: str = ""
    extraction_method: str = "text"
    confidence: float = 1.0


@dataclass(slots=True)
class CodeBasis:
    jurisdiction: str = "HK"
    authority: str = "Hong Kong Buildings Department"
    code_pack_id: str = "hk-bd-concrete-2020-amd-2024-04"
    edition: str = "2013 Code (2020 Edition)"
    amendments: list[str] = field(default_factory=list)
    as_of_date: str | None = None
    rule_set_version: str = "1.0.0"
    engineering_approved: bool = False


@dataclass(slots=True)
class ExtractedFact:
    fact_id: str
    name: str
    value: Any
    unit: str | None = None
    evidence: list[SourceEvidence] = field(default_factory=list)
    confidence: float = 0.0
    conflict: bool = False
    reviewer_overridden: bool = False


@dataclass(slots=True)
class CheckResult:
    rule_id: str
    title: str
    status: CheckStatus
    citations: list[str]
    formula: str
    formula_version: str
    inputs: dict[str, Any]
    demand: float | None = None
    capacity: float | None = None
    utilisation: float | None = None
    unit: str | None = None
    evidence: list[SourceEvidence] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    message: str = ""
    deterministic: bool = True


@dataclass(slots=True)
class AuditEvent:
    event_type: str
    reviewer: str
    reason: str
    timestamp: str = field(default_factory=utc_now)
    fact_id: str | None = None
    old_value: Any = None
    new_value: Any = None


@dataclass(slots=True)
class ReviewRun:
    run_id: str
    source_file: str
    source_sha256: str
    code_basis: CodeBasis
    status: ReviewStatus = ReviewStatus.DRAFT
    page_count: int = 0
    processed_pages: list[int] = field(default_factory=list)
    unprocessed_pages: list[int] = field(default_factory=list)
    facts: list[ExtractedFact] = field(default_factory=list)
    checks: list[CheckResult] = field(default_factory=list)
    ai_observations: list[str] = field(default_factory=list)
    audit_events: list[AuditEvent] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    model_provider: str | None = None
    model_name: str | None = None
    prompt_version: str = "idc-v0.17"

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)
