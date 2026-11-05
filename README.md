# C3MechV4.2.0 — release candidate 3

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

This development snapshot provides C3MechV4.2.0-rc.3 for public testing. It
adopts the optimized ammonia chemistry described in the
[release notes](RELEASES/V4.2.0/RELEASE_NOTES.md), based on C3MechV4.0.1 with
the reviewed corrections retained. The associated ammonia paper is being
prepared for submission to *Combustion and Flame*. The preprint citation will
be added when available.

The stable model remains available on the [main branch](https://github.com/C3Mech/C3Mech/tree/main).
This release candidate may change before the final C3MechV4.2.0 release.

## Download compiled models

The [V4.2.0-rc.3 release](https://github.com/C3Mech/C3Mech/releases/tag/V4.2.0-rc.3)
provides the compiled CHEMKIN models, independent-collider Cantera YAML models,
model catalogue and current species dictionary. Use the model catalogue to
select a submodel and report its model identifier when using it.

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
the solver. The adopted ammonia fit uses LMR-R. Generated `_Cantera.CKI` and
YAML filenames identify solver output formats.

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
