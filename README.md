# C3MechV4.0.1
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

**C3MechV4.0.1** is a universal chemical kinetic model developed for both conventional and renewable fuels (e.g., alkanes, hydrogen, ammonia, dimethyl ether, dimethyl carbonate/ethylene carbonate). It has been validated for a wide range of conditions and uses a hierarchical structure that allows the targeted compilation of sub-models. This repository is linked to the publication ["Modeling Combustion Chemistry using C3MechV4.0: an extension to mixtures of hydrogen, ammonia, alkanes, and cycloalkanes"](https://doi.org/10.1016/j.jaecs.2025.100385) and its ["forthcoming Corrigendum"](link-to-be-added-upon-publication).

## 0. Full model

If you only need the full C3MechV4.0.1 model in CHEMKIN format, use [`FULL_MODEL/`](FULL_MODEL/).

## 1. Quick start: ready-to-use sub-models

For most applications, you can use a **precompiled sub-model**:

1. Go to [`PRECOMPILED/`](PRECOMPILED/).
2. Open `PRECOMPILED/README.md`.
3. In the **"Quick access table with commonly used sub-models"**, find the row
   that best matches your case (e.g., cyclopentadiene).
4. In that row, look at the `MID(HT/LT-HT)` column. It shows two MIDs,
   `MID_HT/MID_LT-HT`:
   - The first MID is the **HT** version (model with only high-temperature
     chemistry).
   - The second MID is the **LT-HT** version (model that additionally includes
     low-temperature chemistry).

   The entry in this column is also a link. Clicking it opens the directory
   for that model (for example, `C6/C0-C5_C5CY_C6CY_PAH/` for cyclopentadiene).

Then:

- **CHEMKIN**  
  In the directory opened by the MID link, go to `Chemkin/` and use the
  `.CKI`, `.THERM`, and `.TRAN` files whose names start with  
  `C3MechV4.0.1_<MID>_`.

- **Cantera**  
  In the same directory, go to `Cantera/` and use the `.yaml` file whose name
  starts with `C3MechV4.0.1_<MID>_`.

If the table lists the same MID for HT and LT-HT, there is only a single version, and the same files are used across the entire temperature range. We recommend citing the MID when using a sub-model of C3MechV4.0.1.

## 2. Advanced use and model development

For most applications, the instructions above and the files under `PRECOMPILED/` are all you need. The remaining parts of this repository are mainly relevant if you have **specific requirements for which sub-modules are combined into a model** or if you are involved in **model development**.

The full repository additionally provides the following components, which are described in more detail below:

- All sub-modules maintained by the C3 consortium in `CHEMKIN` format 
- A species directory (CSV & PDF), along with a Python script for checking species data and converting them from CSV format to a PDF  
- A compiler script to generate CHEMKIN files from user-selected sub-modules  
- Several other precompiled sub-models (in CHEMKIN and Cantera YAML format) for direct use

## 3. Repository contents

1. **[`FULL_MODEL`](FULL_MODEL/)**  
   Directory with the full C3MechV4.0.1 model (MID 4HZZ) in a simplified naming scheme consistent with the distribution on fuelmech.org. Contains `C3MechV4.0.1.CKI`, `C3MechV4.0.1.THERM`, and `C3MechV4.0.1.TRAN` in CHEMKIN format; no YAML file is provided here.

2. **[`PRECOMPILED`](PRECOMPILED/)**  
This directory contains frequently used sub-models that have already been compiled in CHEMKIN and Cantera YAML formats. They can be used directly without the additional compilation step and are provided for convenience.  
   *Recommended starting point for most users.*

3. **[`SUBMODULES`](SUBMODULES/)**  
This directory contains sub-modules with kinetic data organized by the research groups that developed them and the jointly used files `SOURCE-C3Mech.THERM` and `SOURCE-C3Mech.TRAN` that provide all thermochemistry and transport data for C3MechV4.0.1. These files are recommended as a starting point for model development based on C3MechV4.0.1.

4. **[`SPECIES_DICTIONARY`](SPECIES_DICTIONARY/)**  
This directory provides a CSV file with plain species data and a PDF generated from these, which serves as an overview. The Python script `make_species_dict.py` implements the C3Mech species model and checks constraints on the data in the CSV file. It can optionally generate LaTeX code and plots of species structures, which can then be compiled into a PDF. The script can also be adapted to manage species data in other chemical kinetic models. Refer to the `README.md` for more details on the species model, the data in the CSV file, and the script's usage. 

5. **[`COMPILER`](COMPILER/)**  
This directory includes the script `compile_c3mech.py` and instructions on creating CHEMKIN-format mechanisms from user-selected sub-modules. For details on usage, refer to `README.md`.

For questions or suggestions, please open an issue or reach out to [Luna Pratali Maffei](mailto:luna.pratali@polimi.it) or [Raymond Langer](mailto:r.langer@itv.rwth-aachen.de) directly.
