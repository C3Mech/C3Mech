# Precompiled models 

This directory contains precompiled chemical kinetic sub-models of C3MechV4.0.1, tailored to specific fuel compositions and conditions, and the full version of C3MechV4.0.1.

## Quick start in this directory

- For typical/simple cases, use the **Quick access table with commonly used sub-models** below:  
  Pick the row that matches your case (e.g., cyclopentadiene), use the entry in `MID(HT/LT-HT)` (HT or LT-HT), which links to the corresponding directory, and then locate the CHEMKIN and Cantera files as described in **Available precompiled models**.
- If you need a sub-model that is not listed in the Quick access table (for example, with a different choice of N, PAH, or CY sub-modules), ignore the Quick access table and use the detailed tables in the `C0/`, `C1-C2/`, ..., `C8+/` sections below.
- If there is **no precompiled sub-model** with the combination of sub-modules you require, use the compiler in [`../COMPILER/`](../COMPILER/) to generate a custom sub-model.

The full C3MechV4.0.1 model corresponds to the directory `C8+/C0-C8+_C5CY_C6CY_DMC+EC_N_PAH/` with MID `4HZZ`, also available in [`../FULL_MODEL/`](../FULL_MODEL/).

## Terminology and background

The sub-models were compiled from the sub-modules in the directory [`SUBMODULES/`](../SUBMODULES/). The reactions in the sub-modules are grouped based on the number of carbon atoms in the species (C0, C1-C2, C3-C4, C5, C6, C7, C8+, C5CY, C6CY), with aromatic species being managed separately. Here, 'CY' refers to non-aromatic, cyclic fuel components. Additionally, sub-modules for dimethyl carbonate and ethylene carbonate (DMC+EC), nitrogen-containing species (N), cross-reactions between nitrogen- and carbon-containing species (C-N), and polycyclic aromatic hydrocarbons (PAH) are available. The tables below list all precompiled sub-models, where in this subdirectory "N" refers to the combined N- and C-N sub-modules if a sub-model contains carbon atoms. 

Many sub-models are available as smaller high-temperature (HT) versions, which are suitable for simulations of unstretched premixed and counterflow flames, high-temperature flow reactors, and shock tubes. Low-temperature (LT) chemistry is, for example, required to simulate jet-stirred reactors, flow reactors under lower-temperature conditions, and rapid compression machine (RCM) experiments. The columns NS(HT/LT-HT) and NR(HT/LT-HT) in the tables below refer to the number of species and reactions in the respective sub-models. 

Each HT and LT-HT version is assigned a unique model ID (MID(HT/LT-HT)) that encodes the specific sub-module combination; if a single model is used across all temperatures, the counts (NS and NR) and MIDs are the same. If you need a combination not listed here, see [`COMPILER/`](../COMPILER/) directory for an easy-to-use script to create custom sub-models.

## Notes and recommendations 

- **Selecting a sub-model:** Selecting a sub-model with only the necessary sub-modules facilitates and speeds up kinetic simulations. 
- **User responsibility:** The user must select an _appropriate_ sub-model for a simulation case. 

For questions or suggestions, please open an issue or [contact us](mailto:r.langer@itv.rwth-aachen.de). 

## Available precompiled models

You can download individual files or clone all files. For each sub-model, there are CHEMKIN (.CKI, .THERM, .TRAN) and Cantera (.yaml) files. The layout is the same in every sub-model directory under the carbon-group directories
(`C0/`, `C1-C2/`, `C3-C4/`, `C5/`, `C6/`, `C7/`, `C8+/`), for example
`C6/C0-C5_C5CY_C6CY_PAH/`:

- `Chemkin/`:
  - mechanism files `C3MechV4.0.1_*.CKI` (CHEMKIN‑PRO/OpenSMOKE++)
  - corresponding thermodynamic and transport data files `C3MechV4.0.1_*.THERM`
    and `C3MechV4.0.1_*.TRAN`
- `Cantera/`:
  - Cantera/FlameMaster-compatible mechanism files `C3MechV4.0.1_*_Cantera.CKI`
  - Cantera `.yaml` files

