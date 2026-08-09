#!/usr/bin/env python3
"""
GAPS Asset Pack Installer
Version 1.0.0

Installs a GAPS Asset Pack ZIP into an existing repository without requiring
manual folder merging.

Safety:
- Validates pack manifest and SHA-256 hashes.
- Rejects path traversal and files outside approved repository roots.
- Never installs directly into Reference/GoldMasters.
- Backs up every replaced file before copying.
- Supports dry-run by default; --apply performs the install.
- Can run repository/YAML/reference validation after install.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile, BadZipFile

import yaml

TOOL_VERSION = "1.0.0"

ALLOWED_ROOTS = {
    "Reference/Concepts",
    "Reference/Identity",
    "Reference/Candidates",
    "Intermediate/Assets",
    "Intermediate/Builds",
    "Docs",
    "Specifications",
    "Production",
}

FORBIDDEN_ROOT = "Reference/GoldMasters"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Safely install a GAPS Asset Pack into a repository."
    )
    parser.add_argument("pack", type=Path, help="Path to the Asset Pack ZIP.")
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="Repository root. Defaults to parent of Compiler when installed there.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually install. Without this flag the command is a dry run.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run available GAPS validators after successful installation.",
    )
    return parser.parse_args()


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def detect_repo(explicit: Path | None) -> Path:
    if explicit is not None:
        root = explicit.expanduser().resolve()
    else:
        script = Path(__file__).resolve()
        if script.parent.name.lower() == "compiler":
            root = script.parent.parent
        else:
            root = Path.cwd().resolve()

    required = [root / "Compiler", root / "Core", root / "Intermediate", root / "Reference"]
    if not all(p.exists() for p in required):
        raise RuntimeError(
            f"Not a GAPS repository root: {root}\n"
            "Use --repo C:\\Projects\\GAPS_XenoWarrior if needed."
        )
    return root


def normalize_rel(value: str) -> str:
    value = value.replace("\\", "/").strip("/")
    p = Path(value)
    if p.is_absolute() or ".." in p.parts:
        raise RuntimeError(f"Unsafe path in asset pack: {value}")
    return value


def allowed_path(rel: str) -> bool:
    if rel == FORBIDDEN_ROOT or rel.startswith(FORBIDDEN_ROOT + "/"):
        return False
    return any(rel == root or rel.startswith(root + "/") for root in ALLOWED_ROOTS)


def read_manifest(zip_path: Path) -> dict:
    try:
        with ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            if "AssetPack.yaml" not in names:
                raise RuntimeError("AssetPack.yaml is missing from the ZIP.")
            data = yaml.safe_load(zf.read("AssetPack.yaml").decode("utf-8"))
    except BadZipFile as exc:
        raise RuntimeError(f"Invalid ZIP: {exc}") from exc

    if not isinstance(data, dict):
        raise RuntimeError("AssetPack.yaml must contain a YAML mapping.")
    if data.get("schema_version") != "1.0":
        raise RuntimeError("Unsupported Asset Pack schema_version.")
    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise RuntimeError("AssetPack.yaml contains no files.")
    return data


def validate_archive(zip_path: Path, manifest: dict) -> list[dict]:
    validated = []
    with ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        for item in manifest["files"]:
            if not isinstance(item, dict):
                raise RuntimeError("Invalid file entry in AssetPack.yaml.")
            rel = normalize_rel(str(item.get("path", "")))
            expected = str(item.get("sha256", "")).lower()

            if not allowed_path(rel):
                raise RuntimeError(f"Pack attempts to install forbidden path: {rel}")
            if rel not in names:
                raise RuntimeError(f"Archive is missing declared file: {rel}")

            payload = zf.read(rel)
            actual = hashlib.sha256(payload).hexdigest()
            if actual != expected:
                raise RuntimeError(
                    f"Hash mismatch for {rel}\nExpected: {expected}\nActual:   {actual}"
                )
            validated.append({"path": rel, "sha256": actual})
    return validated


def backup_path(repo: Path, asset_id: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return repo / "Management" / "Backups" / "AssetPacks" / f"{asset_id}_{stamp}"


def install(zip_path: Path, repo: Path, manifest: dict, files: list[dict], apply: bool):
    asset_id = str(manifest.get("asset_id", "UNKNOWN_ASSET"))
    replacements = []
    additions = []

    for item in files:
        target = repo / Path(item["path"])
        if target.exists():
            replacements.append((item["path"], target))
        else:
            additions.append((item["path"], target))

    print(f"GAPS Asset Pack Installer v{TOOL_VERSION}")
    print(f"Asset: {asset_id}")
    print(f"Pack: {zip_path}")
    print(f"Repository: {repo}")
    print(f"Files verified: {len(files)}")
    print(f"New files: {len(additions)}")
    print(f"Existing files to replace: {len(replacements)}")
    print("Gold Master writes: FORBIDDEN")
    print()

    if replacements:
        print("Existing files that would be replaced:")
        for rel, _ in replacements:
            print(f"  - {rel}")
        print()

    if not apply:
        print("DRY RUN PASSED")
        print("No repository files were changed.")
        print("Rerun with --apply to install this pack.")
        return None

    backup = backup_path(repo, asset_id)
    with ZipFile(zip_path, "r") as zf:
        try:
            for rel, target in replacements:
                backup_target = backup / Path(rel)
                backup_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup_target)

            for item in files:
                rel = item["path"]
                target = repo / Path(rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(rel) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)

                actual = hash_file(target)
                if actual != item["sha256"]:
                    raise RuntimeError(f"Post-copy hash verification failed: {rel}")

        except Exception:
            # Restore anything that had an original backup.
            for rel, target in replacements:
                saved = backup / Path(rel)
                if saved.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(saved, target)
            raise

    print("INSTALLATION PASSED")
    print(f"Backup folder: {backup}")
    print("No Gold Master was created or modified.")
    return backup


def run_validators(repo: Path, manifest: dict):
    commands = [
        [sys.executable, str(repo / "Compiler" / "validate_yaml.py")],
        [sys.executable, str(repo / "Compiler" / "validate_repository.py")],
    ]

    candidate = manifest.get("candidate")
    if candidate:
        candidate_path = repo / Path(normalize_rel(str(candidate)))
        validator = repo / "Compiler" / "validate_reference.py"
        if validator.is_file() and candidate_path.is_file():
            commands.append([sys.executable, str(validator), str(candidate_path)])

    print()
    print("VALIDATION")
    print("----------")
    failed = False
    for command in commands:
        if not Path(command[1]).is_file():
            print(f"SKIP: {command[1]} does not exist.")
            continue
        print("RUN:", " ".join(command))
        result = subprocess.run(command, cwd=repo, check=False)
        if result.returncode != 0:
            failed = True
            print(f"VALIDATOR EXIT CODE: {result.returncode}")
    if failed:
        print("POST-INSTALL VALIDATION: WARNING/FAILURE")
        return 2
    print("POST-INSTALL VALIDATION: PASS")
    return 0


def main():
    args = parse_args()
    pack = args.pack.expanduser().resolve()
    if not pack.is_file():
        print(f"INSTALLER ERROR: Pack not found: {pack}", file=sys.stderr)
        return 2

    try:
        repo = detect_repo(args.repo)
        manifest = read_manifest(pack)
        files = validate_archive(pack, manifest)
        install(pack, repo, manifest, files, args.apply)

        if args.apply and args.validate:
            return run_validators(repo, manifest)

    except Exception as exc:
        print(f"INSTALLER ERROR: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
