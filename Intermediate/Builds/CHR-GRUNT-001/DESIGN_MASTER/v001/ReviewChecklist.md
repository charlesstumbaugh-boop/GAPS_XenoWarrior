# Asset Review Checklist

- **Generator version:** 1.0.0
- **Build ID:** `CHR_GRUNT_001_DESIGN_MASTER_v001`
- **Asset ID:** `CHR-GRUNT-001`
- **Asset name:** Grunt Soldier
- **Build mode:** Draft
- **Production authorized:** No

## Reviewer Instructions

Review the generated candidate against the compiled Prompt.md, declared references, and this checklist. Do not promote the asset when any required item fails.

## File and Output Checks

- [ ] Exactly one production asset is present
- [ ] Canvas is 1024 × 1024 pixels
- [ ] PNG uses real RGBA transparency
- [ ] No baked checkerboard or opaque background is present
- [ ] Entire body or asset is visible with no clipping
- [ ] No title, labels, footer, logo, UI panel, or presentation layout is present

## Identity and Visual Checks

- [ ] Forward-facing
- [ ] Silhouette distinct from player
- [ ] Approved palette
- [ ] Correct cel shading
- [ ] Smaller rifle than player
- [ ] Distinct simplified helmet
- [ ] Transparent background
- [ ] Entire body visible
- [ ] Animation-ready proportions
- [ ] Friendly npc readability

## Reference Contract Checks

- [ ] Reference `REF_CHR_PLAYER_001_GOLD_MASTER` is resolved — resolved by compiler
- [ ] Reference `REF_CHR_PLAYER_001_GOLD_MASTER` was used only as `style_only`
- [ ] `REF_CHR_PLAYER_001_GOLD_MASTER` did not transfer silhouette, helmet, armor layout, weapon identity, or proportions

## Automatic Rejection Review

- [ ] Not present: Player clone
- [ ] Not present: Player recolor
- [ ] Not present: Presentation sheet
- [ ] Not present: Baked checkerboard
- [ ] Not present: Opaque background
- [ ] Not present: Cropped body
- [ ] Not present: Incorrect camera orientation
- [ ] Not present: Unapproved palette
- [ ] Not present: Photorealistic or 3d rendering

## Compiler Warnings

- [ ] Review warning: IAS document status is DRAFT, not APPROVED.

## Review Decision

- [ ] PASS — candidate may proceed to validate_reference.py
- [ ] FAIL — candidate must be rejected or revised

**Reviewer:** ______________________________

**Review date:** ___________________________

**Notes:**

____________________________________________________________________

____________________________________________________________________
