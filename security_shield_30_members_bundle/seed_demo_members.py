from __future__ import annotations
import argparse, base64, csv, hashlib, secrets, sqlite3
from datetime import datetime
from pathlib import Path

def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()

def new_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")

def ensure_schema(con):
    con.execute("""CREATE TABLE IF NOT EXISTS employees(
        employee_id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
        full_name TEXT NOT NULL, department_id TEXT NOT NULL DEFAULT 'General',
        access_level TEXT NOT NULL CHECK(access_level IN ('A','B','C')),
        password_hash TEXT NOT NULL, totp_secret TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL, failed_attempts INTEGER NOT NULL DEFAULT 0,
        locked_until REAL NOT NULL DEFAULT 0)""")
    con.execute("""CREATE TABLE IF NOT EXISTS auth_audit(
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
        employee_id TEXT, event TEXT NOT NULL, detail TEXT NOT NULL)""")
    con.execute("""CREATE TABLE IF NOT EXISTS dashboard_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, source TEXT NOT NULL,
        language TEXT NOT NULL, action TEXT NOT NULL, risk_score REAL NOT NULL,
        attack_type TEXT NOT NULL, description TEXT NOT NULL, employee_id TEXT,
        department_id TEXT, visibility TEXT NOT NULL DEFAULT 'department')""")

def main():
    parser = argparse.ArgumentParser(description="Safely add 30 demo accounts to the Security Shield SQLite database.")
    parser.add_argument("--db", default="security_shield_dashboard_events.sqlite3",
                        help="Path to the Streamlit app's database (default: security_shield_dashboard_events.sqlite3)")
    parser.add_argument("--csv", default="demo_member_credentials_seeded.csv",
                        help="Path for generated one-time demo credentials CSV")
    args = parser.parse_args()
    db_path, csv_path = Path(args.db), Path(args.csv)
    if db_path.exists():
        backup = db_path.with_suffix(db_path.suffix + ".before_demo_seed.bak")
        if not backup.exists():
            import shutil
            shutil.copy2(db_path, backup)
            print(f"Backup created: {backup}")
    departments = ["Engineering", "Security", "Data", "Operations", "HR"]
    generated = []
    con = sqlite3.connect(db_path)
    try:
        con.row_factory = sqlite3.Row
        ensure_schema(con)
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        existing_ids = {r["employee_id"] for r in con.execute("SELECT employee_id FROM employees")}
        for level, prefix, role, count in [
            ("A", "CEO", "Senior Management", 10),
            ("B", "MGR", "Department Manager", 10),
            ("C", "EMP", "Employee", 10),
        ]:
            for i in range(1, count + 1):
                employee_id = f"{prefix}{i:03d}"
                if employee_id in existing_ids:
                    continue
                email = f"{employee_id.lower()}@example.test"
                name = f"{role} Demo {i:02d}"
                department = "Executive" if level == "A" else departments[(i-1) % len(departments)]
                password = "Demo-" + secrets.token_urlsafe(12) + "-9!"
                secret = new_totp_secret()
                con.execute("""INSERT INTO employees
                    (employee_id,email,full_name,department_id,access_level,password_hash,totp_secret,active,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                    (employee_id,email,name,department,level,password_hash(password),secret,1,now))
                generated.append({
                    "employee_id":employee_id, "email":email, "full_name":name,
                    "department":department, "access_level":level,
                    "role":{"A":"CEO / Senior Management","B":"Department Manager","C":"Employee"}[level],
                    "temporary_password":password, "totp_secret":secret,
                    "authenticator_label":f"{employee_id} — Robust LLM Security Shield"
                })
        con.commit()
    finally:
        con.close()
    if generated:
        # Write only credentials created during this run; never append to an unrelated CSV.
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(generated[0].keys()))
            writer.writeheader()
            writer.writerows(generated)
    else:
        print("No new accounts were created; no new credential CSV was written.")
    print(f"New demo accounts created: {len(generated)}")
    print(f"Credential file: {csv_path.resolve()}")
    print("Keep the credential CSV private. It contains temporary passwords and MFA secrets.")
    print("These are synthetic demo identities; change/remove them before any real deployment.")

if __name__ == "__main__":
    main()
