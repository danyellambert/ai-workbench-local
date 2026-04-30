#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ACCESS_CONTROL_PATH = REPO_ROOT / "src" / "product" / "access_control.py"

spec = importlib.util.spec_from_file_location("ads_access_control", ACCESS_CONTROL_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load {ACCESS_CONTROL_PATH}")

access_control = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = access_control
spec.loader.exec_module(access_control)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate an AI Decision Studio admin password hash.")
    parser.add_argument("--password", help="Password to hash. Omit to be prompted securely.")
    args = parser.parse_args()

    password = args.password
    if password is None:
        password = getpass.getpass("Admin password: ")
        confirm = getpass.getpass("Confirm admin password: ")
        if password != confirm:
            print("Passwords do not match.", file=sys.stderr)
            return 1

    print(access_control.hash_admin_password(password))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
