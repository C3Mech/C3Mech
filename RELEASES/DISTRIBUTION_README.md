# C3MechV4.2.0 — public release candidate 3

This distribution contains the compiled public submodels of C3MechV4.2.0-rc.3.
The model and its supporting ammonia manuscript remain under review.

Open [MODEL_CATALOG.md](MODEL_CATALOG.md) to choose a submodel. Each model
has a model identifier, abbreviated MID, which should be reported when the
model is used. CHEMKIN directories contain the kinetics, thermochemistry and
transport files. Cantera directories contain independent-collider kinetics
and YAML files. The CHEMKIN `LOWMX/LOWSP` input supports linear mixture rules
in reduced pressure or pressure, as selected by the solver.

The current species dictionary is in
[SPECIES_DICTIONARY/species_dict.pdf](SPECIES_DICTIONARY/species_dict.pdf).
The CSV in the same directory contains the corresponding source definitions.
[MANIFEST.json](MANIFEST.json) records the source identity, model inventory
and file checksums.

Read [RELEASE_NOTES.md](RELEASE_NOTES.md) for the model changes and citation
requirements. The ammonia preprint citation will be added when available.
The model files use the [CC BY 4.0 license](LICENSE); see
[USAGE_TERMS.md](USAGE_TERMS.md) and [CITATION.cff](CITATION.cff).

Source and compilation instructions are available from the
[public repository](https://github.com/C3Mech/C3Mech/tree/dev).
The fixed release is [V4.2.0-rc.3](https://github.com/C3Mech/C3Mech/releases/tag/V4.2.0-rc.3).
