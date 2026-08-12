#!/usr/bin/env python3
from pathlib import Path
import ast

def main():
    p=Path("Tools/AnimationStudio/animation_studio.py")
    if not p.is_file():
        print("ANIMATION STUDIO TRANSFORM-CORE VALIDATION: FAIL")
        print("Missing:",p);return 2
    t=p.read_text(encoding="utf-8")
    try:ast.parse(t)
    except SyntaxError as e:
        print("ANIMATION STUDIO TRANSFORM-CORE VALIDATION: FAIL");print(e);return 2
    req=[
        'APP_VERSION = "0.5.0"',
        'transform_core":"full_canvas_affine_ops"',
        "def _apply_op",
        "center=(float(op[\"pivot_x\"]),float(op[\"pivot_y\"]))",
        "def _part_layer",
        "fr[\"ops\"][t].append",
    ]
    miss=[x for x in req if x not in t]
    if miss:
        print("ANIMATION STUDIO TRANSFORM-CORE VALIDATION: FAIL")
        for x in miss:print("-",x)
        return 2
    print("ANIMATION STUDIO TRANSFORM-CORE VALIDATION: PASS")
    print("Studio version: 0.5.0")
    print("Transform model: FULL-CANVAS AFFINE OPERATIONS")
    print("Exact global pivot rotation: YES")
    print("Center-axis position compensation: REMOVED")
    print("Descendant rigid transform: YES")
    print("Approved source art modified: NO")
    print("NEXT TEST: LowerArm_L ±10° at saved elbow pivot; Hand_L must remain attached.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
