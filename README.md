# C3MechV4.2.0 — release candidate 3

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

This is a prerelease of C3MechV4.2.0, which will supersede C3MechV4.0.1.
It adopts the optimized ammonia chemistry described in the
[release notes](RELEASES/V4.2.0/RELEASE_NOTES.md). The associated ammonia paper
is being prepared for submission to *Combustion and Flame*. The preprint
citation will be added when available.

The stable model remains available on the [main branch](https://github.com/C3Mech/C3Mech/tree/main).
This release candidate may change before the final C3MechV4.2.0 release.

## Download compiled models

The [V4.2.0-rc.3 release](https://github.com/C3Mech/C3Mech/releases/tag/V4.2.0-rc.3)
provides compiled models in CHEMKIN and Cantera YAML formats, together with
the model catalogue and current species dictionary. Use the model catalogue to
select a submodel and report its model identifier when using it.

We recommend the [linear mixture rule in reduced pressure (LMRR)](https://doi.org/10.1016/j.proci.2016.06.068). The Cantera
YAML models use LMRR. For simulation software that reads mechanisms in CHEMKIN
format but does not support LMRR, `LEGACY/` provides an independent-collider
(IC) kinetics file. It uses the same thermochemistry and transport data as
the main model.

The release keeps carbon folders such as `C0/` and `C1-C2/` at the top level.
Each submodel uses the following layout. Here,
`<model>` stands for the filename prefix, which includes the C3Mech version,
model identifier and temperature range where applicable.

```text
<carbon-group>/
└── <submodel>/
    ├── <model>.CKI       # Main kinetics (LMRR)
    ├── <model>.THERM     # Thermochemistry
    ├── <model>.TRAN      # Transport
    ├── <model>.yaml      # Cantera model (LMRR)
    └── LEGACY/
        └── <model>_IC.CKI
```

For Cantera, load the `.yaml` file using Cantera 3.1 or later. For software
that reads CHEMKIN format, use the `.CKI` file together with its matching
`.THERM` and `.TRAN` files. Use `LEGACY/<model>_IC.CKI` when the solver does
not support LMRR, together with the property files in its parent directory.

The existing `FULL_MODEL/` and `PRECOMPILED/` directories retain the earlier
C3MechV4.0.1 files, whose filenames identify that version. They are historical
outputs; use the candidate release download for V4.2.0-rc.3.

## Compile models

The public compiler supports all valid combinations of the supplied public
submodules. See [COMPILER/README.md](COMPILER/README.md) for environment setup,
model selection and generation of all combinations. No separate validation
repository or internal source tree is required.

Source pairs identify their collider formulation. `_IC.MECH` uses the
independent-collider formulation. The unsuffixed counterpart contains
`LOWMX/LOWSP` input for the linear mixture rule in reduced pressure
(LMR-R, also called LMRR) or pressure (LMR-P, also called LMRP), as selected by
the solver. The adopted ammonia fit uses LMR-R. Collider formulations and
solver file formats are separate choices.

The [species dictionary instructions](SPECIES_DICTIONARY/README.md) explain
how to generate the document from the current species CSV. The
[release instructions](RELEASES/README.md) describe compilation and packaging.
Scientific validation and release audits are carried out internally.

## Citation and license

Cite the applicable C3Mech publications and the adopted ammonia work listed
in [CITATION.cff](CITATION.cff) and the release notes. The C3MechV4.0 baseline
is described in [Pratali Maffei et al. (2025)](https://doi.org/10.1016/j.jaecs.2025.100385)
and its [corrigendum](https://doi.org/10.1016/j.jaecs.2026.100462).

Model files use the existing [CC BY 4.0 license](LICENSE). The compiler and
species-dictionary tools retain their MIT licenses.

For questions, open an issue or contact
[Luna Pratali Maffei](mailto:luna.pratali@polimi.it) or
[Raymond Langer](mailto:r.langer@itv.rwth-aachen.de).
