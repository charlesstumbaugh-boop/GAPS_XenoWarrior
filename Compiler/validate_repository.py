#!/usr/bin/env python3
"""
GAPS_XenoWarrior Repository Validator
Version 0.1.0

Runs repository validation categories 1–6 and writes:
    Management/RepositoryReport.md

Exit codes:
    0 = PASS
    1 = PASS WITH WARNINGS
    2 = FAIL
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml


TOOL_VERSION = "0.1.0"

REQUIRED_FOLDERS = [
    "Compiler",
    "Core",
    "Intermediate",
    "Management",
    "Reference",
    "Specifications",
    "Docs",
]

REQUIRED_COMPILER_FILES = [
    "Compiler/build_prompt.py",
    "Compiler/validate_reference.py",
    "Compiler/validate_yaml.py",
    "Compiler/requirements.txt",
]

REQUIRED_MANAGEMENT_FILES = [
    "Management/ProductBacklog.md",
    "Management/Sprint01.md",
    "Management/SprintReview.md",
    "Management/DefinitionOfDone.md",
    "Management/Roadmap.md",
    "Management/ProductVision.md",
]

REQUIRED_CORE_FILES = [
    "Core/Rendering.yaml",
    "Core/Palette.yaml",
    "Core/Camera.yaml",
    "Core/Lighting.yaml",
    "Core/Validation.yaml",
    "Core/Export.yaml",
    "Core/Naming.yaml",
    "Core/PromptRules.yaml",
]

REQUIRED_BUILD_FILES = [
    "Intermediate/Builds/PLAYER_001/DESIGN_MASTER/v001/Build.yaml",
    "Intermediate/Builds/PLAYER_001/DESIGN_MASTER/v001/Prompt.md",
    "Intermediate/Builds/PLAYER_001/DESIGN_MASTER/v001/GenerationManifest.yaml",
    "Intermediate/Builds/PLAYER_001/DESIGN_MASTER/v001/BuildReport.md",
]

PLACEHOLDER_TOKENS = {
    "",
    "todo",
    "tbd",
    "placeholder",
    "coming soon",
    "not implemented",
    "pending",
}


@dataclass
class Check:
    category: str
    item: str
    status: str
    details: str


@dataclass
class ValidationSummary:
    checks: list[Check] = field(default_factory=list)

    def add(self, category: str, item: str, status: str, details: str) -> None:
        self.checks.append(Check(category, item, status, details))

    @property
    def fail_count(self) -> int:
        return sum(check.status == "FAIL" for check in self.checks)

    @property
    def warning_count(self) -> int:
        return sum(check.status in {"WARNING", "EMPTY"} for check in self.checks)

    @property
    def pass_count(self) -> int:
        return sum(check.status == "PASS" for check in self.checks)

    @property
    def overall(self) -> str:
        if self.fail_count:
            return "FAIL"
        if self.warning_count:
            return "PASS WITH WARNINGS"
        return "PASS"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the GAPS_XenoWarrior repository."
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
        default=Path("Management/RepositoryReport.md"),
        help="Report path relative to repository root.",
    )
    return parser.parse_args()


def is_meaningful_text(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False

    non_comment_lines = [
        line.strip()
        for line in stripped.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not non_comment_lines:
        return False

    combined = " ".join(non_comment_lines).strip().lower()
    return combined not in PLACEHOLDER_TOKENS


def check_required_paths(
    repository: Path,
    summary: ValidationSummary,
    category: str,
    paths: list[str],
    expect_directory: bool,
) -> None:
    for relative in paths:
        path = repository / relative
        exists = path.is_dir() if expect_directory else path.is_file()

        if not exists:
            summary.add(category, relative, "FAIL", "Required path is missing.")
            continue

        if expect_directory:
            summary.add(category, relative, "PASS", "Required folder exists.")
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8-sig")
        except OSError as error:
            summary.add(category, relative, "FAIL", f"Unable to read file: {error}")
            continue

        if not is_meaningful_text(text):
            summary.add(category, relative, "EMPTY", "File exists but is empty or placeholder-only.")
        else:
            summary.add(category, relative, "PASS", "Required file exists and contains content.")


def check_yaml_integrity(repository: Path, summary: ValidationSummary) -> None:
    yaml_files = sorted(
        {*repository.rglob("*.yaml"), *repository.rglob("*.yml")},
        key=lambda path: str(path).lower(),
    )

    if not yaml_files:
        summary.add("5. YAML Integrity", "Repository YAML scan", "FAIL", "No YAML files found.")
        return

    for path in yaml_files:
        relative = path.relative_to(repository).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = path.read_text(encoding="utf-8-sig")
            except Exception as error:
                summary.add("5. YAML Integrity", relative, "FAIL", f"Unreadable: {error}")
                continue
        except OSError as error:
            summary.add("5. YAML Integrity", relative, "FAIL", f"Unreadable: {error}")
            continue

        if not text.strip():
            summary.add("5. YAML Integrity", relative, "EMPTY", "Whitespace-only or empty YAML.")
            continue

        try:
            documents = list(yaml.safe_load_all(text))
        except yaml.YAMLError as error:
            mark = getattr(error, "problem_mark", None)
            location = (
                f"line {mark.line + 1}, column {mark.column + 1}"
                if mark is not None
                else "unknown location"
            )
            problem = getattr(error, "problem", None) or str(error)
            summary.add("5. YAML Integrity", relative, "FAIL", f"{location}: {problem}")
            continue

        if not documents or all(document in (None, {}, []) for document in documents):
            summary.add("5. YAML Integrity", relative, "EMPTY", "Parses but contains no meaningful YAML data.")
        else:
            summary.add("5. YAML Integrity", relative, "PASS", f"Parsed {len(documents)} document(s).")


def run_yaml_validator(repository: Path, summary: ValidationSummary) -> None:
    validator = repository / "Compiler" / "validate_yaml.py"
    if not validator.exists():
        summary.add(
            "5. YAML Integrity",
            "Compiler/validate_yaml.py execution",
            "FAIL",
            "YAML validator is missing.",
        )
        return

    result = subprocess.run(
        [sys.executable, str(validator), str(repository)],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        status = "PASS"
    elif result.returncode == 1:
        status = "WARNING"
    else:
        status = "FAIL"

    details = (
        f"Exit code {result.returncode}. "
        f"{result.stdout.strip().splitlines()[-1] if result.stdout.strip() else 'No output.'}"
    )
    summary.add("5. YAML Integrity", "validate_yaml.py execution", status, details)


def write_report(repository: Path, report_path: Path, summary: ValidationSummary) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()

    lines = [
        "# GAPS Repository Validation Report",
        "",
        f"- **Validator version:** {TOOL_VERSION}",
        f"- **Repository:** `{repository}`",
        f"- **Generated (UTC):** `{timestamp}`",
        f"- **Overall status:** **{summary.overall}**",
        f"- **PASS:** {summary.pass_count}",
        f"- **WARNING/EMPTY:** {summary.warning_count}",
        f"- **FAIL:** {summary.fail_count}",
        "",
        "## Category Summary",
        "",
        "| Category | PASS | WARNING/EMPTY | FAIL | Result |",
        "|---|---:|---:|---:|---|",
    ]

    categories = []
    for check in summary.checks:
        if check.category not in categories:
            categories.append(check.category)

    for category in categories:
        checks = [check for check in summary.checks if check.category == category]
        passes = sum(check.status == "PASS" for check in checks)
        warnings = sum(check.status in {"WARNING", "EMPTY"} for check in checks)
        failures = sum(check.status == "FAIL" for check in checks)
        result = "FAIL" if failures else ("WARNING" if warnings else "PASS")
        lines.append(f"| {category} | {passes} | {warnings} | {failures} | **{result}** |")

    lines.extend(
        [
            "",
            "## Detailed Results",
            "",
            "| Category | Status | Item | Details |",
            "|---|---|---|---|",
        ]
    )

    for check in summary.checks:
        details = check.details.replace("|", r"\|").replace("\n", " ")
        lines.append(
            f"| {check.category} | **{check.status}** | `{check.item}` | {details} |"
        )

    lines.extend(
        [
            "",
            "## Exit Code Contract",
            "",
            "- `0` — PASS",
            "- `1` — PASS WITH WARNINGS",
            "- `2` — FAIL",
            "",
        ]
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    repository = args.repository.resolve()

    if not repository.exists() or not repository.is_dir():
        print(f"REPOSITORY VALIDATION FAILED: Directory does not exist: {repository}")
        return 2

    summary = ValidationSummary()

    check_required_paths(
        repository,
        summary,
        "1. Repository Structure",
        REQUIRED_FOLDERS,
        expect_directory=True,
    )

    check_required_paths(
        repository,
        summary,
        "2. Required Compiler Files",
        REQUIRED_COMPILER_FILES,
        expect_directory=False,
    )

    check_required_paths(
        repository,
        summary,
        "3. Required Management Files",
        REQUIRED_MANAGEMENT_FILES,
        expect_directory=False,
    )

    check_required_paths(
        repository,
        summary,
        "4. Core Specifications",
        REQUIRED_CORE_FILES,
        expect_directory=False,
    )

    check_yaml_integrity(repository, summary)
    run_yaml_validator(repository, summary)

    check_required_paths(
        repository,
        summary,
        "6. Build Pipeline",
        REQUIRED_BUILD_FILES,
        expect_directory=False,
    )

    report_path = (
        args.report if args.report.is_absolute() else repository / args.report
    ).resolve()

    write_report(repository, report_path, summary)

    print(f"Repository validation: {summary.overall}")
    print(f"PASS: {summary.pass_count}")
    print(f"WARNING/EMPTY: {summary.warning_count}")
    print(f"FAIL: {summary.fail_count}")
    print(f"Report: {report_path}")

    if summary.fail_count:
        return 2
    if summary.warning_count:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
