# Intermediate Asset Specifications

## Purpose

The `Intermediate` folder stores complete, AI-independent descriptions of
assets after all approved GameArtBible rules have been combined.

These files are called Intermediate Asset Specifications, abbreviated as IAS.

An IAS is not an image prompt.

An IAS is not production artwork.

An IAS is a complete record of what an asset is supposed to be.

---

## Current Project Phase

During the current manual phase, IAS files will be created and reviewed by
ChatGPT and the project owner.

No Python scripts or automated compiler are required.

The project owner may copy the approved IAS content into this repository and
commit it through the GitHub website.

Automation may be added later without changing the approved GameArtBible rules.

---

## Why This Folder Exists

Different image-generation systems interpret prompts differently.

The IAS provides one stable asset definition that remains unchanged even when
the image provider or prompt wording changes.

The same IAS may later be translated into prompts for:

- ChatGPT image generation
- Other AI image-generation systems
- Human concept artists
- Human animators
- Unity production workflows
- Future tools not yet selected

The IAS is therefore the stable contract between the GameArtBible and the
system producing the artwork.

---

## Folder Structure

```text
Intermediate/

├── README.md
├── Schemas/
├── Assets/
└── Builds/
