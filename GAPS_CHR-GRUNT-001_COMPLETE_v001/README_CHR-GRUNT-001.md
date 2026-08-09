# CHR-GRUNT-001 Complete GAPS Package

Asset: **Grunt Soldier 1**  
Asset ID: `CHR-GRUNT-001`

This package captures the approved concept, identity lock, fingerprint, production
candidate, staged design master, IAS, review metadata, and a package checker.

## Important distinction

- The original concept image is the **identity authority**.
- `CHR-PLAYER-001` is **style-only authority**.
- The approval card is reference/documentation only.
- The 1024×1024 RGBA production PNG is the candidate to validate and promote.

## Install

Extract this ZIP into the root of `GAPS_XenoWarrior`.

## Run

```cmd
python Compiler\check_grunt_package.py
```

Then:

```cmd
python Compiler\validate_yaml.py
```

Then:

```cmd
python Compiler\validate_reference.py "Reference\Candidates\CHR-GRUNT-001\CHR-GRUNT-001_DESIGN_MASTER_candidate_v001.png"
```

Expected candidate hash:

`5361936e46090d3cb8c7d67dd148908bbc059b1d2e1ae56fae0b2b79af289237`

## Promotion

If reference validation and your visual review both pass, use your existing promotion tool:

```cmd
python Compiler\approve_asset.py "Reference\Candidates\CHR-GRUNT-001\CHR-GRUNT-001_DESIGN_MASTER_candidate_v001.png" --approved-by "Project Owner" --confirm-promote
```

The package includes a staged Gold Master PNG because this design was explicitly
approved, but the repository's existing `approve_asset.py` remains the official
promotion authority. If it reports that the staged Gold Master already exists,
delete only the staged Gold Master PNG from this package install and rerun
`approve_asset.py`; do not overwrite an existing officially promoted version.

## Production identity

- Friendly NPC infantry
- Lighter metallic armor than the Player
- Tan/brown tactical undersuit
- Hazard-yellow caution/friendly recognition accents
- Plasma-blue visor
- Compact service carbine
- Narrower/agile silhouette
- Not a Player recolor or reskin
