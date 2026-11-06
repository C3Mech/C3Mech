# Precompiled C3MechV4.2.0 models

This directory contains the compiled models supplied with
[V4.2.0-rc.3](https://github.com/C3Mech/C3Mech/releases/tag/V4.2.0-rc.3).
Use the [model catalogue](MODEL_CATALOG.md) to select a submodel and find its
model identifier. The [complete model](../FULL_MODEL/) is also provided separately.

Each submodel contains its main CHEMKIN mechanism, thermochemistry, transport
data and Cantera YAML model. We recommend the linear mixture rule in reduced
pressure (LMRR). The Cantera YAML models use LMRR and require Cantera 3.1 or later.

For simulation software that reads mechanisms in CHEMKIN format but does not
support LMRR, use the independent-collider (IC) mechanism file in `LEGACY/`,
together with the thermochemistry and transport files in its parent directory.

The release ZIP contains the same model files, with the model folders directly
at its top level. See [COMPILER/README.md](../COMPILER/README.md) to generate a
different supported selection. [MODEL_MANIFEST.json](MODEL_MANIFEST.json)
records the generation source and model-file checksums.
