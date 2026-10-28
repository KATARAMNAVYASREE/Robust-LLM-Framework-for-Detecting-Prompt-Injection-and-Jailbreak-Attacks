
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "security_shield_dashboard_events.sqlite3"

print("Dashboard database:", DB_PATH)

if not DB_PATH.exists():
    print("Database file not found.")
    raise SystemExit(1)

with sqlite3.connect(DB_PATH) as con:
    tables = [
        row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    ]

    print("Tables:", tables)

    for table in tables:
        if table.startswith("sqlite_"):
            continue

        columns = {
            row[1] for row in con.execute(
                f'PRAGMA table_info("{table}")'
            )
        }

        if "action" in columns and (
            "risk_score" in columns or "attack_type" in columns
        ):
            con.execute(f'DELETE FROM "{table}"')
            print("Cleared:", table)

    con.commit()

print("Dashboard scan history reset.")
