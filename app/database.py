
import csv
import io
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(
    os.getenv("SECURITY_DB_PATH", str(PROJECT_ROOT / "security_logs.db"))
)


def get_connection():
    """Open a SQLite connection with dictionary-style rows."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(str(DB_PATH), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def init_db():
    """Create the security log table and add missing columns safely."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                input_text TEXT NOT NULL DEFAULT '',
                risk_score REAL NOT NULL DEFAULT 0,
                confidence REAL,
                attack_type TEXT NOT NULL DEFAULT 'none',
                action TEXT NOT NULL DEFAULT 'ALLOW',
                source TEXT NOT NULL DEFAULT 'prompt',
                filename TEXT,
                is_attack INTEGER NOT NULL DEFAULT 0,
                details_json TEXT NOT NULL DEFAULT '{}'
            )
        """)

        # Support an existing Stage 1 database without deleting its logs.
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(security_logs)"
            ).fetchall()
        }

        additions = {
            "source": "TEXT NOT NULL DEFAULT 'prompt'",
            "filename": "TEXT",
            "is_attack": "INTEGER NOT NULL DEFAULT 0",
            "details_json": "TEXT NOT NULL DEFAULT '{}'",
            "confidence": "REAL",
        }

        for name, definition in additions.items():
            if name not in columns:
                connection.execute(
                    f"ALTER TABLE security_logs ADD COLUMN {name} {definition}"
                )

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_security_logs_timestamp
            ON security_logs(timestamp)
        """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_security_logs_action
            ON security_logs(action)
        """)
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_security_logs_source
            ON security_logs(source)
        """)


def log_scan(
    input_text: str,
    risk_score: float = 0,
    confidence: Optional[float] = None,
    attack_type: str = "none",
    action: str = "ALLOW",
    source: str = "prompt",
    filename: Optional[str] = None,
    is_attack: bool = False,
    details: Optional[dict[str, Any]] = None,
) -> int:
    """Persist one scan and return its database ID."""
    init_db()

    safe_score = max(0.0, min(1.0, float(risk_score or 0)))

    safe_confidence = None
    if confidence is not None:
        safe_confidence = max(0.0, min(1.0, float(confidence)))

    timestamp = datetime.now(timezone.utc).isoformat()
    details_json = json.dumps(details or {}, ensure_ascii=False, default=str)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO security_logs (
                timestamp, input_text, risk_score, confidence,
                attack_type, action, source, filename, is_attack,
                details_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                str(input_text or ""),
                safe_score,
                safe_confidence,
                str(attack_type or "none"),
                str(action or "ALLOW").upper(),
                str(source or "prompt"),
                filename,
                int(bool(is_attack)),
                details_json,
            ),
        )
        return int(cursor.lastrowid)


def _row_to_dict(row):
    item = dict(row)
    item["is_attack"] = bool(item.get("is_attack", 0))

    try:
        item["details"] = json.loads(item.pop("details_json", "{}"))
    except (TypeError, json.JSONDecodeError):
        item["details"] = {}
        item.pop("details_json", None)

    return item


def get_logs(
    limit: int = 500,
    action: Optional[str] = None,
    attack_type: Optional[str] = None,
    source: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Return recent logs with optional filters."""
    init_db()

    limit = max(1, min(int(limit), 5000))
    clauses = []
    params = []

    if action:
        clauses.append("UPPER(action) = ?")
        params.append(action.upper())

    if attack_type:
        clauses.append("LOWER(attack_type) = ?")
        params.append(attack_type.lower())

    if source:
        clauses.append("LOWER(source) = ?")
        params.append(source.lower())

    if start_date:
        clauses.append("date(timestamp) >= date(?)")
        params.append(start_date)

    if end_date:
        clauses.append("date(timestamp) <= date(?)")
        params.append(end_date)

    where_sql = ""
    if clauses:
        where_sql = "WHERE " + " AND ".join(clauses)

    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM security_logs
            {where_sql}
            ORDER BY id DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def get_summary():
    """Return dashboard metrics for all recorded scans."""
    init_db()

    with get_connection() as connection:
        row = connection.execute("""
            SELECT
                COUNT(*) AS total_scans,
                COALESCE(SUM(is_attack), 0) AS detected_attacks,
                COALESCE(SUM(CASE WHEN UPPER(action) = 'BLOCK'
                                  THEN 1 ELSE 0 END), 0) AS blocked_scans,
                COALESCE(SUM(CASE WHEN UPPER(action) = 'REVIEW'
                                  THEN 1 ELSE 0 END), 0) AS review_scans,
                COALESCE(SUM(CASE WHEN UPPER(action) = 'ALLOW'
                                  THEN 1 ELSE 0 END), 0) AS allowed_scans,
                COALESCE(AVG(risk_score), 0) AS average_risk
            FROM security_logs
        """).fetchone()

        sources = connection.execute("""
            SELECT source, COUNT(*) AS count
            FROM security_logs
            GROUP BY source
        """).fetchall()

        actions = connection.execute("""
            SELECT action, COUNT(*) AS count
            FROM security_logs
            GROUP BY action
        """).fetchall()

        recent = connection.execute("""
            SELECT timestamp, action, risk_score, source, attack_type
            FROM security_logs
            ORDER BY id DESC
            LIMIT 10
        """).fetchall()

    result = dict(row)
    result["average_risk"] = round(float(result["average_risk"]), 4)
    result["scans_by_source"] = {
        item["source"]: item["count"] for item in sources
    }
    result["scans_by_action"] = {
        item["action"]: item["count"] for item in actions
    }
    result["recent_scans"] = [dict(item) for item in recent]

    return result


def export_logs_csv(logs=None):
    """Convert log records to CSV text."""
    if logs is None:
        logs = get_logs(limit=5000)

    output = io.StringIO()
    fieldnames = [
        "id",
        "timestamp",
        "source",
        "filename",
        "input_text",
        "risk_score",
        "confidence",
        "attack_type",
        "action",
        "is_attack",
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for log in logs:
        writer.writerow({
            field: json.dumps(log.get(field), ensure_ascii=False)
            if field == "input_text"
            else log.get(field, "")
            for field in fieldnames
        })

    return output.getvalue()
