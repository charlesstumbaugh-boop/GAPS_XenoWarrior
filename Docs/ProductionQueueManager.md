# GAPS Production Queue Manager

The queue manager removes the need to remember or manually track the next body part.

## Commands

Show the current repository-derived queue:

```cmd
python Compiler\build_queue.py --show
```

Synchronize `gaps.py` and rebuild the queue:

```cmd
python Compiler\build_queue.py --sync
```

Create the handoff for the next genuinely missing part:

```cmd
python Compiler\build_queue.py --handoff-next
```

## Source of truth

The queue is rebuilt from actual PNG files under:

```text
Production/<ASSET-ID>/03_Parts/
```

`Management/ProductionQueue.yaml` is generated output, not manually maintained
production truth.

## Current pilot asset

For `CHR-GRUNT-001`, after the approved `UpperArm_L` has been packaged,
the next expected missing part should be `LowerArm_L`.

The approved LowerArm_L image still must be passed through
`build_production_pack.py` before the queue advances.
