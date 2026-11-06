# Generated model catalog

This directory contains generated chemical kinetic sub-models of
C3MechV4.2.0. Each sub-model contains a defined selection of the available
submodules.

## Quick start

- For typical cases, use the quick-access table below and follow its linked model identifier (MID).
- For another available submodule combination, use the detailed tables.

The full C3MechV4.2.0 model corresponds to the directory [`C8+/C0-C8+_C5CY_C6CY_DMC+EC_N_PAH/`](C8+/C0-C8+_C5CY_C6CY_DMC+EC_N_PAH/) with MID `4HZZ`.

## Terminology and background

The source reactions are grouped into submodules based on the number of carbon atoms and chemical scope. The `CY` label identifies non-aromatic cyclic fuel components. The `N` label includes the nitrogen and carbon-nitrogen submodules when carbon-containing chemistry is selected. The `PAH` label identifies polycyclic aromatic hydrocarbon chemistry.

Many sub-models are available as a high-temperature (HT) version and as a
combined low-temperature and high-temperature (LT-HT) version. The LT-HT
version is the reference for each submodule selection. The corresponding HT
version excludes the additional low-temperature chemistry where the versions
differ. The HT and LT-HT names describe the included chemistry. They indicate
the temperature regimes where that chemistry is typically relevant, but they
do not establish fixed applicability limits. The user must assess whether a
selected sub-model is appropriate for the intended simulation. When the
suitability of an HT version is uncertain, the corresponding LT-HT version
provides the reference.

`CHEMKIN NS(HT/LT-HT)` and `CHEMKIN NR(HT/LT-HT)` give the corresponding
numbers of species and reaction records in the
LOWMX/LOWSP files for LMR-R (LMRR) or LMR-P (LMRP), as selected by the solver.
The generated Cantera YAML files use native LMRR. The `LEGACY/` mechanism
file uses the independent-collider (IC) formulation for compatible older solvers.
Each version has a MID that identifies its exact submodule selection.

## Notes and recommendations

- Select only the submodules required for the simulation case to reduce computational cost.
- The user is responsible for selecting an appropriate sub-model.
- State the MID when documenting the use of a C3Mech sub-model.

