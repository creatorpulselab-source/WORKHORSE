#!/usr/bin/env python3
"""
Prism — AI Social Media Content Studio — user management

Usage:
  py add_user.py list
  py add_user.py add <username> <password>
  py add_user.py remove <username>
  py add_user.py disable <username>
  py add_user.py enable <username>
"""
import hashlib, json, os, secrets, sys
from pathlib import Path

USERS_FILE = Path(__file__).parent / "users.json"

# Match main.py: on Fly.io the persistent volume at /data holds the real
# users.json — without this, running this script in production would
# silently edit the ephemeral copy instead of the one the app actually reads.
_fly_data = Path("/data")
if _fly_data.exists() and os.access(str(_fly_data), os.W_OK):
    USERS_FILE = _fly_data / "users.json"


def load():
    if USERS_FILE.exists():
        return json.loads(USERS_FILE.read_text())
    return {"users": {}, "session_hours": 24}


def save(data):
    USERS_FILE.write_text(json.dumps(data, indent=2))


def hash_pw(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 260000).hex()


def cmd_list():
    users = load().get("users", {})
    if not users:
        print("No users configured.")
        return
    print(f"\n  {'Username':<22} Status")
    print("  " + "-" * 32)
    for name, info in users.items():
        status = "enabled" if info.get("enabled", True) else "disabled"
        print(f"  {name:<22} {status}")
    print()


def cmd_add(username, password):
    data = load()
    salt = secrets.token_hex(16)
    data.setdefault("users", {})[username] = {
        "salt": salt, "hash": hash_pw(password, salt), "enabled": True,
    }
    save(data)
    print(f"  User '{username}' added/updated.")


def cmd_remove(username):
    data = load()
    if username in data.get("users", {}):
        del data["users"][username]; save(data)
        print(f"  User '{username}' removed.")
    else:
        print(f"  User '{username}' not found.")


def cmd_toggle(username, enable: bool):
    data = load()
    if username in data.get("users", {}):
        data["users"][username]["enabled"] = enable; save(data)
        print(f"  User '{username}' {'enabled' if enable else 'disabled'}.")
    else:
        print(f"  User '{username}' not found.")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "list":          cmd_list()
    elif args[0] == "add"     and len(args)==3: cmd_add(args[1], args[2])
    elif args[0] == "remove"  and len(args)==2: cmd_remove(args[1])
    elif args[0] == "disable" and len(args)==2: cmd_toggle(args[1], False)
    elif args[0] == "enable"  and len(args)==2: cmd_toggle(args[1], True)
    else: print(__doc__)
