
import base64
import hashlib
import hmac
import sqlite3
import struct
import time
from pathlib import Path

DB_PATH = Path("security_shield_dashboard_events.sqlite3")

with sqlite3.connect(DB_PATH) as conn:
    row = conn.execute(
        "SELECT totp_secret FROM employees WHERE employee_id = ?",
        ("CEO001",)
    ).fetchone()

if row is None:
    print("CEO001 not found in the demo database.")
else:
    secret = row[0].strip().upper()
    secret += "=" * ((8 - len(secret) % 8) % 8)
    key = base64.b32decode(secret)

    counter = int(time.time()) // 30
    digest = hmac.new(
        key, struct.pack(">Q", counter), hashlib.sha1
    ).digest()

    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    pin = f"{number % 1_000_000:06d}"

    print("CEO001 current 6-digit PIN:", pin)
    print(f"PIN expires in about {30 - int(time.time()) % 30} seconds.")
