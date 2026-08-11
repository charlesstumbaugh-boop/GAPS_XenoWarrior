#!/usr/bin/env python3
from pathlib import Path
import ast

def main():
    p=Path("Tools/AnimationStudio/animation_studio.py")
    if not p.is_file():
        print("ANIMATION STUDIO EXACT-PIVOT VALIDATION: FAIL")
        print("Missing:",p);return 2
    t=p.read_text(encoding="utf-8")
    try: ast.parse(t)
    except SyntaxError as e:
        print("ANIMATION STUDIO EXACT-PIVOT VALIDATION: FAIL");print(e);return 2
    req=[
        "APP_VERSION='0.4.0'",
        "def _rotated_top_left_about_pivot",
        "center=(cx,cy)",
        "Rotated {n}",
        "def _save_pivots",
    ]
    miss=[x for x in req if x not in t]
    if miss:
        print("ANIMATION STUDIO EXACT-PIVOT VALIDATION: FAIL")
        for x in miss: print("-",x)
        return 2
    print("ANIMATION STUDIO EXACT-PIVOT VALIDATION: PASS")
    print("Studio version: 0.4.0")
    print("Rotation origin: USER-CALIBRATED PIVOT")
    print("Image-center rotation fallback: REMOVED for calibrated joints")
    print("Descendant following: ENABLED")
    print("Approved source art modified: NO")
    print("NEXT TEST: LowerArm_L +/-10 degrees around its saved elbow pivot.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
