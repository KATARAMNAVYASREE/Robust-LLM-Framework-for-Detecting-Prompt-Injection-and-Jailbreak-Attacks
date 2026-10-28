from __future__ import annotations
import csv
import io
import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).resolve().parents[1] / "security_logs.db"

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS security_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            source TEXT, language TEXT, action TEXT, risk_score REAL,
            attack_type TEXT, text TEXT, normalized_text TEXT
        )""")
        con.commit()

def log_event(source, language, action, risk_score, attack_type, text=None, normalized_text=None):
    init_db()
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""INSERT INTO security_events
            (source, language, action, risk_score, attack_type, text, normalized_text)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (source, language, action, float(risk_score), attack_type, text, normalized_text))
        con.commit()

def read_events():
    init_db()
    with sqlite3.connect(DB_PATH) as con:
        df = pd.read_sql_query("SELECT * FROM security_events ORDER BY id DESC", con)
    return df

def export_events_csv(events=None):
    df = read_events() if events is None else events
    return df.to_csv(index=False).encode("utf-8-sig")
