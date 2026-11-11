# C3MechV4.2.0

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

C3Mech is a comprehensive chemical kinetic model for conventional and renewable
fuels, including hydrocarbons, hydrogen, ammonia and oxygenated fuels. Its
modular structure supports models tailored to different fuel mixtures.

## Download models

**[Download C3MechV4.2.0-rc.3](https://github.com/C3Mech/C3Mech/releases/tag/V4.2.0-rc.3)**

The release ZIP contains the full model and smaller submodels in CHEMKIN and
Cantera YAML formats, with thermochemistry and transport data.
The README inside the ZIP explains which files to use.

This prerelease of C3MechV4.2.0 incorporates optimized ammonia chemistry and
will supersede C3MechV4.0.1. See the
[release notes](RELEASES/V4.2.0/RELEASE_NOTES.md) for the changes.
[All releases](https://github.com/C3Mech/C3Mech/releases) include earlier versions.

## What to cite

When using the adopted ammonia chemistry, cite the ammonia preprint alongside
the C3Mech publication and its corrigendum:

- S. Girhe, F. Loffredo, R. Langer, H. Pitsch (2026).
  *Ammonia combustion kinetic model optimization using elementary rate
  coefficient and global combustion data*. [ChemRxiv preprint, version 1](https://doi.org/10.26434/chemrxiv.15011965/v1).
  Submitted to *Combustion and Flame*.
- L. Pratali Maffei et al. (2025).
  [Modeling combustion chemistry using C3MechV4.0: An extension to mixtures of
  hydrogen, ammonia, alkanes, and cycloalkanes](https://doi.org/10.1016/j.jaecs.2025.100385).
  *Applications in Energy and Combustion Science*, 24, 100385.
- [Corrigendum (2026)](https://doi.org/10.1016/j.jaecs.2026.100462).
  *Applications in Energy and Combustion Science*, 26, 100462.

Citation metadata are available in [CITATION.cff](CITATION.cff).

## Source and support

For custom model combinations, see the [compiler instructions](COMPILER/README.md).
Ready-to-use compiled models are distributed through the releases.

For questions, [open an issue](https://github.com/C3Mech/C3Mech/issues) or contact
[Luna Pratali Maffei](mailto:luna.pratali@polimi.it) or
[Raymond Langer](mailto:r.langer@itv.rwth-aachen.de).
Model files are licensed under [CC BY 4.0](LICENSE); the compiler and
species-dictionary tools retain their MIT licenses.
