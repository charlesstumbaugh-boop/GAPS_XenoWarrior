# GAPS Tool Handoff Standard

GAPS must never trap an asset inside one AI, one archive type, one art program,
or one game engine.

The GitHub repository is the source of truth. ZIP files are only delivery
containers.

## Canonical repository form

Every important production item must exist as normal files:

```text
Reference/Concepts/.../Concept.png
Reference/Identity/.../IdentityLock.yaml
Reference/GoldMasters/.../DesignMaster.png
Production/.../Rig/RigSpecification.yaml
Production/.../Rig/Parts/*.png
Production/.../Animation/Idle/v001/Frames/*.png
Production/.../Animation/Idle/v001/AnimationMetadata.yaml
```

No tool should need to unzip an archive to understand an asset.

## AI handoff

Give an AI only the files needed for the task:

- approved concept PNG;
- Gold Master PNG;
- IdentityLock.yaml;
- RigSpecification.yaml;
- relevant Markdown instructions.

## Krita handoff

Krita receives PNG visual assets and the rig specification. It may produce a
`.kra` source file, but it must also export portable PNG frames.

## Unity handoff

Unity receives PNG frames or sprite sheets plus documented pivot,
pixels-per-unit, frame rate, loop state, and animation metadata.

## ZIP policy

ZIP is allowed for download, transport, backup, and releases. It is not allowed
as the only canonical representation of an asset.

## Portability acceptance test

An asset passes when:

1. A human can browse it in GitHub.
2. An AI can receive individual source-of-truth files.
3. Krita can consume the visual and rig files.
4. Unity can consume the exported frames or sprite sheet.
5. No critical data exists only in chat history.
6. No critical data exists only inside a ZIP.
