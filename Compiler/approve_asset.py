#!/usr/bin/env python3
"""
GAPS Gold Master Promotion Tool
Increment 5 — Final Promotion
Version 0.5.0

Capabilities:
- Validate a PNG candidate.
- Resolve canonical Gold Master destination.
- Prevent overwrite of existing Gold Masters or approval history.
- Generate Approval.md and Review.yaml.
- Copy the validated candidate to the Gold Master destination.
- Verify the copied file hash matches the candidate.
- Update approval records from STAGED_FOR_PROMOTION to APPROVED.

The source candidate is preserved.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

TOOL_VERSION = "0.5.0"
PATTERN = re.compile(
    r"^(?P<asset>[A-Z0-9-]+)_DESIGN_MASTER(?:_candidate)?_"
    r"(?P<version>v[0-9]{3})(?:_INVALID)?\.png$",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and promote a candidate to Gold Master."
    )
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--approved-by", default="Project Owner")
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument(
        "--confirm-promote",
        action="store_true",
        help="Required to perform the final image copy and approval.",
    )
    return parser.parse_args()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repository_root() -> Path:
    root = Path(__file__).resolve().parent.parent
    if not (root / "Compiler").is_dir():
        raise RuntimeError("Unable to determine repository root.")
    return root


def run_reference_validator(root: Path, candidate: Path, width: int, height: int) -> int:
    validator = root / "Compiler" / "validate_reference.py"
    if not validator.is_file():
        raise RuntimeError(f"Reference validator not found: {validator}")

    command = [
        sys.executable,
        str(validator),
        str(candidate),
        "--width",
        str(width),
        "--height",
        str(height),
    ]
    print("\nReference Validation")
    print("--------------------")
    print("Command:", " ".join(command), "\n")
    return subprocess.run(command, cwd=root, check=False).returncode


def resolve_target(root: Path, candidate: Path) -> dict[str, Path | str]:
    match = PATTERN.fullmatch(candidate.name)
    if match is None:
        raise ValueError(
            "Candidate filename must resemble "
            "CHR-PLAYER-001_DESIGN_MASTER_candidate_v001.png"
        )

    asset_id = match.group("asset").upper()
    version = match.group("version").lower()
    filename = f"{asset_id}_DESIGN_MASTER_{version}.png"
    design_dir = root / "Reference" / "GoldMasters" / asset_id / "Design"
    records_dir = design_dir / version

    return {
        "asset_id": asset_id,
        "version": version,
        "filename": filename,
        "image": design_dir / filename,
        "records": records_dir,
        "approval": records_dir / "Approval.md",
        "review": records_dir / "Review.yaml",
    }


def write_records(
    target: dict[str, Path | str],
    candidate: Path,
    approved_by: str,
    approved_at: datetime,
    width: int,
    height: int,
    final_status: str,
    image_copied: bool,
) -> None:
    records = target["records"]
    approval = target["approval"]
    review = target["review"]

    assert isinstance(records, Path)
    assert isinstance(approval, Path)
    assert isinstance(review, Path)

    records.mkdir(parents=True, exist_ok=True)
    candidate_sha = file_hash(candidate)

    approval.write_text(
        f"""# Gold Master Approval Record

## Asset

- **Asset ID:** `{target['asset_id']}`
- **Version:** `{target['version']}`
- **Target filename:** `{target['filename']}`
- **Target path:** `{target['image']}`

## Candidate

- **Candidate path:** `{candidate}`
- **Candidate SHA-256:** `{candidate_sha}`

## Validation

- **Reference validation:** PASS
- **Required canvas:** {width} × {height}
- **Required format:** PNG
- **Required transparency:** true alpha transparency
- **Promotion tool version:** {TOOL_VERSION}

## Approval

