# C3MechV4.2.0

> **Release candidate:** The chemical kinetic model is considered complete but
> remains under review and may change before the final release. Peer review of
> the associated work has not been completed.

C3MechV4.2.0 incorporates the optimized NH3/H2/NOx chemistry of
Girhe et al. [1]. Rate parameters for 70 reactions were optimized using
elementary rate coefficient data from 141 publications and 11,273 global
combustion measurements from 113 publications. When using an NH3 submodule,
cite Girhe et al. [1] in addition to the other citations required for
C3MechV4.2.0.

The optimization of the NH3/H2/NOx chemistry is part of the following work:

1. Girhe, S., Langer, R., Loffredo, F.,
   Pitsch, H. (2026). Ammonia combustion kinetic model optimization using
   elementary rate coefficient and global combustion data. Manuscript in
   preparation for submission to *Combustion and Flame*.

This third release candidate applies the optimized ammonia chemistry described
above to the C3MechV4.0.1 baseline. The C1/C2 and carbon-nitrogen chemistry
updates included in the earlier V4.2.0 release candidates have been reverted
to the C3MechV4.0.1 baseline.

Reviewed corrections across the repository are retained, including
thermochemistry temperature-range extensions and repairs to incomplete
reaction pathways. These include the replacement of inconsistent RFLUORENE
pathways with the existing `0.5C12H9 + 0.5C14H9` treatment.

Species-definition inconsistencies involving HNO2, H2NCHO, H2NCO and HNO3 have
been corrected. Nitric acid is now represented consistently as HONO2, and the
duplicate HNO3 entry has been removed.
The original singlet CH2OO data are retained under the explicit label `CH2OO(S)`.

The OH* subset based on [Kathrotia et al. (2010)](https://doi.org/10.1016/j.combustflame.2010.04.003),
as used in the adopted ammonia chemistry, replaces the previous
[Hall and Petersen (2006)](https://doi.org/10.1002/kin.20196) subset. The adopted
subset includes the ammonia model's nitrogen-species reactions and retains
C3Mech's CH + O2 formation channel and quenching by CO2, CO and CH4.

Source submodules now use `_IC.MECH` to identify the independent-collider
formulation. The paired `LOWMX/LOWSP` input is labelled for LMR-R (LMRR) or
LMR-P (LMRP), as selected by the solver. This naming update does not change
reaction parameters, thermochemistry or transport data.
