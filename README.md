# GameArtBible
### Version 0.1.0
**Project Status:** Foundation

---

# Overview

GameArtBible is the canonical production specification for the VR Rail Shooter project.

This repository is **not** concept art.

It is **not** a prompt library.

It is **not** game code.

It is the single source of truth that defines every visual rule used to create production-quality game assets.

Every AI-generated image, sprite sheet, animation, background, effect, UI element, and prop must conform to this specification.

If an asset conflicts with this repository, the repository is considered correct.

---

# Project Goals

The GameArtBible exists to eliminate the most common problems encountered when generating AI artwork:

- Style drift
- Palette changes
- Perspective inconsistencies
- Character redesigns
- Lighting differences
- Animation inconsistency
- Prompt rewriting
- Asset duplication
- Loss of production history

The repository creates a repeatable pipeline that allows future assets to be generated with predictable results.

---

# Philosophy

The GameArtBible is treated as source code.

Images are considered compiled output.

The YAML specifications define the project.

Generated PNG files are products of those specifications.

The specification always has priority over generated artwork.

---

# Repository Structure

```
GameArtBible/

README.md
CHANGELOG.md
VERSION.yaml

/Core
/Characters
/Enemies
/Bosses
/Weapons
/Props
/FX
/Backgrounds
/UI
/Templates
/Reviews
/ReferenceImages
/Scripts
```

Each folder has a specific responsibility.

---

# Folder Responsibilities

## Core

Contains immutable project-wide specifications.

Examples:

- Rendering Rules
- Camera Rules
- Palette
- Lighting
- Animation Standards
- Export Standards

These files affect every asset.

---

## Characters

Contains canonical specifications for all player characters.

Each character has:

- Unique ID
- Version
- DNA Specification
- Animation Specification
- Export Rules
- Reference Images
- Revision History

---

## Enemies

Contains specifications for all enemy types.

Each enemy is independent.

No enemy inherits artwork from another enemy.

Shared rules come from `/Core`.

---

## Bosses

Contains all boss specifications.

Bosses may reference shared rules but have independent DNA.

---

## Weapons

Contains specifications for all weapons.

Weapons are independent assets.

Each weapon maintains its own revision history.

---

## Props

Interactive objects.

Static objects.

Environmental objects.

Collectibles.

---

## FX

Visual effects.

Examples:

- Muzzle Flash
- Smoke
- Sparks
- Plasma
- Fire
- Explosions

---

## Backgrounds

Contains all environment specifications.

Each environment defines:

- Perspective
- Layers
- Color Rules
- Animation Rules

---

## UI

HUD

Menus

Crosshairs

Indicators

Notifications

---

## Templates

Reusable generation templates.

These are never asset-specific.

Templates reference GameArtBible specifications.

---

## Reviews

Every generated asset receives a review document.

Reviews compare generated artwork against the approved specification.

Reviews do not modify specifications.

Reviews only document differences.

---

## ReferenceImages

Approved production images.

Only approved assets belong here.

ReferenceImages are never overwritten.

---

## Scripts

Automation tools.

Validation scripts.

Prompt generators.

Asset comparison utilities.

Future Unity export helpers.

---

# Source of Truth

The order of authority is:

1. Core Specifications
2. Asset DNA Files
3. Approved Reference Images
4. Prompt Templates
5. Generated Artwork

If conflicts exist, higher authority wins.

---

# Asset Lifecycle

Every asset follows the same lifecycle.

```
Specification

↓

Generation

↓

Review

↓

Approval

↓

Repository Update

↓

Production
```

No asset bypasses review.

---

# Versioning

Semantic Versioning is used.

Major.Minor.Patch

Examples

1.0.0

1.1.0

1.1.3

2.0.0

Rules

Major

Breaking visual changes.

Minor

New approved features.

Patch

Corrections.

---

# Immutable Rules

Approved specifications are immutable.

Specifications never change without:

- Review
- Approval
- Version Increment
- Changelog Entry

---

# AI Workflow

Every AI generation must begin by reading:

Core Specifications

↓

Relevant Asset DNA

↓

Prompt Template

↓

Reference Images

↓

Generate Artwork

↓

Create Review

↓

Human Approval

↓

Repository Update

No prompt should contain visual information that already exists in the repository.

The repository replaces prompt engineering.

---

# Approval Process

Every production asset requires approval.

Review status:

DRAFT

IN REVIEW

APPROVED

REJECTED

ARCHIVED

Only APPROVED assets become reference material.

---

# Changelog Policy

Every approved modification must produce:

Version increment

Review document

Changelog entry

Specification update

No undocumented changes are permitted.

---

# Design Principles

The repository favors:

Consistency over creativity.

Repeatability over randomness.

Specification over interpretation.

Documentation over memory.

Every visual decision should exist somewhere in this repository.

Nothing important should exist only inside a prompt.

---

# Long-Term Vision

The GameArtBible is intended to become a complete production specification capable of generating a commercial-quality asset library while maintaining visual consistency across the entire project.

The long-term objective is to allow any approved AI system or artist to recreate assets from the specification with minimal interpretation.

The repository evolves only through explicit review and approval.