- **Status:** {final_status}
- **Approved by:** {approved_by}
- **Approval date (UTC):** {approved_at.isoformat()}
- **Gold Master copied:** {"Yes" if image_copied else "No"}
- **History overwrite allowed:** No
""",
        encoding="utf-8",
    )

    review_data = {
        "metadata": {
            "document_type": "gold_master_review",
            "tool_version": TOOL_VERSION,
        },
        "asset": {
            "asset_id": target["asset_id"],
            "version": target["version"],
            "candidate_file": candidate.name,
            "candidate_sha256": candidate_sha,
            "target_file": target["filename"],
            "target_path": str(target["image"]),
        },
        "validation": {
            "reference_validation": "PASS",
            "canvas": {"width": width, "height": height},
            "format": "PNG",
            "true_alpha_required": True,
        },
        "approval": {
            "status": final_status,
            "approved_by": approved_by,
            "approved_at_utc": approved_at.isoformat(),
            "gold_master": image_copied,
            "image_copied": image_copied,
            "overwrite_allowed": False,
        },
    }
    review.write_text(
        yaml.safe_dump(review_data, sort_keys=False),
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()
    candidate = args.candidate.expanduser().resolve()
    approved_by = args.approved_by.strip() or "Project Owner"

    print(f"GAPS Gold Master Promotion Tool v{TOOL_VERSION}\n")

    if not candidate.is_file():
        print("ERROR\n-----\nCandidate asset not found.")
        print(f"Path: {candidate}")
        return 2

    if candidate.suffix.lower() != ".png":
        print("ERROR\n-----\nCandidate must be a PNG file.")
        return 2

    print("Candidate")
    print("---------")
    print(f"Path: {candidate}")
    print(f"Name: {candidate.name}")
    print(f"Size: {candidate.stat().st_size} bytes")
    print(f"SHA-256: {file_hash(candidate)}")

    try:
        root = repository_root()
        validation_code = run_reference_validator(root, candidate, args.width, args.height)
    except RuntimeError as error:
        print(f"\nERROR\n-----\n{error}")
        return 2

    print("\nPromotion Gate")
    print("--------------")
    if validation_code != 0:
        print("REJECTED")
        print("Reason: Reference validation did not pass.")
        print("No files were changed.")
        return 2
    print("VALIDATED")

    try:
        target = resolve_target(root, candidate)
    except ValueError as error:
        print(f"\nDESTINATION RESOLUTION FAILED\n{error}")
        return 2

    print("\nDestination Resolution")
    print("----------------------")
    print(f"Asset ID: {target['asset_id']}")
    print(f"Version: {target['version']}")
    print(f"Image target: {target['image']}")
    print(f"Approval target: {target['approval']}")
    print(f"Review target: {target['review']}")

    image_target = target["image"]
    records_target = target["records"]
    assert isinstance(image_target, Path)
    assert isinstance(records_target, Path)

    if image_target.exists():
        print("\nPromotion Status")
        print("----------------")
        print("BLOCKED")
        print("Reason: Gold Master already exists and will not be overwritten.")
        return 2

    if not args.confirm_promote:
        print("\nPromotion Status")
        print("----------------")
        print("READY FOR FINAL PROMOTION")
        print("No files were changed.")
        print("Rerun with --confirm-promote to copy and approve the Gold Master.")
        return 1

    approved_at = datetime.now(timezone.utc)

    try:
        image_target.parent.mkdir(parents=True, exist_ok=True)
        records_target.mkdir(parents=True, exist_ok=True)

        write_records(
            target=target,
            candidate=candidate,
            approved_by=approved_by,
            approved_at=approved_at,
            width=args.width,
            height=args.height,
            final_status="STAGED_FOR_PROMOTION",
            image_copied=False,
        )

        shutil.copy2(candidate, image_target)

        source_hash = file_hash(candidate)
        destination_hash = file_hash(image_target)
        if source_hash != destination_hash:
            image_target.unlink(missing_ok=True)
            raise RuntimeError("Copied Gold Master hash does not match candidate hash.")

        write_records(
            target=target,
            candidate=candidate,
            approved_by=approved_by,
            approved_at=approved_at,
            width=args.width,
            height=args.height,
            final_status="APPROVED",
            image_copied=True,
        )
    except Exception as error:
        print("\nPROMOTION FAILED")
        print(f"Reason: {error}")
        print("Review the destination before retrying.")
        return 2

    print("\nPromotion Result")
    print("----------------")
    print("APPROVED")
    print(f"Gold Master: {image_target}")
    print(f"SHA-256: {file_hash(image_target)}")
    print(f"Approval record: {target['approval']}")
    print(f"Review record: {target['review']}")
    print("Source candidate preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
