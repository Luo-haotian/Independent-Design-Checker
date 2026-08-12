"""SQLite persistence for reviews, facts, results, decisions, and audit events."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import AuditEvent, ReviewRun, ReviewStatus, utc_now


class ReviewStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS review_runs (
                    run_id TEXT PRIMARY KEY, status TEXT NOT NULL, source_file TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY, status TEXT NOT NULL, payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS facts (
                    run_id TEXT NOT NULL, fact_id TEXT NOT NULL, payload_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, fact_id), FOREIGN KEY (run_id) REFERENCES review_runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS results (
                    run_id TEXT NOT NULL, result_index INTEGER NOT NULL, payload_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, result_index), FOREIGN KEY (run_id) REFERENCES review_runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, event_type TEXT NOT NULL,
                    reviewer TEXT NOT NULL, reason TEXT NOT NULL, timestamp TEXT NOT NULL,
                    fact_id TEXT, old_value_json TEXT, new_value_json TEXT,
                    FOREIGN KEY (run_id) REFERENCES review_runs(run_id)
                );
                """
            )

    def save_job(self, job: dict[str, Any]) -> None:
        job_id = str(job.get("id", "")).strip()
        if not job_id:
            raise ValueError("A persisted job requires an id.")
        with self.connect() as db:
            db.execute(
                "INSERT INTO jobs VALUES (?, ?, ?, ?) ON CONFLICT(job_id) DO UPDATE SET status=excluded.status, payload_json=excluded.payload_json, updated_at=excluded.updated_at",
                (job_id, str(job.get("status", "unknown")), json.dumps(job), utc_now()),
            )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT payload_json FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def save_run(self, run: ReviewRun) -> None:
        payload = run.to_dict()
        now = utc_now()
        with self.connect() as db:
            db.execute(
                "INSERT INTO review_runs VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(run_id) DO UPDATE SET status=excluded.status, payload_json=excluded.payload_json, updated_at=excluded.updated_at",
                (run.run_id, run.status.value, run.source_file, run.source_sha256, json.dumps(payload), run.created_at, now),
            )
            db.execute("DELETE FROM facts WHERE run_id=?", (run.run_id,))
            db.execute("DELETE FROM results WHERE run_id=?", (run.run_id,))
            db.executemany("INSERT INTO facts VALUES (?, ?, ?)", [(run.run_id, f.fact_id, json.dumps(payload["facts"][i])) for i, f in enumerate(run.facts)])
            db.executemany("INSERT INTO results VALUES (?, ?, ?)", [(run.run_id, i, json.dumps(item)) for i, item in enumerate(payload["checks"])])

    def get_payload(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as db:
            row = db.execute("SELECT status, payload_json FROM review_runs WHERE run_id=?", (run_id,)).fetchone()
            if not row:
                return None
            payload = json.loads(row["payload_json"])
            payload["status"] = row["status"]
            payload["facts"] = [json.loads(item[0]) for item in db.execute("SELECT payload_json FROM facts WHERE run_id=? ORDER BY fact_id", (run_id,))]
            payload["checks"] = [json.loads(item[0]) for item in db.execute("SELECT payload_json FROM results WHERE run_id=? ORDER BY result_index", (run_id,))]
            payload["audit_events"] = [
                {
                    "event_type": item["event_type"], "reviewer": item["reviewer"], "reason": item["reason"],
                    "timestamp": item["timestamp"], "fact_id": item["fact_id"],
                    "old_value": json.loads(item["old_value_json"]), "new_value": json.loads(item["new_value_json"]),
                }
                for item in db.execute("SELECT * FROM audit_events WHERE run_id=? ORDER BY id", (run_id,))
            ]
        return payload

    def edit_fact(self, run_id: str, fact_id: str, new_value: Any, *, evidence: list[dict[str, Any]], reviewer: str, reason: str) -> None:
        if not reviewer.strip() or not reason.strip() or not evidence:
            raise ValueError("Fact edits require reviewer, reason, and evidence.")
        if any(not isinstance(item, dict) or not isinstance(item.get("page"), int) or item.get("page", 0) < 1 for item in evidence):
            raise ValueError("Every fact-edit evidence item requires a positive page number.")
        with self.connect() as db:
            row = db.execute("SELECT payload_json FROM facts WHERE run_id=? AND fact_id=?", (run_id, fact_id)).fetchone()
            if not row:
                raise KeyError(fact_id)
            fact = json.loads(row[0])
            old_value = fact.get("value")
            fact.update(value=new_value, evidence=evidence, reviewer_overridden=True)
            db.execute("UPDATE facts SET payload_json=? WHERE run_id=? AND fact_id=?", (json.dumps(fact), run_id, fact_id))
            run_row = db.execute("SELECT payload_json FROM review_runs WHERE run_id=?", (run_id,)).fetchone()
            run_payload = json.loads(run_row[0])
            run_payload["status"] = ReviewStatus.DRAFT.value
            run_payload["checks"] = []
            db.execute("DELETE FROM results WHERE run_id=?", (run_id,))
            db.execute(
                "UPDATE review_runs SET status=?, payload_json=?, updated_at=? WHERE run_id=?",
                (ReviewStatus.DRAFT.value, json.dumps(run_payload), utc_now(), run_id),
            )
            self._audit(db, run_id, AuditEvent("FACT_EDIT", reviewer.strip(), reason.strip(), fact_id=fact_id, old_value=old_value, new_value=new_value))

    def decide(self, run_id: str, decision: str, *, reviewer: str, reason: str) -> None:
        if not reviewer.strip() or not reason.strip():
            raise ValueError("Reviewer name and reason are required.")
        status = ReviewStatus(decision.upper())
        if status not in {ReviewStatus.APPROVED, ReviewStatus.REJECTED}:
            raise ValueError("Decision must be APPROVED or REJECTED.")
        with self.connect() as db:
            row = db.execute("SELECT status FROM review_runs WHERE run_id=?", (run_id,)).fetchone()
            if not row:
                raise KeyError(run_id)
            if row["status"] != ReviewStatus.READY_FOR_REVIEW.value:
                raise ValueError("Only a READY_FOR_REVIEW run can receive a decision; rerun checks after fact edits.")
            db.execute("UPDATE review_runs SET status=?, updated_at=? WHERE run_id=?", (status.value, utc_now(), run_id))
            self._audit(db, run_id, AuditEvent("REVIEW_DECISION", reviewer.strip(), reason.strip(), new_value=status.value))

    @staticmethod
    def _audit(db: sqlite3.Connection, run_id: str, event: AuditEvent) -> None:
        db.execute(
            "INSERT INTO audit_events(run_id,event_type,reviewer,reason,timestamp,fact_id,old_value_json,new_value_json) VALUES (?,?,?,?,?,?,?,?)",
            (run_id, event.event_type, event.reviewer, event.reason, event.timestamp, event.fact_id, json.dumps(event.old_value), json.dumps(event.new_value)),
        )

    def audit_history(self, run_id: str) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM audit_events WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
        return [dict(row) for row in rows]