The thermodynamic (`*.THERM`) and transport (`*.TRAN`) files are **identical** for both `*.CKI` variants and are therefore stored only once in `Chemkin/`. The `.CKI` files are provided as CHEMKIN-PRO/OpenSMOKE++‑compatible versions and as Cantera/FlameMaster‑compatible versions (filenames containing `Cantera`).

Once you have chosen a sub-model in one of the tables below (for example, from the **Quick access table**), use its `MID(HT/LT‑HT)` entry (and the link to the corresponding directory) to locate the CHEMKIN and Cantera files. We recommend citing the `MID` when using a sub-model of C3MechV4.0.1.

## Quick access table with commonly used sub-models

Use this table for typical/simple cases:

- Pick the row that matches your case (e.g., cyclopentadiene).
- Use the desired MID from `MID(HT/LT-HT)` (HT or LT-HT); each MID entry links to the directory for that sub-model.
- In that directory, locate the CHEMKIN and Cantera files as described in **Available precompiled models** above.

If you need a configuration that is not listed here (e.g. different selection of N, PAH, or CY sub-modules), ignore this table and use the detailed tables in the `C0/`, `C1-C2/`, ..., `C8+/` sections below.

| Fuels                      | MID(HT/LT-HT)                           | C0 | C1-C2 | C3-C4 | C5 | C6-C8+ | C5CY | C6CY | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) |
|:--------------------------:|:---------------------------------------:|:--:|:-----:|:-----:|:--:|:------:|:----:|:----:|:-:|:---:|:------------:|:------------:|
| Hydrogen and ammonia       | [2906/2906](C0/C0_N/)                   | ✓  |       |       |    |        |      |      | ✓ |     |    43/43     |   273/273    |
| Methane                    | [3DI0/3DI0](C1-C2/C0-C1-C2/)            | ✓  |   ✓   |       |    |        |      |      |   |     |   101/101    |   658/658    |
| C0–C4 fuels                | [3R00/44I0](C3-C4/C0-C3-C4/)            | ✓  |   ✓   |   ✓   |    |        |      |      |   |     |   372/723    |  2510/3952   |
| Aromatic and cyclic fuels* | [3SO1/47U1](C6/C0-C3-C4_C5CY_C6CY_PAH/) | ✓  |   ✓   |   ✓   |    |        |  ✓   |  ✓   |   |  ✓  |   597/1048   |  5833/7623   |
| Cyclopentadiene            | [3X61/4GU1](C6/C0-C5_C5CY_C6CY_PAH/)    | ✓  |   ✓   |   ✓   | ✓  |        |  ✓   |  ✓   |   |  ✓  |   735/1546   |  6728/9582   |
| TPRF**                     | [3XQP/4HZD](C8+/C0-C8+_C5CY_C6CY_PAH/)  | ✓  |   ✓   |   ✓   | ✓  |   ✓    |  ✓   |  ✓   |   |  ✓  |  1489/4874   | 10480/20617  |

**\*Aromatic and cyclic fuels**: Benzene, toluene, phenol, indene, naphthalene, xylene, alpha-methylnaphthalene, C1–CY5 with PAHs

**\*\*TPRF**: Toluene Primary Reference Fuel


###  [C0/](C0/) (Number of carbon atoms: 0)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT)         |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:---------------------:|
| ✓  |       |       |    |    |    |     |      |      |        |   |     |    16/16     |    23/23     | [2900/2900](C0/C0/)   |
| ✓  |       |       |    |    |    |     |      |      |        | ✓ |     |    43/43     |   273/273    | [2906/2906](C0/C0_N/) |

###  [C1-C2/](C1-C2/) (Number of carbon atoms: 1–2)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT)                       |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:-----------------------------------:|
| ✓  |   ✓   |       |    |    |    |     |      |      |        |   |     |   101/101    |   658/658    | [3DI0/3DI0](C1-C2/C0-C1-C2/)        |
| ✓  |   ✓   |       |    |    |    |     |      |      |   ✓    |   |     |   108/108    |   696/696    | [3DIC/3DIC](C1-C2/C0-C1-C2_DMC+EC/) |
| ✓  |   ✓   |       |    |    |    |     |      |      |        | ✓ |     |   249/268    |  1634/1660   | [3DI8/3DIA](C1-C2/C0-C1-C2_N/)      |

