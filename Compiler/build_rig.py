#!/usr/bin/env python3
"""
GAPS Rig Builder v0.1.0

Builds transparent full-canvas rig-part PNGs from an approved Gold Master and
per-part masks. This tool does NOT invent hidden pixels.

Modes:
  --prepare   Create blank mask canvases if missing.
  --build     Apply completed masks and generate Parts/*.png and RigManifest.yaml.

Run from repository root.
"""

from pathlib import Path
import argparse, hashlib, sys
from PIL import Image
import yaml

VERSION="0.1.0"

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def load_yaml(p):
    with open(p,"r",encoding="utf-8") as f:
        return yaml.safe_load(f)

def resolve(repo, s):
    return repo / Path(str(s).replace("\\","/"))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--asset-id",default="CHR-GRUNT-001")
    mode=ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare",action="store_true")
    mode.add_argument("--build",action="store_true")
    args=ap.parse_args()

    repo=Path.cwd().resolve()
    spec_path=repo/"Production"/args.asset_id/"03_Rig"/"RigSpecification.yaml"
    if not spec_path.is_file():
        print(f"RIG BUILDER ERROR: missing {spec_path}")
        return 2
    spec=load_yaml(spec_path)
    gold=resolve(repo,spec["source"]["gold_master"])
    if not gold.is_file():
        print(f"RIG BUILDER ERROR: missing Gold Master {gold}")
        return 2

    master=Image.open(gold).convert("RGBA")
    if master.size != (1024,1024):
        print(f"RIG BUILDER ERROR: expected 1024x1024 Gold Master, found {master.size}")
        return 2

    if args.prepare:
        created=0
        for part in spec["parts"]:
            mask=resolve(repo,part["mask"])
            mask.parent.mkdir(parents=True,exist_ok=True)
            if not mask.exists():
                Image.new("L",(1024,1024),0).save(mask)
                created+=1
        print(f"GAPS Rig Builder v{VERSION}")
        print(f"Prepared masks: {created}")
        print("Masks are intentionally blank. Paint desired part regions white in Krita/Photopea/GIMP.")
        print("Do not resize or crop the mask canvas.")
        return 0

    manifest={"asset_id":args.asset_id,"version":spec["metadata"]["version"],"gold_master_sha256":sha256(gold),"parts":[]}
    failed=[]
    for part in spec["parts"]:
        mask_path=resolve(repo,part["mask"])
        out_path=resolve(repo,part["output"])
        if not mask_path.is_file():
            failed.append(f"missing mask: {mask_path}")
            continue
        mask=Image.open(mask_path).convert("L")
        if mask.size != master.size:
            failed.append(f"wrong mask size: {mask_path} = {mask.size}")
            continue
        extrema=mask.getextrema()
        if extrema == (0,0):
            failed.append(f"blank mask: {mask_path}")
            continue
        alpha=Image.new("L",master.size,0)
        # combine source alpha with mask
        src_alpha=master.getchannel("A")
        import PIL.ImageChops
        alpha=PIL.ImageChops.multiply(src_alpha,mask)
        part_img=master.copy()
        part_img.putalpha(alpha)
        out_path.parent.mkdir(parents=True,exist_ok=True)
        part_img.save(out_path,"PNG")
        manifest["parts"].append({
            "name":part["name"],"parent":part["parent"],"pivot":part["pivot"],
            "z_order":part["z_order"],"file":str(out_path.relative_to(repo)).replace("\\","/"),
            "sha256":sha256(out_path)
        })

    if failed:
        print("RIG BUILD BLOCKED")
        for item in failed: print("-",item)
        print("Complete the masks, then rerun --build.")
        return 2

    manifest_path=repo/"Production"/args.asset_id/"03_Rig"/"RigManifest.yaml"
    with open(manifest_path,"w",encoding="utf-8") as f:
        yaml.safe_dump(manifest,f,sort_keys=False)

    print(f"GAPS Rig Builder v{VERSION}")
    print(f"Rig parts generated: {len(manifest['parts'])}")
    print(f"Manifest: {manifest_path}")
    print("RIG BUILD: PASS")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
