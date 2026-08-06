# GAPS Repository Validation Report

- **Validator version:** 0.1.0
- **Repository:** `C:\Projects\GAPS_XenoWarrior`
- **Generated (UTC):** `2026-08-06T17:15:23.047055+00:00`
- **Overall status:** **PASS WITH WARNINGS**
- **PASS:** 50
- **WARNING/EMPTY:** 18
- **FAIL:** 0

## Category Summary

| Category | PASS | WARNING/EMPTY | FAIL | Result |
|---|---:|---:|---:|---|
| 1. Repository Structure | 7 | 0 | 0 | **PASS** |
| 2. Required Compiler Files | 4 | 0 | 0 | **PASS** |
| 3. Required Management Files | 6 | 0 | 0 | **PASS** |
| 4. Core Specifications | 8 | 0 | 0 | **PASS** |
| 5. YAML Integrity | 21 | 18 | 0 | **WARNING** |
| 6. Build Pipeline | 4 | 0 | 0 | **PASS** |

## Detailed Results

| Category | Status | Item | Details |
|---|---|---|---|
| 1. Repository Structure | **PASS** | `Compiler` | Required folder exists. |
| 1. Repository Structure | **PASS** | `Core` | Required folder exists. |
| 1. Repository Structure | **PASS** | `Intermediate` | Required folder exists. |
| 1. Repository Structure | **PASS** | `Management` | Required folder exists. |
| 1. Repository Structure | **PASS** | `Reference` | Required folder exists. |
| 1. Repository Structure | **PASS** | `Specifications` | Required folder exists. |
| 1. Repository Structure | **PASS** | `Docs` | Required folder exists. |
| 2. Required Compiler Files | **PASS** | `Compiler/build_prompt.py` | Required file exists and contains content. |
| 2. Required Compiler Files | **PASS** | `Compiler/validate_reference.py` | Required file exists and contains content. |
| 2. Required Compiler Files | **PASS** | `Compiler/validate_yaml.py` | Required file exists and contains content. |
| 2. Required Compiler Files | **PASS** | `Compiler/requirements.txt` | Required file exists and contains content. |
| 3. Required Management Files | **PASS** | `Management/ProductBacklog.md` | Required file exists and contains content. |
| 3. Required Management Files | **PASS** | `Management/Sprint01.md` | Required file exists and contains content. |
| 3. Required Management Files | **PASS** | `Management/SprintReview.md` | Required file exists and contains content. |
| 3. Required Management Files | **PASS** | `Management/DefinitionOfDone.md` | Required file exists and contains content. |
| 3. Required Management Files | **PASS** | `Management/Roadmap.md` | Required file exists and contains content. |
| 3. Required Management Files | **PASS** | `Management/ProductVision.md` | Required file exists and contains content. |
| 4. Core Specifications | **PASS** | `Core/Rendering.yaml` | Required file exists and contains content. |
| 4. Core Specifications | **PASS** | `Core/Palette.yaml` | Required file exists and contains content. |
| 4. Core Specifications | **PASS** | `Core/Camera.yaml` | Required file exists and contains content. |
| 4. Core Specifications | **PASS** | `Core/Lighting.yaml` | Required file exists and contains content. |
| 4. Core Specifications | **PASS** | `Core/Validation.yaml` | Required file exists and contains content. |
| 4. Core Specifications | **PASS** | `Core/Export.yaml` | Required file exists and contains content. |
| 4. Core Specifications | **PASS** | `Core/Naming.yaml` | Required file exists and contains content. |
| 4. Core Specifications | **PASS** | `Core/PromptRules.yaml` | Required file exists and contains content. |
| 5. YAML Integrity | **PASS** | `.github/workflows/gaps-validation.yml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Core/Animation.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Core/Camera.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Core/Export.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Core/Gameplay.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Core/Lighting.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Core/Naming.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Core/Palette.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Core/PromptRules.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Core/Rendering.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Core/Validation.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Intermediate/Assets/PLAYER_001.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Intermediate/Builds/PLAYER_001/DESIGN_MASTER/v001/Build.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Intermediate/Builds/PLAYER_001/DESIGN_MASTER/v001/GenerationManifest.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Intermediate/Schemas/IAS.schema.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **EMPTY** | `Reference/GoldMasters/CHR-PLAYER-001/Animation/Idle/Review.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **PASS** | `Reference/GoldMasters/CHR-PLAYER-001/CHR-PLAYER-001_DESIGN_MASTER_v001.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Reference/GoldMasters/CHR-PLAYER-001/Design/v001/Review.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **PASS** | `Specifications/Construction/Humanoid.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **EMPTY** | `Specifications/DroneSkeleton.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **EMPTY** | `Specifications/EyeLine.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **EMPTY** | `Specifications/HandPositions.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **EMPTY** | `Specifications/HumanoidSkeleton.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **EMPTY** | `Specifications/Materials/AlienBioTissue.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **EMPTY** | `Specifications/Materials/AlienChitin.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **EMPTY** | `Specifications/Materials/CarbonFiber.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **EMPTY** | `Specifications/Materials/EnergyPlasma.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **EMPTY** | `Specifications/Materials/MilitaryPolymer.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **PASS** | `Specifications/Materials/PaintedSteel.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **EMPTY** | `Specifications/Materials/Rubber.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **EMPTY** | `Specifications/Materials/VisorGlass.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **EMPTY** | `Specifications/MechSkeleton.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **EMPTY** | `Specifications/PlayerSkeleton.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **EMPTY** | `Specifications/PoseLibrary.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **PASS** | `Specifications/Poses/PoseLibrary.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **EMPTY** | `Specifications/QuadrupedSkeleton.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **EMPTY** | `Specifications/WeaponMounts.yaml` | Whitespace-only or empty YAML. |
| 5. YAML Integrity | **PASS** | `VERSION.yaml` | Parsed 1 document(s). |
| 5. YAML Integrity | **WARNING** | `validate_yaml.py execution` | Exit code 1. YAML INTEGRITY: WARNING |
| 6. Build Pipeline | **PASS** | `Intermediate/Builds/PLAYER_001/DESIGN_MASTER/v001/Build.yaml` | Required file exists and contains content. |
| 6. Build Pipeline | **PASS** | `Intermediate/Builds/PLAYER_001/DESIGN_MASTER/v001/Prompt.md` | Required file exists and contains content. |
| 6. Build Pipeline | **PASS** | `Intermediate/Builds/PLAYER_001/DESIGN_MASTER/v001/GenerationManifest.yaml` | Required file exists and contains content. |
| 6. Build Pipeline | **PASS** | `Intermediate/Builds/PLAYER_001/DESIGN_MASTER/v001/BuildReport.md` | Required file exists and contains content. |

## Exit Code Contract

- `0` — PASS
- `1` — PASS WITH WARNINGS
- `2` — FAIL