###  [C3-C4/](C3-C4/) (Number of carbon atoms: 3–4)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT)                  |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:------------------------------:|
| ✓  |   ✓   |   ✓   |    |    |    |     |      |      |        |   |     |   372/723    |  2510/3952   | [3R00/44I0](C3-C4/C0-C3-C4/)   |
| ✓  |   ✓   |   ✓   |    |    |    |     |      |      |        | ✓ |     |   493/861    |  3482/4950   | [3R08/44IA](C3-C4/C0-C3-C4_N/) |

###  [C5/](C5/) (Number of carbon atoms: 5)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT)                    |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:--------------------------------:|
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |      |        |   |     |   424/841    |  2669/4352   | [3SI0/47I0](C5/C0-C3-C4_C5CY/)   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |      |      |        |   |     |   531/1245   |  3412/5919   | [3VI0/4DI0](C5/C0-C5/)           |
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |      |        | ✓ |     |   544/978    |  3641/5350   | [3SI8/47IA](C5/C0-C3-C4_C5CY_N/) |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |      |        |   |     |   564/1341   |  3564/6311   | [3X00/4GI0](C5/C0-C5_C5CY/)      |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |      |      |        | ✓ |     |   644/1372   |  4384/6917   | [3VI8/4DIA](C5/C0-C5_N/)         |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |      |        | ✓ |     |   677/1468   |  4536/7309   | [3X08/4GIA](C5/C0-C5_C5CY_N/)    |

###  [C6/](C6/) (Number of carbon atoms: 6)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT)                             |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:-----------------------------------------:|
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |  ✓   |        |   |     |   456/907    |  2776/4566   | [3SO0/47U0](C6/C0-C3-C4_C5CY_C6CY/)       |
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |  ✓   |        | ✓ |     |   576/1044   |  3748/5564   | [3SO8/47UA](C6/C0-C3-C4_C5CY_C6CY_N/)     |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |  ✓   |        |   |     |   595/1406   |  3671/6525   | [3X60/4GU0](C6/C0-C5_C5CY_C6CY/)          |
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |  ✓   |        |   |  ✓  |   597/1048   |  5833/7623   | [3SO1/47U1](C6/C0-C3-C4_C5CY_C6CY_PAH/)   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |  ✓   |        | ✓ |     |   708/1533   |  4643/7523   | [3X68/4GUA](C6/C0-C5_C5CY_C6CY_N/)        |
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |  ✓   |        | ✓ |  ✓  |   717/1185   |  6805/8621   | [3SO9/47UB](C6/C0-C3-C4_C5CY_C6CY_N_PAH/) |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |  ✓   |        |   |  ✓  |   735/1546   |  6728/9582   | [3X61/4GU1](C6/C0-C5_C5CY_C6CY_PAH/)      |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |      |      |        |   |     |   783/2297   |  4509/9402   | [3W00/4EI0](C6/C0-C6/)                    |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |      |        |   |     |   816/2393   |  4661/9794   | [3XI0/4HI0](C6/C0-C6_C5CY/)               |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |  ✓   |        |   |     |   844/2454   |  4768/10008  | [3XO0/4HU0](C6/C0-C6_C5CY_C6CY/)          |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |  ✓   |        | ✓ |  ✓  |   848/1673   |  7700/10580  | [3X69/4GUB](C6/C0-C5_C5CY_C6CY_N_PAH/)    |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |      |      |        | ✓ |     |   891/2413   |  5481/10400  | [3W08/4EIA](C6/C0-C6_N/)                  |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |      |        | ✓ |     |   924/2509   |  5633/10792  | [3XI8/4HIA](C6/C0-C6_C5CY_N/)             |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |  ✓   |        | ✓ |     |   952/2570   |  5740/11006  | [3XO8/4HUA](C6/C0-C6_C5CY_C6CY_N/)        |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |  ✓   |        |   |  ✓  |   983/2593   |  7827/13067  | [3XO1/4HU1](C6/C0-C6_C5CY_C6CY_PAH/)      |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |  ✓   |        | ✓ |  ✓  |  1091/2709   |  8799/14065  | [3XO9/4HUB](C6/C0-C6_C5CY_C6CY_N_PAH/)    |

