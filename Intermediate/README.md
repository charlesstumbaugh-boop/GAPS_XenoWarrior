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

Schemas

Contains the rules that define which fields every IAS file must contain.

Example:
Schemas/IAS.schema.yaml
Assets

Contains the current approved IAS for each asset.

Examples:

Assets/PLAYER_001.yaml
Assets/ENEMY_GRUNT_001.yaml
Assets/WEAPON_RIFLE_001.yaml
Builds

Contains records created for individual generation attempts.

Examples:

Builds/PLAYER_001/idle/v001/
Builds/ENEMY_GRUNT_001/attack/v003/

Each build may eventually contain:

IAS.yaml
Prompt.md
GenerationManifest.yaml
Review.yaml
BuildLog.yaml

Not all of these files are required during the manual foundation phase.

Manual Workflow

Until automation is intentionally introduced, use this workflow:

1. Read the approved GameArtBible files.

2. Create or update the asset's IAS file.

3. Review the IAS with the project owner.

4. Mark the IAS as APPROVED.

5. Create a generation prompt from the approved IAS.

6. Generate the image or sprite sheet.

7. Compare the result against the IAS and approved reference images.

8. Record the result in a review file.

9. Approve or reject the generated artwork.

10. Update the GameArtBible only when the project owner explicitly approves
    a design change.
Source-of-Truth Rules

The order of authority is:

1. GameArtBible Core contracts
2. Approved construction and material specifications
3. Approved asset Design specification
4. Approved asset Production specification
5. Approved IAS
6. Approved reference images
7. Generated prompts
8. Unreviewed generated artwork

A lower-level item may not silently override a higher-level item.

IAS Rules

Every IAS must:

Have a unique asset ID.
Record its version.
Record the GameArtBible version used.
List all inherited specifications.
Resolve palette references to approved palette IDs.
Identify all materials.
Define construction and proportions.
Define camera and orientation requirements.
Define animation requirements when applicable.
Define export requirements.
List prohibited changes.
Record approval status.
Avoid undocumented artistic decisions.
Missing Information

An IAS must never invent a missing value.

When required information is unavailable, use:

value: null
resolution_status: REQUIRES_REVIEW

The asset must not proceed to production until the missing requirement is
approved.

Change Control

Approved IAS files are not silently overwritten.

A change requires:

A review record
Project-owner approval
A version increase
A changelog entry

Rejected generated artwork does not automatically change the IAS.

The IAS changes only when the project owner intentionally changes the approved
asset design or production requirements.

Relationship to Prompts

Prompts are temporary build outputs.

The IAS is the durable asset definition.

A prompt may be rewritten for a different image-generation system without
changing the IAS.

No important design rule should exist only inside a prompt.

Relationship to the Future Compiler

The future compiler may automate the following work:

Reading GameArtBible files
Resolving inherited specifications
Building IAS files
Translating IAS files into provider-specific prompts
Creating review templates
Creating generation manifests

The future compiler must not:

Invent design information
Approve assets
Change approved specifications
Rewrite the GameArtBible without explicit human approval

Automation is optional and will be introduced only after the manual workflow is
stable and understood.

Current Operating Rule

For the foundation phase:

Store structured specifications first. Automate only after the specifications
successfully produce consistent artwork through the manual workflow.
