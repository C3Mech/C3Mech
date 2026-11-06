# Full C3MechV4.2.0 model

This directory provides the complete C3MechV4.2.0 model supplied with
[V4.2.0-rc.3](https://github.com/C3Mech/C3Mech/releases/tag/V4.2.0-rc.3).
Its model identifier is `4HZZ`, and it includes the combined low-temperature
and high-temperature chemistry. These files are identical to the corresponding
[precompiled model](../PRECOMPILED/C8+/C0-C8+_C5CY_C6CY_DMC+EC_N_PAH/).

- [C3MechV4.2.0_4HZZ_C0-C8+_C5CY_C6CY_DMC+EC_N_PAH_LT-HT.CKI](C3MechV4.2.0_4HZZ_C0-C8+_C5CY_C6CY_DMC+EC_N_PAH_LT-HT.CKI) is the main CHEMKIN mechanism.
- [C3MechV4.2.0_4HZZ_C0-C8+_C5CY_C6CY_DMC+EC_N_PAH_LT-HT.THERM](C3MechV4.2.0_4HZZ_C0-C8+_C5CY_C6CY_DMC+EC_N_PAH_LT-HT.THERM) contains the thermochemistry.
- [C3MechV4.2.0_4HZZ_C0-C8+_C5CY_C6CY_DMC+EC_N_PAH_LT-HT.TRAN](C3MechV4.2.0_4HZZ_C0-C8+_C5CY_C6CY_DMC+EC_N_PAH_LT-HT.TRAN) contains the transport data.
- [C3MechV4.2.0_4HZZ_C0-C8+_C5CY_C6CY_DMC+EC_N_PAH_LT-HT.yaml](C3MechV4.2.0_4HZZ_C0-C8+_C5CY_C6CY_DMC+EC_N_PAH_LT-HT.yaml) is the Cantera model.
- [LEGACY/C3MechV4.2.0_4HZZ_C0-C8+_C5CY_C6CY_DMC+EC_N_PAH_LT-HT_IC.CKI](LEGACY/C3MechV4.2.0_4HZZ_C0-C8+_C5CY_C6CY_DMC+EC_N_PAH_LT-HT_IC.CKI) is the independent-collider (IC) mechanism file.

We recommend the linear mixture rule in reduced pressure (LMRR). The Cantera
model uses LMRR and requires Cantera 3.1 or later. For simulation software that
reads mechanisms in CHEMKIN format but does not support LMRR, use the IC file
in `LEGACY/` with the thermochemistry and transport files above.
