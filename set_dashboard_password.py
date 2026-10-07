"""Run this to set (or change) the WORKHORSE dashboard login password.
Prompts interactively so the password is never typed anywhere but this terminal.
Stores a salted scrypt hash in secrets.json (gitignored) - never plaintext.
"""
import getpass
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from shared.auth import hash_password

SECRETS_FILE = Path(__file__).parent / "secrets.json"


def main():
    pw = getpass.getpass("Set WORKHORSE dashboard password: ")
    pw2 = getpass.getpass("Confirm password: ")
    if pw != pw2:
        print("Passwords did not match. Nothing changed.")
        return
    if len(pw) < 8:
        print("Password must be at least 8 characters. Nothing changed.")
        return

    data = {}
    if SECRETS_FILE.exists():
        data = json.loads(SECRETS_FILE.read_text(encoding="utf-8"))

    creds = hash_password(pw)
    auth = data.setdefault("dashboard_auth", {})
    auth["salt"] = creds["salt"]
    auth["password_hash"] = creds["hash"]
    if not auth.get("session_secret"):
        auth["session_secret"] = os.urandom(32).hex()

    SECRETS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("Dashboard password set. Restart the server and log in at /login.")


if __name__ == "__main__":
    main()
