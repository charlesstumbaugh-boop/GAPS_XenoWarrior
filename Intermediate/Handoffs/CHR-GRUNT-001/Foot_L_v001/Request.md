# GAPS External Manufacturing Handoff

Asset: CHR-GRUNT-001
Asset Name: Grunt Soldier 1
Part: Foot_L
Stage: parts_manufacturing
Operation: reference_locked_part_generation
Output: Production/CHR-GRUNT-001/03_Parts/Foot_L.png

## Manufacturing Task

Manufacture exactly one production PNG for `Foot_L` from the files contained in
this handoff. The repository references are authoritative.

## Hard Rules

- Do not redesign the character or requested part.
- Do not create a new character, poster, sheet, scene, or concept.
- Preserve approved identity, armor family, palette, line work, shading, and silhouette.
- Use the approved Animation Master as the character visual authority.
- If an approved counterpart part is supplied, use it as the geometry/style authority
  and produce only the required opposite-side counterpart.
- Do not introduce new armor panels, colors, lights, weapons, props, or anatomy.
- Return exactly one isolated production part.
- Final production normalization: 1024 x 1024 RGBA with true alpha transparency.
- No checkerboard, text, labels, UI, floor, scenery, or cast shadow.
- If the supplied references conflict or are insufficient, STOP and report the
  conflict instead of inventing missing design information.

## Repository Destination

`Production/CHR-GRUNT-001/03_Parts/Foot_L.png`

Read `ManufacturingContract.yaml` before generation.