###  [C7/](C7/) (Number of carbon atoms: 7)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT)                          |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:--------------------------------------:|
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |      |      |        |   |     |   867/2731   |  4840/10749  | [3W20/4EM0](C7/C0-C7/)                 |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |      |        |   |     |   900/2827   |  4992/11141  | [3XK0/4HM0](C7/C0-C7_C5CY/)            |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |  ✓   |        |   |     |   927/2887   |  5099/11355  | [3XQ0/4HY0](C7/C0-C7_C5CY_C6CY/)       |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |      |      |        | ✓ |     |   970/2834   |  5812/11747  | [3W28/4EMA](C7/C0-C7_N/)               |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |      |        | ✓ |     |  1003/2930   |  5964/12139  | [3XK8/4HMA](C7/C0-C7_C5CY_N/)          |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |  ✓   |        | ✓ |     |  1030/2990   |  6071/12353  | [3XQ8/4HYA](C7/C0-C7_C5CY_C6CY_N/)     |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |  ✓   |        |   |  ✓  |  1066/3026   |  8158/14414  | [3XQ1/4HY1](C7/C0-C7_C5CY_C6CY_PAH/)   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |  ✓   |        | ✓ |  ✓  |  1169/3129   |  9130/15412  | [3XQ9/4HYB](C7/C0-C7_C5CY_C6CY_N_PAH/) |

###  [C8+/](C8+/) (Number of carbon atoms: 8+)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT)                                   |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:-----------------------------------------------:|
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |      |      |        |   |     |  1290/4579   |  7145/16935  | [3W2O/4ENC](C8+/C0-C8+/)                        |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |      |      |   ✓    |   |     |  1296/4585   |  7183/16973  | [3W30/4ENO](C8+/C0-C8+_DMC+EC/)                 |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |      |        |   |     |  1323/4675   |  7297/17327  | [3XKO/4HNC](C8+/C0-C8+_C5CY/)                   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |      |   ✓    |   |     |  1329/4681   |  7335/17365  | [3XL0/4HNO](C8+/C0-C8+_C5CY_DMC+EC/)            |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |        |   |     |  1350/4735   |  7404/17541  | [3XQO/4HZC](C8+/C0-C8+_C5CY_C6CY/)              |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |   ✓    |   |     |  1356/4741   |  7442/17579  | [3XR0/4HZO](C8+/C0-C8+_C5CY_C6CY_DMC+EC/)       |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |      |      |        | ✓ |     |  1393/4682   |  8117/17933  | [3W2W/4ENM](C8+/C0-C8+_N/)                      |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |      |      |   ✓    | ✓ |     |  1399/4688   |  8155/17971  | [3W38/4ENY](C8+/C0-C8+_DMC+EC_N/)               |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |      |        | ✓ |     |  1426/4778   |  8269/18325  | [3XKW/4HNM](C8+/C0-C8+_C5CY_N/)                 |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |      |   ✓    | ✓ |     |  1432/4784   |  8307/18363  | [3XL8/4HNY](C8+/C0-C8+_C5CY_DMC+EC_N/)          |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |        | ✓ |     |  1453/4838   |  8376/18539  | [3XQW/4HZM](C8+/C0-C8+_C5CY_C6CY_N/)            |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |   ✓    | ✓ |     |  1459/4844   |  8414/18577  | [3XR8/4HZY](C8+/C0-C8+_C5CY_C6CY_DMC+EC_N/)     |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |        |   |  ✓  |  1489/4874   | 10480/20617  | [3XQP/4HZD](C8+/C0-C8+_C5CY_C6CY_PAH/)          |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |   ✓    |   |  ✓  |  1495/4880   | 10518/20655  | [3XR1/4HZP](C8+/C0-C8+_C5CY_C6CY_DMC+EC_PAH/)   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |        | ✓ |  ✓  |  1592/4977   | 11452/21615  | [3XQX/4HZN](C8+/C0-C8+_C5CY_C6CY_N_PAH/)        |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |   ✓    | ✓ |  ✓  |  1598/4983   | 11490/21653  | [3XR9/4HZZ](C8+/C0-C8+_C5CY_C6CY_DMC+EC_N_PAH/) |
