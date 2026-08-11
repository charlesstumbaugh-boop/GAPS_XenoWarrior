#!/usr/bin/env python3
from pathlib import Path
import shutil

FILES = [
    "RigCalibration.yaml",
    "JointSockets.yaml",
    "PivotValidation.yaml",
    "AssemblyOffsets.yaml",
    "CalibrationReview.yaml",
    "CalibrationReport.md",
]

def same_file(a: Path, b: Path) -> bool:
    try:
        return a.resolve() == b.resolve()
    except Exception:
        return False

def main():
    repo = Path.cwd().resolve()
    package_source = (
        Path(__file__).resolve().parent.parent
        / "Production"
        / "CHR-GRUNT-001"
        / "04_Calibration"
    )
    destination = (
        repo
        / "Production"
        / "CHR-GRUNT-001"
        / "04_Calibration"
    )

    rig_spec = (
        repo
        / "Production"
        / "CHR-GRUNT-001"
        / "03_Rig"
        / "RigSpecification.yaml"
    )
    if not rig_spec.is_file():
        print("CALIBRATION BUILD: FAIL")
        print("Missing existing RigSpecification.yaml")
        return 2

    destination.mkdir(parents=True, exist_ok=True)

    installed = 0
    already_present = 0

    for name in FILES:
        src = package_source / name
        dst = destination / name

        if not src.is_file():
            print("CALIBRATION BUILD: FAIL")
            print("Package file missing:", src)
            return 2

        # If the ZIP was extracted directly into the repository root,
        # src and dst are the same physical file. Do not copy a file onto itself.
        if same_file(src, dst):
            already_present += 1
            continue

        shutil.copy2(src, dst)
        installed += 1

    print("RIG CALIBRATION BUILD: PASS")
    print(f"Files installed: {installed}")
    print(f"Files already in destination: {already_present}")
    print("Art files modified: NO")
    print("Calibration status: IN PROGRESS")
    print(
        "NEXT: review "
        "Production\\CHR-GRUNT-001\\04_Calibration\\CalibrationReport.md"
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
