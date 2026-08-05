# GAPS_XenoWarrior Compiler

## Purpose

The Compiler is responsible for transforming structured GameArtBible specifications into deterministic AI generation requests.

The compiler never invents information.

The compiler only assembles information that already exists inside the repository.

This guarantees that every prompt is reproducible.

---

# Philosophy

Traditional AI workflows rely on manually written prompts.

GAPS_XenoWarrior does not.

Prompts are build artifacts.

The repository is the source code.

---

# Compiler Responsibilities

The compiler is responsible for:

- Reading specifications
- Resolving inheritance
- Resolving material definitions
- Resolving palette references
- Resolving construction rules
- Resolving animation contracts
- Resolving export contracts
- Producing deterministic prompts
- Producing review templates
- Producing generation manifests

The compiler is NOT responsible for making artistic decisions.

---

# Build Pipeline

```
GameArtBible

↓

Core Contracts

↓

Construction Specifications

↓

Material Specifications

↓

Asset Design

↓

Asset Production

↓

Prompt Generation

↓

AI Image Generation

↓

Review

↓

Approval

↓

Repository Update
```

---

# Input

The compiler reads:

Core/

Specifications/

Characters/

Enemies/

Weapons/

FX/

Templates/

---

# Output

The compiler produces:

Prompt.md

GenerationManifest.yaml

ReviewTemplate.yaml

AssetManifest.yaml

---

# Compiler Rules

1. Never invent missing values.

2. Never override approved specifications.

3. Never ignore inherited contracts.

4. Never generate prompts using raw HEX colors.

5. Never use free-form rendering descriptions.

6. Every prompt must reference repository versions.

---

# Build Order

The compiler resolves information in this order:

1. VERSION.yaml

2. Core Contracts

3. Asset Class

4. Construction Rules

5. Materials

6. Palette

7. Asset Design

8. Production Rules

9. Prompt Rules

10. Prompt Output

---

# Generated Prompt Sections

Every prompt shall contain the following sections:

- Project
- Rendering
- Camera
- Lighting
- Palette
- Construction
- Materials
- Asset Definition
- Animation
- Export
- Restrictions

---

# Build Manifest

Every generated asset produces:

Prompt.md

GenerationManifest.yaml

ReviewTemplate.yaml

BuildLog.yaml

No generation is allowed without a Build Manifest.

---

# Long-Term Goal

The compiler should eventually support multiple AI providers while producing functionally equivalent prompts.

Changing AI providers should not require changing the GameArtBible.

Only the compiler should require updates.