For questions or suggestions, visit the [source repository](https://github.com/C3Mech/C3Mech) or contact [Luna Pratali Maffei](mailto:luna.pratali@polimi.it) or [Raymond Langer](mailto:r.langer@itv.rwth-aachen.de).

## Verify generated files

`MODEL_MANIFEST.json` records digest values calculated with the Secure Hash
Algorithm with a 256 bit output (SHA-256).
`c3mech_configuration_sha256` is calculated from the exact bytes of the
selected C3Mech configuration file. It identifies the selected configuration
associated with this inventory and used to render this catalog.

The manifest records two SHA-256 hashes for every generated file.
`sha256` verifies the exact file bytes, including the generation timestamp and
line endings. `normalized_sha256` replaces recognized compiler and
Cantera-converter timestamps with fixed values and converts CRLF line endings
to LF before hashing. Use `normalized_sha256` to compare model content
generated at different times or on different platforms.

## Available generated models

Every submodel directory contains the following files:

```text
<model>.CKI       # Main kinetics (LMRR)
<model>.THERM     # Thermochemistry
<model>.TRAN      # Transport
<model>.yaml      # Cantera model (LMRR)
LEGACY/
  <model>_IC.CKI
```

Here, `<model>` contains the model name, model identifier and temperature range where applicable. We recommend the [linear mixture rule in reduced pressure (LMRR)](https://doi.org/10.1016/j.proci.2016.06.068). For simulation software that reads mechanisms in CHEMKIN format but does not support LMRR, `LEGACY/` provides an independent-collider (IC) mechanism file. It uses the `.THERM` and `.TRAN` files in its parent directory. The Cantera YAML file uses native LMRR and requires Cantera 3.1 or later.

## Quick access table with commonly used sub-models

| Use case                       | Directory                    | MID(HT/LT-HT)                           | C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | CHEMKIN NS(HT/LT-HT) | CHEMKIN NR(HT/LT-HT) |
|:------------------------------:|:----------------------------:|:---------------------------------------:|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:--------------------:|:--------------------:|
| Hydrogen and ammonia           | `C0/C0_N/`                   | [2906/2906](C0/C0_N/)                   | ✓  |       |       |    |    |    |     |      |      |        | ✓ |     | 43/43                | 275/275              |
| Methane                        | `C1-C2/C0-C1-C2/`            | [3DI0/3DI0](C1-C2/C0-C1-C2/)            | ✓  | ✓     |       |    |    |    |     |      |      |        |   |     | 109/109              | 663/663              |
| C0 to C4 fuels                 | `C3-C4/C0-C3-C4/`            | [3R00/44I0](C3-C4/C0-C3-C4/)            | ✓  | ✓     | ✓     |    |    |    |     |      |      |        |   |     | 379/730              | 2521/3964            |
| Aromatic and cyclic fuels      | `C6/C0-C3-C4_C5CY_C6CY_PAH/` | [3SO1/47U1](C6/C0-C3-C4_C5CY_C6CY_PAH/) | ✓  | ✓     | ✓     |    |    |    |     | ✓    | ✓    |        |   | ✓   | 599/1052             | 5771/7561            |
| Cyclopentadiene                | `C6/C0-C5_C5CY_C6CY_PAH/`    | [3X61/4GU1](C6/C0-C5_C5CY_C6CY_PAH/)    | ✓  | ✓     | ✓     | ✓  |    |    |     | ✓    | ✓    |        |   | ✓   | 752/1549             | 6707/9520            |
| Toluene Primary Reference Fuel | `C8+/C0-C8+_C5CY_C6CY_PAH/`  | [3XQP/4HZD](C8+/C0-C8+_C5CY_C6CY_PAH/)  | ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   | ✓    | ✓    |        |   | ✓   | 1593/4917            | 10599/20709          |

- **Aromatic and cyclic fuels:** Includes benzene, toluene, phenol, indene, naphthalene, xylene, alpha-methylnaphthalene, C1 through CY5 species, and polycyclic aromatic hydrocarbons.

## Detailed tables

### [C0/](C0/)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | Directory  | CHEMKIN NS(HT/LT-HT) | CHEMKIN NR(HT/LT-HT) | MID(HT/LT-HT)         |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:----------:|:--------------------:|:--------------------:|:---------------------:|
| ✓  |       |       |    |    |    |     |      |      |        |   |     | `C0/C0/`   | 17/17                | 23/23                | [2900/2900](C0/C0/)   |
| ✓  |       |       |    |    |    |     |      |      |        | ✓ |     | `C0/C0_N/` | 43/43                | 275/275              | [2906/2906](C0/C0_N/) |

### [C1-C2/](C1-C2/)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | Directory                | CHEMKIN NS(HT/LT-HT) | CHEMKIN NR(HT/LT-HT) | MID(HT/LT-HT)                       |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------------------:|:--------------------:|:--------------------:|:-----------------------------------:|
| ✓  | ✓     |       |    |    |    |     |      |      |        |   |     | `C1-C2/C0-C1-C2/`        | 109/109              | 663/663              | [3DI0/3DI0](C1-C2/C0-C1-C2/)        |
| ✓  | ✓     |       |    |    |    |     |      |      | ✓      |   |     | `C1-C2/C0-C1-C2_DMC+EC/` | 116/116              | 701/701              | [3DIC/3DIC](C1-C2/C0-C1-C2_DMC+EC/) |
| ✓  | ✓     |       |    |    |    |     |      |      |        | ✓ |     | `C1-C2/C0-C1-C2_N/`      | 249/268              | 1637/1663            | [3DI8/3DIA](C1-C2/C0-C1-C2_N/)      |

### [C3-C4/](C3-C4/)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | Directory           | CHEMKIN NS(HT/LT-HT) | CHEMKIN NR(HT/LT-HT) | MID(HT/LT-HT)                  |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:-------------------:|:--------------------:|:--------------------:|:------------------------------:|
| ✓  | ✓     | ✓     |    |    |    |     |      |      |        |   |     | `C3-C4/C0-C3-C4/`   | 379/730              | 2521/3964            | [3R00/44I0](C3-C4/C0-C3-C4/)   |
| ✓  | ✓     | ✓     |    |    |    |     |      |      |        | ✓ |     | `C3-C4/C0-C3-C4_N/` | 498/866              | 3495/4964            | [3R08/44IA](C3-C4/C0-C3-C4_N/) |

### [C5/](C5/)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | Directory             | CHEMKIN NS(HT/LT-HT) | CHEMKIN NR(HT/LT-HT) | MID(HT/LT-HT)                    |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:---------------------:|:--------------------:|:--------------------:|:--------------------------------:|
| ✓  | ✓     | ✓     |    |    |    |     | ✓    |      |        |   |     | `C5/C0-C3-C4_C5CY/`   | 430/846              | 2674/4356            | [3SI0/47I0](C5/C0-C3-C4_C5CY/)   |
| ✓  | ✓     | ✓     |    |    |    |     | ✓    |      |        | ✓ |     | `C5/C0-C3-C4_C5CY_N/` | 548/981              | 3648/5356            | [3SI8/47IA](C5/C0-C3-C4_C5CY_N/) |
| ✓  | ✓     | ✓     | ✓  |    |    |     |      |      |        |   |     | `C5/C0-C5/`           | 551/1249             | 3457/5923            | [3VI0/4DI0](C5/C0-C5/)           |
| ✓  | ✓     | ✓     | ✓  |    |    |     | ✓    |      |        |   |     | `C5/C0-C5_C5CY/`      | 585/1345             | 3610/6315            | [3X00/4GI0](C5/C0-C5_C5CY/)      |
| ✓  | ✓     | ✓     | ✓  |    |    |     |      |      |        | ✓ |     | `C5/C0-C5_N/`         | 662/1374             | 4431/6923            | [3VI8/4DIA](C5/C0-C5_N/)         |
| ✓  | ✓     | ✓     | ✓  |    |    |     | ✓    |      |        | ✓ |     | `C5/C0-C5_C5CY_N/`    | 696/1470             | 4584/7315            | [3X08/4GIA](C5/C0-C5_C5CY_N/)    |

### [C6/](C6/)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | Directory                      | CHEMKIN NS(HT/LT-HT) | CHEMKIN NR(HT/LT-HT) | MID(HT/LT-HT)                             |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------------------------:|:--------------------:|:--------------------:|:-----------------------------------------:|
| ✓  | ✓     | ✓     |    |    |    |     | ✓    | ✓    |        |   |     | `C6/C0-C3-C4_C5CY_C6CY/`       | 462/915              | 2783/4573            | [3SO0/47U0](C6/C0-C3-C4_C5CY_C6CY/)       |
| ✓  | ✓     | ✓     |    |    |    |     | ✓    | ✓    |        | ✓ |     | `C6/C0-C3-C4_C5CY_C6CY_N/`     | 580/1050             | 3757/5573            | [3SO8/47UA](C6/C0-C3-C4_C5CY_C6CY_N/)     |
| ✓  | ✓     | ✓     |    |    |    |     | ✓    | ✓    |        |   | ✓   | `C6/C0-C3-C4_C5CY_C6CY_PAH/`   | 599/1052             | 5771/7561            | [3SO1/47U1](C6/C0-C3-C4_C5CY_C6CY_PAH/)   |
| ✓  | ✓     | ✓     | ✓  |    |    |     | ✓    | ✓    |        |   |     | `C6/C0-C5_C5CY_C6CY/`          | 616/1413             | 3719/6532            | [3X60/4GU0](C6/C0-C5_C5CY_C6CY/)          |
| ✓  | ✓     | ✓     |    |    |    |     | ✓    | ✓    |        | ✓ | ✓   | `C6/C0-C3-C4_C5CY_C6CY_N_PAH/` | 717/1187             | 6745/8561            | [3SO9/47UB](C6/C0-C3-C4_C5CY_C6CY_N_PAH/) |
| ✓  | ✓     | ✓     | ✓  |    |    |     | ✓    | ✓    |        | ✓ |     | `C6/C0-C5_C5CY_C6CY_N/`        | 727/1538             | 4693/7532            | [3X68/4GUA](C6/C0-C5_C5CY_C6CY_N/)        |
| ✓  | ✓     | ✓     | ✓  |    |    |     | ✓    | ✓    |        |   | ✓   | `C6/C0-C5_C5CY_C6CY_PAH/`      | 752/1549             | 6707/9520            | [3X61/4GU1](C6/C0-C5_C5CY_C6CY_PAH/)      |
| ✓  | ✓     | ✓     | ✓  | ✓  |    |     |      |      |        |   |     | `C6/C0-C6/`                    | 820/2301             | 4574/9409            | [3W00/4EI0](C6/C0-C6/)                    |
| ✓  | ✓     | ✓     | ✓  | ✓  |    |     | ✓    |      |        |   |     | `C6/C0-C6_C5CY/`               | 854/2397             | 4727/9801            | [3XI0/4HI0](C6/C0-C6_C5CY/)               |
| ✓  | ✓     | ✓     | ✓  |    |    |     | ✓    | ✓    |        | ✓ | ✓   | `C6/C0-C5_C5CY_C6CY_N_PAH/`    | 863/1674             | 7681/10520           | [3X69/4GUB](C6/C0-C5_C5CY_C6CY_N_PAH/)    |
| ✓  | ✓     | ✓     | ✓  | ✓  |    |     | ✓    | ✓    |        |   |     | `C6/C0-C6_C5CY_C6CY/`          | 882/2461             | 4836/10018           | [3XO0/4HU0](C6/C0-C6_C5CY_C6CY/)          |
| ✓  | ✓     | ✓     | ✓  | ✓  |    |     |      |      |        | ✓ |     | `C6/C0-C6_N/`                  | 926/2415             | 5548/10409           | [3W08/4EIA](C6/C0-C6_N/)                  |
| ✓  | ✓     | ✓     | ✓  | ✓  |    |     | ✓    |      |        | ✓ |     | `C6/C0-C6_C5CY_N/`             | 960/2511             | 5701/10801           | [3XI8/4HIA](C6/C0-C6_C5CY_N/)             |
| ✓  | ✓     | ✓     | ✓  | ✓  |    |     | ✓    | ✓    |        | ✓ |     | `C6/C0-C6_C5CY_C6CY_N/`        | 988/2575             | 5810/11018           | [3XO8/4HUA](C6/C0-C6_C5CY_C6CY_N/)        |
| ✓  | ✓     | ✓     | ✓  | ✓  |    |     | ✓    | ✓    |        |   | ✓   | `C6/C0-C6_C5CY_C6CY_PAH/`      | 1016/2595            | 7824/13006           | [3XO1/4HU1](C6/C0-C6_C5CY_C6CY_PAH/)      |
| ✓  | ✓     | ✓     | ✓  | ✓  |    |     | ✓    | ✓    |        | ✓ | ✓   | `C6/C0-C6_C5CY_C6CY_N_PAH/`    | 1122/2709            | 8798/14006           | [3XO9/4HUB](C6/C0-C6_C5CY_C6CY_N_PAH/)    |

### [C7/](C7/)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | Directory                   | CHEMKIN NS(HT/LT-HT) | CHEMKIN NR(HT/LT-HT) | MID(HT/LT-HT)                          |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:---------------------------:|:--------------------:|:--------------------:|:--------------------------------------:|
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  |     |      |      |        |   |     | `C7/C0-C7/`                 | 923/2743             | 4924/10779           | [3W20/4EM0](C7/C0-C7/)                 |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  |     | ✓    |      |        |   |     | `C7/C0-C7_C5CY/`            | 957/2839             | 5077/11171           | [3XK0/4HM0](C7/C0-C7_C5CY/)            |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  |     | ✓    | ✓    |        |   |     | `C7/C0-C7_C5CY_C6CY/`       | 984/2902             | 5186/11388           | [3XQ0/4HY0](C7/C0-C7_C5CY_C6CY/)       |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  |     |      |      |        | ✓ |     | `C7/C0-C7_N/`               | 1024/2844            | 5898/11779           | [3W28/4EMA](C7/C0-C7_N/)               |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  |     | ✓    |      |        | ✓ |     | `C7/C0-C7_C5CY_N/`          | 1058/2940            | 6051/12171           | [3XK8/4HMA](C7/C0-C7_C5CY_N/)          |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  |     | ✓    | ✓    |        | ✓ |     | `C7/C0-C7_C5CY_C6CY_N/`     | 1085/3003            | 6160/12388           | [3XQ8/4HYA](C7/C0-C7_C5CY_C6CY_N/)     |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  |     | ✓    | ✓    |        |   | ✓   | `C7/C0-C7_C5CY_C6CY_PAH/`   | 1118/3036            | 8174/14376           | [3XQ1/4HY1](C7/C0-C7_C5CY_C6CY_PAH/)   |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  |     | ✓    | ✓    |        | ✓ | ✓   | `C7/C0-C7_C5CY_C6CY_N_PAH/` | 1219/3137            | 9148/15376           | [3XQ9/4HYB](C7/C0-C7_C5CY_C6CY_N_PAH/) |

### [C8+/](C8+/)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | Directory                            | CHEMKIN NS(HT/LT-HT) | CHEMKIN NR(HT/LT-HT) | MID(HT/LT-HT)                                   |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------------------------------:|:--------------------:|:--------------------:|:-----------------------------------------------:|
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   |      |      |        |   |     | `C8+/C0-C8+/`                        | 1400/4626            | 7349/17112           | [3W2O/4ENC](C8+/C0-C8+/)                        |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   |      |      | ✓      |   |     | `C8+/C0-C8+_DMC+EC/`                 | 1406/4632            | 7387/17150           | [3W30/4ENO](C8+/C0-C8+_DMC+EC/)                 |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   | ✓    |      |        |   |     | `C8+/C0-C8+_C5CY/`                   | 1434/4722            | 7502/17504           | [3XKO/4HNC](C8+/C0-C8+_C5CY/)                   |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   | ✓    |      | ✓      |   |     | `C8+/C0-C8+_C5CY_DMC+EC/`            | 1440/4728            | 7540/17542           | [3XL0/4HNO](C8+/C0-C8+_C5CY_DMC+EC/)            |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   | ✓    | ✓    |        |   |     | `C8+/C0-C8+_C5CY_C6CY/`              | 1461/4785            | 7611/17721           | [3XQO/4HZC](C8+/C0-C8+_C5CY_C6CY/)              |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   | ✓    | ✓    | ✓      |   |     | `C8+/C0-C8+_C5CY_C6CY_DMC+EC/`       | 1467/4791            | 7649/17759           | [3XR0/4HZO](C8+/C0-C8+_C5CY_C6CY_DMC+EC/)       |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   |      |      |        | ✓ |     | `C8+/C0-C8+_N/`                      | 1501/4727            | 8323/18112           | [3W2W/4ENM](C8+/C0-C8+_N/)                      |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   |      |      | ✓      | ✓ |     | `C8+/C0-C8+_DMC+EC_N/`               | 1507/4733            | 8361/18150           | [3W38/4ENY](C8+/C0-C8+_DMC+EC_N/)               |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   | ✓    |      |        | ✓ |     | `C8+/C0-C8+_C5CY_N/`                 | 1535/4823            | 8476/18504           | [3XKW/4HNM](C8+/C0-C8+_C5CY_N/)                 |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   | ✓    |      | ✓      | ✓ |     | `C8+/C0-C8+_C5CY_DMC+EC_N/`          | 1541/4829            | 8514/18542           | [3XL8/4HNY](C8+/C0-C8+_C5CY_DMC+EC_N/)          |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   | ✓    | ✓    |        | ✓ |     | `C8+/C0-C8+_C5CY_C6CY_N/`            | 1562/4886            | 8585/18721           | [3XQW/4HZM](C8+/C0-C8+_C5CY_C6CY_N/)            |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   | ✓    | ✓    | ✓      | ✓ |     | `C8+/C0-C8+_C5CY_C6CY_DMC+EC_N/`     | 1568/4892            | 8623/18759           | [3XR8/4HZY](C8+/C0-C8+_C5CY_C6CY_DMC+EC_N/)     |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   | ✓    | ✓    |        |   | ✓   | `C8+/C0-C8+_C5CY_C6CY_PAH/`          | 1593/4917            | 10599/20709          | [3XQP/4HZD](C8+/C0-C8+_C5CY_C6CY_PAH/)          |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   | ✓    | ✓    | ✓      |   | ✓   | `C8+/C0-C8+_C5CY_C6CY_DMC+EC_PAH/`   | 1599/4923            | 10637/20747          | [3XR1/4HZP](C8+/C0-C8+_C5CY_C6CY_DMC+EC_PAH/)   |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   | ✓    | ✓    |        | ✓ | ✓   | `C8+/C0-C8+_C5CY_C6CY_N_PAH/`        | 1694/5018            | 11573/21709          | [3XQX/4HZN](C8+/C0-C8+_C5CY_C6CY_N_PAH/)        |
| ✓  | ✓     | ✓     | ✓  | ✓  | ✓  | ✓   | ✓    | ✓    | ✓      | ✓ | ✓   | `C8+/C0-C8+_C5CY_C6CY_DMC+EC_N_PAH/` | 1700/5024            | 11611/21747          | [3XR9/4HZZ](C8+/C0-C8+_C5CY_C6CY_DMC+EC_N_PAH/) |
