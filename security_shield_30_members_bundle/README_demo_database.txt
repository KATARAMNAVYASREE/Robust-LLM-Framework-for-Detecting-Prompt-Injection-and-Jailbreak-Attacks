Robust LLM Security Shield — 30 demo members

Database: security_shield_30_members.sqlite3
Member credential list: demo_member_credentials.csv
Safe seeding script for your existing app database: seed_demo_members.py

The database contains 10 synthetic accounts per level:
- Level A: CEO / Senior Management (CEO001–CEO010)
- Level B: Department Manager (MGR001–MGR010)
- Level C: Employee (EMP001–EMP010)

Passwords are randomly generated and stored in the database only as PBKDF2-SHA256 salted hashes.
The CSV contains temporary passwords and TOTP authenticator secrets so each demo account can sign in.
Keep that CSV private. These are fake example.test email addresses, not real employees.

To add the accounts to your existing dashboard database without replacing existing records:
1. Copy seed_demo_members.py into the same folder as security_shield_dashboard_rbac.py.
2. Back up your database first.
3. Run: python seed_demo_members.py
4. The script creates a .before_demo_seed.bak backup if the target database already exists.
5. Keep demo_member_credentials.csv private.

The app's existing login requires a six-digit TOTP code. For each user, add the TOTP secret from the CSV to an authenticator app, then enter the current code. The secret is the setup key; do not enter the secret itself as the OTP code.

Important: these are synthetic demo accounts. Do not use this dataset as production employee data. Before real deployment, replace the demo users, rotate credentials, and review authentication/session/security controls.
