# C3MechV4.2.0

This distribution contains the compiled public submodels of C3MechV4.2.0-rc.3.
The model and its supporting ammonia manuscript remain under review.

For the complete model, use [FULL_MODEL/](FULL_MODEL/):

```text
FULL_MODEL/
├── C3MechV4.2.0.CKI       # CHEMKIN-format mechanism (LMRR; uses LOWMX/LOWSP keywords)
├── C3MechV4.2.0.THERM     # Thermochemistry
├── C3MechV4.2.0.TRAN      # Transport
├── C3MechV4.2.0.yaml      # Cantera YAML mechanism (LMRR)
└── LEGACY/
    └── C3MechV4.2.0_IC.CKI
```

The full model includes all supplied submodules and their low- and
high-temperature chemistry. Open [MODEL_CATALOG.md](MODEL_CATALOG.md) to choose
a smaller submodel. Each model
has a model identifier, abbreviated MID, which should be reported when the
model is used. Each submodel provides a CHEMKIN-format mechanism, thermochemistry and
transport files, together with a Cantera YAML mechanism.

We recommend the [linear mixture rule in reduced pressure (LMRR)](https://doi.org/10.1016/j.proci.2016.06.068). The Cantera
YAML models use LMRR. For simulation software that reads mechanisms in CHEMKIN
format but does not support LMRR, `LEGACY/` provides an independent-collider
(IC) mechanism file. It uses the same thermochemistry and transport data as
the main model.

Compiled models are organized in folders such as `C0/` and `C1-C2/`.
Each submodel uses the following layout. Here,
`<model>` stands for the filename prefix, which includes the C3Mech version,
model identifier and temperature range where applicable.

```text
<group>/
└── <submodel>/
    ├── <model>.CKI       # CHEMKIN-format mechanism (LMRR; uses LOWMX/LOWSP keywords)
    ├── <model>.THERM     # Thermochemistry
    ├── <model>.TRAN      # Transport
    ├── <model>.yaml      # Cantera YAML mechanism (LMRR)
    └── LEGACY/
        └── <model>_IC.CKI
```

The YAML mechanism uses Cantera's native `linear-Burke` reactions.
For Cantera, load the `.yaml` file using Cantera 3.1 or later. For software
that reads CHEMKIN format, use the `.CKI` file together with its matching
`.THERM` and `.TRAN` files. Use `LEGACY/<model>_IC.CKI` when the solver does
not support LMRR, together with the property files in its parent directory.

The current species dictionary is in
[SPECIES_DICTIONARY/species_dict.pdf](SPECIES_DICTIONARY/species_dict.pdf).
The CSV in the same directory contains the corresponding source definitions.
[MANIFEST.json](MANIFEST.json) records the source identity, model inventory
and file checksums.

Read [RELEASE_NOTES.md](RELEASE_NOTES.md) for the model changes and citation
requirements. The ammonia [preprint is available on ChemRxiv](https://doi.org/10.26434/chemrxiv.15011965/v1)
and has been submitted to *Combustion and Flame*.
The model files use the [CC BY 4.0 license](LICENSE); see
[USAGE_TERMS.md](USAGE_TERMS.md) and [CITATION.cff](CITATION.cff).

Source and compilation instructions are available from the
[public repository](https://github.com/C3Mech/C3Mech/tree/dev).
The fixed release is [V4.2.0-rc.3](https://github.com/C3Mech/C3Mech/releases/tag/V4.2.0-rc.3).
