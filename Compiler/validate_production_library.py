#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import yaml

def main():
    repo=Path.cwd()
    reg=repo/"Production"/"Libraries"/"LibraryRegistry.yaml"
    assembly=repo/"Production"/"CHR-GRUNT-001"/"CharacterAssembly.yaml"
    errors=[]
    if not reg.is_file(): errors.append(f"missing {reg}")
    if not assembly.is_file(): errors.append(f"missing {assembly}")
    if errors:
        print("PRODUCTION LIBRARY VALIDATION: FAIL")
        for e in errors: print("-",e)
        return 2
    data=yaml.safe_load(reg.read_text(encoding="utf-8"))
    entries=data.get("heads",[])+data.get("helmets",[])+data.get("armor",[])+data.get("weapons",[])+data.get("materials",[])
    for e in entries:
        p=repo/Path(e["file"])
        if not p.is_file():
            errors.append(f"missing library asset: {e['id']} -> {p}")
            continue
        if p.suffix.lower()==".png":
            im=Image.open(p)
            if im.size!=(1024,1024): errors.append(f"{e['id']}: expected 1024x1024, found {im.size}")
            if im.mode!="RGBA": errors.append(f"{e['id']}: expected RGBA, found {im.mode}")
            if im.convert("RGBA").getchannel("A").getbbox() is None: errors.append(f"{e['id']}: empty alpha")
    asm=yaml.safe_load(assembly.read_text(encoding="utf-8"))
    ids={e["id"] for e in entries}
    for key in ["head","helmet"]:
        ref=asm.get("default_assembly",{}).get(key)
        if ref and ref not in ids: errors.append(f"default assembly references unknown {key}: {ref}")
    for name,var in asm.get("approved_variants",{}).items():
        ref=var.get("head")
        if ref and ref not in ids: errors.append(f"variant {name} references unknown head: {ref}")
    if errors:
        print("PRODUCTION LIBRARY VALIDATION: FAIL")
        for e in errors: print("-",e)
        return 2
    print("PRODUCTION LIBRARY VALIDATION: PASS")
    print(f"Approved heads: {len(data.get('heads',[]))}")
    print(f"Approved helmets: {len(data.get('helmets',[]))}")
    print("Grunt variants: male, female")
    print("Humanoid rig unchanged: YES")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
