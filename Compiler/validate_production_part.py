#!/usr/bin/env python3
"""
GAPS Production Pack Validator
Version 0.1.0
"""

from pathlib import Path
import argparse
import yaml
from PIL import Image

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--character", required=True)
    p.add_argument("--part", required=True)
    args = p.parse_args()

    repo = Path.cwd().resolve()
    png = repo/"Production"/args.character/"03_Parts"/f"{args.part}.png"
    meta = png.with_suffix(".yaml")

    errors=[]

    if not png.is_file():
        errors.append(f"missing PNG: {png}")
    if not meta.is_file():
        errors.append(f"missing YAML: {meta}")

    if png.is_file():
        im = Image.open(png)
        if im.size != (1024,1024):
            errors.append(f"wrong size: {im.size}")
        if im.mode != "RGBA":
            errors.append(f"wrong mode: {im.mode}")
        if im.convert("RGBA").getchannel("A").getbbox() is None:
            errors.append("alpha contains no visible pixels")

    if meta.is_file():
        data = yaml.safe_load(meta.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            errors.append("metadata YAML is invalid")
        elif data.get("metadata",{}).get("part") != args.part:
            errors.append("metadata part does not match requested part")

    if errors:
        print("PRODUCTION PART VALIDATION: FAIL")
        for e in errors:
            print("-",e)
        return 2

    print("PRODUCTION PART VALIDATION: PASS")
    print(f"Character: {args.character}")
    print(f"Part: {args.part}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
