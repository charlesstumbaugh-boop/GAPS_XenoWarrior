#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import yaml

ASSET_ID="CHR-GRUNT-001"

def main():
    repo=Path.cwd().resolve()
    spec_path=repo/"Production"/ASSET_ID/"03_Rig"/"RigSpecification.yaml"
    src_dir=repo/"Production"/ASSET_ID/"03_Rig"/"RigSource"
    out=repo/"Production"/ASSET_ID/"03_Rig"/"RigSourcePreview.png"

    if not spec_path.is_file():
        print("PREVIEW FAIL: missing",spec_path); return 2
    spec=yaml.safe_load(spec_path.read_text(encoding="utf-8"))

    canvas=Image.new("RGBA",(1024,1024),(0,0,0,0))
    missing=[]

    for part in sorted(spec["parts"], key=lambda p:p["z_order"]):
        name=part["name"]
        if name=="Weapon":
            continue
        src=src_dir/f"{name}.png"
        if not src.is_file():
            missing.append(name); continue

        im=Image.open(src).convert("RGBA")
        bbox=im.getchannel("A").getbbox()
        if not bbox: continue
        crop=im.crop(bbox)

        x0,y0,x1,y1=part["guide_box_px"]
        bw,bh=x1-x0,y1-y0
        scale=min(bw/crop.width,bh/crop.height)
        crop=crop.resize((max(1,round(crop.width*scale)),max(1,round(crop.height*scale))),Image.Resampling.LANCZOS)
        x=x0+(bw-crop.width)//2
        y=y0+(bh-crop.height)//2
        canvas.alpha_composite(crop,(x,y))

    canvas.save(out,"PNG")
    if missing:
        print("PREVIEW WARNING missing:",", ".join(missing))
    print("RIG SOURCE PREVIEW: PASS")
    print("Preview:",out)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
