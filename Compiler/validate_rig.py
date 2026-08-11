#!/usr/bin/env python3
"""GAPS Rig Validator v0.1.0"""
from pathlib import Path
from PIL import Image
import argparse, yaml, sys

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--asset-id",default="CHR-GRUNT-001")
    a=ap.parse_args()
    repo=Path.cwd().resolve()
    specp=repo/"Production"/a.asset_id/"03_Rig"/"RigSpecification.yaml"
    if not specp.is_file():
        print("RIG VALIDATION: FAIL - RigSpecification.yaml missing"); return 2
    spec=yaml.safe_load(specp.read_text(encoding="utf-8"))
    errors=[]
    for p in spec["parts"]:
        out=repo/Path(p["output"])
        if not out.is_file():
            errors.append(f"missing part: {p['name']}")
            continue
        im=Image.open(out)
        if im.size!=(1024,1024): errors.append(f"{p['name']}: wrong size {im.size}")
        if im.mode!="RGBA": errors.append(f"{p['name']}: expected RGBA, found {im.mode}")
        if im.convert("RGBA").getchannel("A").getbbox() is None: errors.append(f"{p['name']}: empty alpha")
    if errors:
        print("RIG VALIDATION: FAIL")
        for e in errors: print("-",e)
        return 2
    print(f"RIG VALIDATION: PASS ({len(spec['parts'])} parts)")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
