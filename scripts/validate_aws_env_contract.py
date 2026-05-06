#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def parse_env(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def compose_env_refs(paths: list[Path]) -> set[str]:
    refs: set[str] = set()
    pattern = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-[^}]*)?\}")
    for path in paths:
        if not path.exists():
            continue
        refs.update(pattern.findall(path.read_text(encoding="utf-8", errors="replace")))
    return refs


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AWS env/example key contract.")
    parser.add_argument("--env", default=".env.aws", help="real AWS env file")
    parser.add_argument("--example", default=".env.aws.example", help="safe AWS env example")
    parser.add_argument(
        "--compose",
        action="append",
        default=["docker-compose.aws-slim.yml"],
        help="compose file to inspect for ${VAR} references; may be passed multiple times",
    )
    parser.add_argument(
        "--allow-example-superset",
        action="store_true",
        help="allow example to have defaulted keys and compose refs that are not in the real env",
    )
    args = parser.parse_args()

    env_path = Path(args.env)
    example_path = Path(args.example)

    real = parse_env(env_path)
    example = parse_env(example_path)
    refs = compose_env_refs([Path(item) for item in args.compose])

    real_keys = set(real)
    example_keys = set(example)

    missing_from_example = sorted(real_keys - example_keys)
    missing_from_real = sorted(example_keys - real_keys)
    compose_missing_from_real = sorted(refs - real_keys)
    compose_missing_from_example = sorted(refs - example_keys)

    ok = (
        not missing_from_example
        and (args.allow_example_superset or not missing_from_real)
        and (args.allow_example_superset or not compose_missing_from_real)
        and not compose_missing_from_example
    )

    report = {
        "ok": ok,
        "counts": {
            "real_keys": len(real_keys),
            "example_keys": len(example_keys),
            "compose_refs": len(refs),
        },
        "missing_from_example": missing_from_example,
        "missing_from_real": missing_from_real,
        "compose_missing_from_real": compose_missing_from_real,
        "compose_missing_from_example": compose_missing_from_example,
        "allow_example_superset": args.allow_example_superset,
    }

    print(json.dumps(report, indent=2, sort_keys=True))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
