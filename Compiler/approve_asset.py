#!/usr/bin/env python3
"""
GAPS Gold Master Promotion Tool
Increment 1 — Command-Line Framework
Version 0.1.0

Current capabilities:
- Accept a candidate asset path.
- Verify that the file exists.
- Verify that the candidate is a file.
- Display candidate metadata.
- Stop before validation or promotion.

No files are copied, moved, renamed, approved, or modified in this increment.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


TOOL_NAME = "GAPS Gold Master Promotion Tool"
TOOL_VERSION = "0.1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect a candidate asset before Gold Master validation and promotion."
        )
    )

    parser.add_argument(
        "candidate",
        type=Path,
        help="Path to the candidate production asset.",
    )

    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def display_candidate(candidate: Path) -> None:
    stat = candidate.stat()

    print(f"{TOOL_NAME} v{TOOL_VERSION}")
    print()
    print("Candidate")
    print("---------")
    print(f"Path: {candidate}")
    print(f"Name: {candidate.name}")
    print(f"Extension: {candidate.suffix.lower() or '(none)'}")
    print(f"Size: {stat.st_size} bytes")
    print(f"SHA-256: {sha256(candidate)}")
    print()
    print("Status")
    print("------")
    print("READY FOR VALIDATION")
    print()
    print("No files were changed.")


def main() -> int:
    args = parse_args()
    candidate = args.candidate.expanduser().resolve()

    if not candidate.exists():
        print(f"{TOOL_NAME} v{TOOL_VERSION}", file=sys.stderr)
        print(file=sys.stderr)
        print("ERROR", file=sys.stderr)
        print("-----", file=sys.stderr)
        print("Candidate asset not found.", file=sys.stderr)
        print(f"Path: {candidate}", file=sys.stderr)
        return 2

    if not candidate.is_file():
        print(f"{TOOL_NAME} v{TOOL_VERSION}", file=sys.stderr)
        print(file=sys.stderr)
        print("ERROR", file=sys.stderr)
        print("-----", file=sys.stderr)
        print("Candidate path is not a file.", file=sys.stderr)
        print(f"Path: {candidate}", file=sys.stderr)
        return 2

    try:
        display_candidate(candidate)
    except OSError as error:
        print(f"{TOOL_NAME} v{TOOL_VERSION}", file=sys.stderr)
        print(file=sys.stderr)
        print("ERROR", file=sys.stderr)
        print("-----", file=sys.stderr)
        print(f"Unable to inspect candidate: {error}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
