# Full C3MechV4.0.1 model

This directory provides the full C3MechV4.0.1 model in a format consistent
with the distribution on fuelmech.org.

The files are:

- C3MechV4.0.1.CKI   - kinetics file in CHEMKIN-format (MID 4HZZ)
- C3MechV4.0.1.THERM - thermochemistry data
- C3MechV4.0.1.TRAN  - transport data

These correspond to the C8+ sub-model with C5CY, C6CY, DMC+EC, nitrogen,
and PAH chemistry included (row with MID 3XR9/4HZZ in the C8+ table in
PRECOMPILED/README.md).

If you need a Cantera .yaml file for this model, go to [`PRECOMPILED/C8+/C0-C8+_C5CY_C6CY_DMC+EC_N_PAH/Cantera`](../PRECOMPILED/C8+/C0-C8+_C5CY_C6CY_DMC+EC_N_PAH/Cantera).
