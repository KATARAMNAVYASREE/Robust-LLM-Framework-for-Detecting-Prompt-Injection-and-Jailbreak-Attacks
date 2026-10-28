
import sqlite3
import hashlib
import base64
import os
import getpass
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "security_shield_dashboard_events.sqlite3"

password = getpass.getpass("Enter a NEW password for CEO001: ")
if len(password) < 12:
    raise SystemExit("Use a password with at least 12 characters.")

salt = os.urandom(16)
digest = hashlib.pbkdf2_hmac(
    "sha256", password.encode("utf-8"), salt, 310_000
)
stored_hash = (
    base64.b64encode(salt).decode() + "$" +
    base64.b64encode(digest).decode()
)

with sqlite3.connect(DB_PATH) as con:
    cur = con.execute(
        "UPDATE employees SET password_hash=?, failed_attempts=0, locked_until=0 "
        "WHERE employee_id=?",
        (stored_hash, "CEO001")
    )
    if cur.rowcount != 1:
        raise SystemExit("CEO001 not found in the dashboard database.")

print("Password reset successfully. Keep the new password private.")
print("Your existing authenticator secret was not changed.")
