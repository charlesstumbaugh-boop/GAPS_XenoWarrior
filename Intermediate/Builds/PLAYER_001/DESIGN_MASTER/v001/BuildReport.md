# GAPS_XenoWarrior Build Report

**Build ID:** `PLAYER_001_DESIGN_MASTER_v001`  
**Asset:** `PLAYER_001` — Xeno Warrior Player  
**Compiler version:** `0.4.0`  
**Generated at (UTC):** `2026-08-06T03:14:04.319619+00:00`  
**Authorization:** **TEST BUILD — NOT PRODUCTION AUTHORIZED**

## Outputs

- Prompt: `Intermediate/Builds/PLAYER_001/DESIGN_MASTER/v001/Prompt.md`
- Manifest: `Intermediate/Builds/PLAYER_001/DESIGN_MASTER/v001/GenerationManifest.yaml`
- Build report: `Intermediate/Builds/PLAYER_001/DESIGN_MASTER/v001/BuildReport.md`

## Source State

- IAS status: `DRAFT`
- Draft override used: `True`
- Dependency files loaded: `9`

## Preflight Validation

- Checks passed: `15`
- Production authorized: `False`
- PASS — No handwritten prompt fields are present.
- PASS — Output file names and extensions are valid and distinct.
- PASS — Execution policy requires repository authority and forbids handwritten prompts.
- PASS — Build objective contains no prohibited presentation or background request.
- PASS — Build identity and IAS reference are present.
- PASS — All mandatory IAS sections are present.
- PASS — IAS approval state is compatible with requested build mode.
- PASS — Generation-blocking unresolved requirements were evaluated.
- PASS — PNG, transparency, canvas dimensions, and untrimmed alignment are valid.
- PASS — Camera orientation, full visibility, and no-clipping rules are valid.
- PASS — Palette uses approved references rather than raw colors.
- PASS — Redesign is forbidden and changes require approval.
- PASS — Outline contract is explicit and valid.
- PASS — Reference policy separates visual style from asset identity.
- PASS — Reference image inventory evaluated: 1 declared.

## Warnings

- IAS document status is DRAFT, not APPROVED.
- Generation blockers remain: materials.provisional_assignments.visor, materials.provisional_assignments.under_suit, materials.provisional_assignments.gloves_and_boot_flex_sections, equipment.equipped_assets.WEAPON_PLAYER_RIFLE_001, component_design.helmet, animation.frame_requirements, reference_images.REF_PLAYER_FRONT_MASTER_001
- Reference REF_PLAYER_POSTER_001 could not be resolved: Referenced repository file does not exist: Reference/Concept/vr_rail_shooter_unified_art_bible_poster.png
- The --allow-draft override was used. Generated outputs are for compiler testing only.
- IAS status is DRAFT, not APPROVED.
- Generation-blocking IAS requirements remain: materials.provisional_assignments.visor, materials.provisional_assignments.under_suit, materials.provisional_assignments.gloves_and_boot_flex_sections, equipment.equipped_assets.WEAPON_PLAYER_RIFLE_001, component_design.helmet, animation.frame_requirements, reference_images.REF_PLAYER_FRONT_MASTER_001

## Visual Reference Enforcement

- Declared references: `1`
- `REF_PLAYER_POSTER_001` — `identity` — **UNRESOLVED**

## Reproducibility Sources

| Repository file | SHA-256 |
|---|---|
| `Intermediate/Builds/PLAYER_001/DESIGN_MASTER/v001/Build.yaml` | `a93d577d693500aa843319faf4cce92410f3ccc004c0d1ab6f640fc87bc4d8d1` |
| `Intermediate/Assets/PLAYER_001.yaml` | `cae28257616c456bc9097c2bd43a7845a1baeb4e2f891bd4ef7ca02e64e51739` |
| `Core/Rendering.yaml` | `38264a309c87c4f04b6a7e0d17ce5e5564fa684a823a17ab3aa343dd00f01891` |
| `Core/Palette.yaml` | `f9b8a731e3830cb8fe6272bcd52be3db21278ef4025bc7519c489ce53a08cbc0` |
| `Core/Camera.yaml` | `83b6f4b9da2a683e7dd26582a59af7face9daae56b4be47b5383f0c24437339a` |
| `Core/Lighting.yaml` | `140f7f29ab8aee67b8bc5b2626ca1b4f4926200e74e029433484eb82352a5d58` |
| `Core/Animation.yaml` | `206b4b2b77fbf2bd8691c50041b771008bcd349fcadc0e3b51701faab7b132bb` |
| `Core/Export.yaml` | `2aad0a7ee2a98ef8051c6f07f8da75409526f33b8b523305652434cf1007bf87` |
| `Core/Validation.yaml` | `1ac2a7a408a5ebd2c88a75ce5ec54b843b71acdaff67b7f111d65855e94ce71c` |
| `Specifications/Construction/Humanoid.yaml` | `875b17d81f81d8fa8038d5ad0da8793a6cb815c24dd18c4a6424aa908c38ce36` |
| `Specifications/Materials/PaintedSteel.yaml` | `eb91eafb75ca7b3101198ba8fe4f75bf97cdb2123ca79811f84a08c7bf522b5a` |

## Operating Rule

`Prompt.md` is a generated build artifact. Do not hand-edit it. Correct the approved YAML source or compiler, then rebuild.
