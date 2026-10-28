
import csv
import sqlite3
import hashlib
import base64
import os
import hmac
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "security_shield_dashboard_events.sqlite3"
CSV_FILE = ROOT / "demo_member_credentials_seeded.csv"
EMPLOYEE_ID = "CEO001"

with CSV_FILE.open("r", newline="", encoding="utf-8-sig") as f:
    rows = csv.DictReader(f)
    account = next(
        (r for r in rows
         if r["employee_id"].strip().upper() == EMPLOYEE_ID),
        None
    )

if not account:
    raise SystemExit("CEO001 was not found in the CSV.")

password = account["temporary_password"].strip()
secret = account["totp_secret"].strip().upper()

if not password or not secret:
    raise SystemExit("CSV password or authenticator secret is empty.")

salt = os.urandom(16)
digest = hashlib.pbkdf2_hmac(
    "sha256", password.encode("utf-8"), salt, 310_000
)
password_hash = (
    base64.b64encode(salt).decode("ascii") + "$" +
    base64.b64encode(digest).decode("ascii")
)

with sqlite3.connect(DB) as con:
    cur = con.execute(
        """UPDATE employees
           SET password_hash=?, totp_secret=?,
               failed_attempts=0, locked_until=0
           WHERE employee_id=?""",
        (password_hash, secret, EMPLOYEE_ID)
    )
    if cur.rowcount != 1:
        raise SystemExit("CEO001 was not found in the dashboard database.")

print("CEO001 synchronized with the CSV successfully.")
print("Password and authenticator secret updated; lockout reset.")
print("No credentials or secrets were printed.")
