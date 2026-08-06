#!/usr/bin/env python3
"""
GAPS Gold Master Promotion Tool
Increment 2 — Reference Validation Gate
Version 0.2.0

Capabilities:
- Accept a candidate asset path.
- Verify the file exists.
- Display candidate metadata.
- Run Compiler/validate_reference.py automatically.
- Stop promotion when validation fails.
- Make no file changes.

No files are copied, moved, renamed, approved, or modified in this increment.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path


TOOL_NAME = "GAPS Gold Master Promotion Tool"
TOOL_VERSION = "0.2.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a candidate before Gold Master promotion."
    )
    parser.add_argument(
        "candidate",
        type=Path,
        help="Path to the candidate production asset.",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1024,
        help="Required PNG width. Default: 1024",
    )
    parser.add_argument(
        "--height",
        type=int,
        default=1024,
        help="Required PNG height. Default: 1024",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def locate_repository_root(script_path: Path) -> Path:
    compiler_dir = script_path.parent
    repository_root = compiler_dir.parent

    if not (repository_root / "Compiler").is_dir():
        raise RuntimeError(
            "Unable to determine repository root from the Compiler directory."
        )

    return repository_root


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


def run_reference_validation(
    repository_root: Path,
    candidate: Path,
    width: int,
    height: int,
) -> int:
    validator = repository_root / "Compiler" / "validate_reference.py"

    if not validator.is_file():
        print()
        print("ERROR", file=sys.stderr)
        print("-----", file=sys.stderr)
        print("Reference validator not found.", file=sys.stderr)
        print(f"Expected: {validator}", file=sys.stderr)
        return 2

    command = [
        sys.executable,
        str(validator),
        str(candidate),
        "--width",
        str(width),
        "--height",
        str(height),
    ]

    print()
    print("Reference Validation")
    print("--------------------")
    print(f"Command: {' '.join(command)}")
    print()

    result = subprocess.run(
        command,
        cwd=repository_root,
        check=False,
    )

    return result.returncode


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

    if candidate.suffix.lower() != ".png":
        print(f"{TOOL_NAME} v{TOOL_VERSION}", file=sys.stderr)
        print(file=sys.stderr)
        print("ERROR", file=sys.stderr)
        print("-----", file=sys.stderr)
        print("Candidate must be a PNG file.", file=sys.stderr)
        print(f"Extension: {candidate.suffix or '(none)'}", file=sys.stderr)
        return 2

    try:
        repository_root = locate_repository_root(Path(__file__).resolve())
        display_candidate(candidate)
    except (OSError, RuntimeError) as error:
        print(f"{TOOL_NAME} v{TOOL_VERSION}", file=sys.stderr)
        print(file=sys.stderr)
        print("ERROR", file=sys.stderr)
        print("-----", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 2

    validation_code = run_reference_validation(
        repository_root=repository_root,
        candidate=candidate,
        width=args.width,
        height=args.height,
    )

    print()
    print("Promotion Gate")
    print("--------------")

    if validation_code != 0:
        print("REJECTED")
        print("Reason: Reference validation did not pass.")
        print("No files were changed.")
        return 2

    print("VALIDATED")
    print("Status: READY FOR DESTINATION RESOLUTION")
    print("No files were changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
