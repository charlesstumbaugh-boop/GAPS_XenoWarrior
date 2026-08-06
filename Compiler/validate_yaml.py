#!/usr/bin/env python3
"""
GAPS_XenoWarrior YAML Integrity Validator
Version 0.1.0

Scans the entire repository for .yaml and .yml files, parses each file with
PyYAML, reports PASS / EMPTY / FAIL, writes Management/YAMLIntegrityReport.md,
and returns an automation-friendly exit code.

Exit codes:
    0 = PASS
    1 = WARNING / EMPTY files found
    2 = FAIL / invalid YAML or unreadable file
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


TOOL_VERSION = "0.1.0"
PLACEHOLDER_VALUES = {
    "",
    "todo",
    "tbd",
    "placeholder",
    "coming soon",
    "not implemented",
    "pending",
}


@dataclass(frozen=True)
class Result:
    path: Path
    status: str
    message: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate every YAML file in a GAPS repository."
    )
    parser.add_argument(
        "repository",
        nargs="?",
        default=".",
        type=Path,
        help="Repository root. Default: current directory.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("Management/YAMLIntegrityReport.md"),
        help="Report path relative to repository root.",
    )
    return parser.parse_args()


def meaningful_content(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return value.strip().lower() not in PLACEHOLDER_VALUES

    if isinstance(value, dict):
        if not value:
            return False
        return any(meaningful_content(item) for item in value.values())

    if isinstance(value, list):
        if not value:
            return False
        return any(meaningful_content(item) for item in value)

    return True


def validate_yaml(path: Path) -> Result:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except Exception as error:
            return Result(path, "FAIL", f"Unreadable text encoding: {error}")
    except OSError as error:
        return Result(path, "FAIL", f"Unable to read file: {error}")

    if not text.strip():
        return Result(path, "EMPTY", "File contains only whitespace or no content.")

    try:
        documents = list(yaml.safe_load_all(text))
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        if mark is not None:
            location = f"line {mark.line + 1}, column {mark.column + 1}"
        else:
            location = "unknown location"
        problem = getattr(error, "problem", None) or str(error)
        return Result(path, "FAIL", f"{location}: {problem}")

    if not documents:
        return Result(path, "EMPTY", "No YAML document was found.")

    if not any(meaningful_content(document) for document in documents):
        return Result(
            path,
            "EMPTY",
            "YAML parses, but contains no meaningful data or only placeholder values.",
        )

    return Result(path, "PASS", f"Parsed {len(documents)} YAML document(s).")


def markdown_escape(text: str) -> str:
    return text.replace("|", r"\|").replace("\n", " ")


def write_report(
    report_path: Path,
    repository: Path,
    results: list[Result],
) -> None:
    counts = {
        status: sum(1 for result in results if result.status == status)
        for status in ("PASS", "EMPTY", "FAIL")
    }

    overall = "FAIL" if counts["FAIL"] else ("WARNING" if counts["EMPTY"] else "PASS")
    timestamp = datetime.now(timezone.utc).isoformat()

    lines = [
        "# YAML Integrity Report",
        "",
        f"- **Validator version:** {TOOL_VERSION}",
        f"- **Repository:** `{repository}`",
        f"- **Generated (UTC):** `{timestamp}`",
        f"- **Overall status:** **{overall}**",
        f"- **Files scanned:** {len(results)}",
        f"- **PASS:** {counts['PASS']}",
        f"- **EMPTY:** {counts['EMPTY']}",
        f"- **FAIL:** {counts['FAIL']}",
        "",
        "## Results",
        "",
        "| Status | File | Details |",
        "|---|---|---|",
    ]

    for result in sorted(results, key=lambda item: str(item.path).lower()):
        relative = result.path.relative_to(repository)
        lines.append(
            f"| {result.status} | `{relative.as_posix()}` | "
            f"{markdown_escape(result.message)} |"
        )

    lines.extend(
        [
            "",
            "## Exit Code Contract",
            "",
            "- `0` — all YAML files passed",
            "- `1` — one or more YAML files are empty or placeholders",
            "- `2` — one or more YAML files failed to parse or could not be read",
            "",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    repository = args.repository.resolve()

    if not repository.exists() or not repository.is_dir():
        print(f"VALIDATION FAILED: Repository directory does not exist: {repository}")
        return 2

    yaml_files = sorted(
        {
            *repository.rglob("*.yaml"),
            *repository.rglob("*.yml"),
        },
        key=lambda path: str(path).lower(),
    )

    if not yaml_files:
        print("VALIDATION FAILED: No YAML files were found.")
        return 2

    results = [validate_yaml(path) for path in yaml_files]
    report_path = (
        args.report if args.report.is_absolute() else repository / args.report
    ).resolve()
    write_report(report_path, repository, results)

    pass_count = sum(result.status == "PASS" for result in results)
    empty_count = sum(result.status == "EMPTY" for result in results)
    fail_count = sum(result.status == "FAIL" for result in results)

    print(f"YAML files scanned: {len(results)}")
    print(f"PASS: {pass_count}")
    print(f"EMPTY: {empty_count}")
    print(f"FAIL: {fail_count}")
    print(f"Report: {report_path}")

    for result in results:
        if result.status != "PASS":
            relative = result.path.relative_to(repository)
            print(f"{result.status}: {relative} — {result.message}")

    if fail_count:
        print("YAML INTEGRITY: FAIL")
        return 2

    if empty_count:
        print("YAML INTEGRITY: WARNING")
        return 1

    print("YAML INTEGRITY: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
