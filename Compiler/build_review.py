###############################################################################
# GAPS_XenoWarrior Build Request Template
# This file contains constraints only. Free-form prompt fields are forbidden.
###############################################################################

build:
  id: BUILD_ASSET_ID_PURPOSE_v001
  version: "0.1.0"
  status: DRAFT

asset:
  id: ASSET_ID
  ias_file: Intermediate/Assets/ASSET_ID.yaml

request:
  deliverable: ASSET_ID_DESIGN_MASTER_v001.png
  purpose: >
    State exactly which production artifact is being built and why it exists.

  output:
    output_type: static_image
    image_format: png
    width_px: 1024
    height_px: 1024
    transparent_background: true

  required:
    - clean production artwork only
    - use the approved IAS without reinterpretation

  forbidden:
    - presentation sheet
    - labels or text
    - opaque background
    - checkerboard pixels
    - crop or clipping
