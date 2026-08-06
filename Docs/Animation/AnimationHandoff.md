# GAPS Animation Handoff Guide

## Objective

Define one reusable path from an approved Gold Master to editable animation
source, exported frames, Unity import, and repository return.

## Workflow

```text
Approved Gold Master
→ animation source project
→ exported PNG frames
→ validation
→ Unity import
→ reviewed animation clip
```

## 1. Gold Master input

Use only:

```text
Reference/GoldMasters/<ASSET-ID>/Design/
    <ASSET-ID>_DESIGN_MASTER_v001.png
```

Never animate from a draft candidate. Never save animation work into the Gold
Master folder.

## 2. Editable animation source

Store the animation software project here:

```text
Source/Characters/<ASSET-ID>/Animation/<ACTION>/
```

Examples:

```text
Source/Characters/CHR-GRUNT-001/Animation/Idle/
    CHR-GRUNT-001_IDLE_v001.kra

Source/Characters/CHR-GRUNT-001/Animation/Death/
    CHR-GRUNT-001_DEATH_v001.aseprite
```

Use the native source format of the selected animation software.

## 3. Exported PNG frames

Store exported frames here:

```text
Assets/Characters/<ASSET-ID>/Animations/<ACTION>/v001/Frames/
```

Naming:

```text
<ASSET-ID>_<ACTION>_F##_v001.png
```

Example:

```text
CHR-GRUNT-001_IDLE_F01_v001.png
CHR-GRUNT-001_IDLE_F02_v001.png
```

## 4. Frame requirements

Every frame must preserve:

- 1024 × 1024 canvas unless the asset specification says otherwise;
- true alpha transparency;
- bottom-center pivot;
- stable baseline and scale;
- full-body visibility;
- approved palette, outline, helmet, armor, weapon, and lighting;
- character identity.

Animation may move body parts. It may not redesign the asset.

## 5. Optional sprite sheet

Path:

```text
Assets/Characters/<ASSET-ID>/Animations/<ACTION>/v001/
    <ASSET-ID>_<ACTION>_SPRITESHEET_v001.png
```

Metadata example:

```yaml
asset_id: CHR-GRUNT-001
action: idle
version: v001
frame_count: 6
frame_width: 1024
frame_height: 1024
layout: {columns: 6, rows: 1}
pivot: {mode: bottom_center, x: 0.5, y: 0.0}
frames_per_second: 8
loop: true
```

## 6. Unity destination

Inside the Unity project:

```text
Assets/GameArt/Characters/<ASSET-ID>/
├── Sprites/
├── Animations/
├── Controllers/
└── Materials/
```

Recommended import defaults:

```text
Texture Type: Sprite (2D and UI)
Sprite Mode: Single for individual frames
Sprite Mode: Multiple for sprite sheets
Pixels Per Unit: 100
Mesh Type: Full Rect
Pivot: Bottom Center
Filter Mode: Point
Compression: None
Generate Mip Maps: Off
Alpha Is Transparency: On
```

Clip naming:

```text
<ASSET-ID>_<ACTION>_v001.anim
```

Controller naming:

```text
<ASSET-ID>_CONTROLLER_v001.controller
```

## 7. What returns to GAPS

Commit:

```text
Source/Characters/<ASSET-ID>/Animation/<ACTION>/
Assets/Characters/<ASSET-ID>/Animations/<ACTION>/v001/Frames/
Assets/Characters/<ASSET-ID>/Animations/<ACTION>/v001/*.png
Assets/Characters/<ASSET-ID>/Animations/<ACTION>/v001/*.yaml
```

Do not commit Unity cache, Library, Temp, Logs, or build-output folders.

## 8. Definition of Done

- editable source saved;
- frames exported;
- frames validated;
- pivot and baseline stable;
- identity unchanged;
- Unity import tested;
- animation clip plays correctly;
- files committed and pushed.

This workflow applies to characters, enemies, bosses, and animated props. The
asset template and required animation states change; the pipeline does not.
