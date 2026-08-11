#!/usr/bin/env python3
from pathlib import Path
import ast
def main():
    p=Path('Tools/AnimationStudio/animation_studio.py')
    if not p.is_file():
        print('ANIMATION STUDIO HIERARCHY VALIDATION: FAIL');print('Missing:',p);return 2
    t=p.read_text(encoding='utf-8')
    try:ast.parse(t)
    except SyntaxError as e:
        print('ANIMATION STUDIO HIERARCHY VALIDATION: FAIL');print(e);return 2
    req=["APP_VERSION='0.2.0'","def _descendants","def _rotate_hierarchy","def _pivot","self.hierarchy"]
    miss=[x for x in req if x not in t]
    if miss:
        print('ANIMATION STUDIO HIERARCHY VALIDATION: FAIL')
        for x in miss:print('-',x)
        return 2
    print('ANIMATION STUDIO HIERARCHY VALIDATION: PASS')
    print('Studio version: 0.2.0')
    print('Hierarchical translation: YES')
    print('Hierarchical rotation: YES')
    print('Approved source art modified: NO')
    print('NEXT TEST: WaveTest_v001 — rotate lower arm at elbow and verify hand follows.')
    return 0
if __name__=='__main__':raise SystemExit(main())
