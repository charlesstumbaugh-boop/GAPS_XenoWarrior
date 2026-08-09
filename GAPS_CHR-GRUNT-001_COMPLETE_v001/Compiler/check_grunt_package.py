#!/usr/bin/env python3
"""
GAPS CHR-GRUNT-001 Package Registration Check
Version 1.0.0

Run from repository root after extracting this package.
Checks that the concept, identity lock, fingerprint, candidate, and IAS exist.
It does not overwrite or promote anything.
"""

from pathlib import Path
import hashlib
import sys
import yaml

FILES = [
    Path("Reference/Concepts/Characters/Friendly/CHR-GRUNT-001/CHR-GRUNT-001_CONCEPT_APPROVED_v001.png"),
    Path("Reference/Identity/CHR-GRUNT-001/CHR-GRUNT-001_IdentityLock_v001.yaml"),
    Path("Reference/Identity/CHR-GRUNT-001/CHR-GRUNT-001_AssetFingerprint_v001.yaml"),
    Path("Reference/Candidates/CHR-GRUNT-001/CHR-GRUNT-001_DESIGN_MASTER_candidate_v001.png"),
    Path("Intermediate/Assets/CHR-GRUNT-001.yaml"),
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def main() -> int:
    missing = [p for p in FILES if not p.is_file()]
    if missing:
        print("CHR-GRUNT-001 PACKAGE CHECK: FAIL")
        for p in missing:
            print(f"MISSING: {p}")
        return 2

    for p in FILES:
        if p.suffix.lower() in {".yaml", ".yml"}:
            with p.open("r", encoding="utf-8") as f:
                yaml.safe_load(f)

    candidate = FILES[3]
    print("CHR-GRUNT-001 PACKAGE CHECK: PASS")
    print(f"Candidate SHA-256: {sha256(candidate)}")
    print()
    print("NEXT:")
    print('python Compiler/validate_reference.py "Reference/Candidates/CHR-GRUNT-001/CHR-GRUNT-001_DESIGN_MASTER_candidate_v001.png"')
    print("Then use approve_asset.py only after visual and reference validation pass.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
