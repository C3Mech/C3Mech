# Precompiled models 

This directory contains precompiled chemical kinetic sub-models of C3MechV4.0.1, tailored to specific fuel compositions and conditions, and the full version of C3MechV4.0.1.

## Quick start in this directory

- For typical/simple cases, use the **Quick access table with commonly used sub-models** below:  
  Pick the row that matches your case (e.g., cyclopentadiene), note its `Directory` and MID from `MID(HT/LT-HT)` (HT or LT-HT), and then locate the CHEMKIN and Cantera files as described in **Available precompiled models**.
- If you need a sub-model that is not listed in the Quick access table (for example, with a different choice of N, PAH, or CY sub-modules), ignore the Quick access table and use the detailed tables in the `C0/`, `C1-C2/`, ..., `C8+/` sections below.
- If there is **no precompiled sub-model** with the combination of sub-modules you require, use the compiler in [`../COMPILER/`](../COMPILER/) to generate a custom sub-model.

The full C3MechV4.0.1 model corresponds to directory `C8+/` and MID `4HZZ`.

## Terminology and background

The sub-models were compiled from the sub-modules in the directory [`SUBMODULES/`](../SUBMODULES/). The reactions in the sub-modules are grouped based on the number of carbon atoms in the species (C0, C1-C2, C3-C4, C5, C6, C7, C8+, C5CY, C6CY), with aromatic species being managed separately. Here, 'CY' refers to non-aromatic, cyclic fuel components. Additionally, sub-modules for dimethyl carbonate and ethylene carbonate (DMC+EC), nitrogen-containing species (N), cross-reactions between nitrogen- and carbon-containing species (C-N), and polycyclic aromatic hydrocarbons (PAH) are available. The tables below list all precompiled sub-models, where in this subdirectory "N" refers to the combined N- and C-N sub-modules if a sub-model contains carbon atoms. 

Many sub-models are available as smaller high-temperature (HT) versions, which are suitable for simulations of unstretched premixed and counterflow flames, high-temperature flow reactors, and shock tubes. Low-temperature (LT) chemistry is, for example, required to simulate jet-stirred reactors, flow reactors under lower-temperature conditions, and rapid compression machine (RCM) experiments. The columns NS(HT/LT-HT) and NR(HT/LT-HT) in the tables below refer to the number of species and reactions in the respective sub-models. 

Each HT and LT-HT version is assigned a unique model ID (MID(HT/LT-HT)) that encodes the specific sub-module combination; if a single model is used across all temperatures, the counts (NS and NR) and MIDs are the same. If you need a combination not listed here, see [`COMPILER/`](../COMPILER/) directory for an easy-to-use script to create custom sub-models.

## Notes and recommendations 

- **Selecting a sub-model:** Selecting a sub-model with only the necessary sub-modules facilitates and speeds up kinetic simulations. 
- **User responsibility:** The user must select an _appropriate_ sub-model for a simulation case. 

For questions or suggestions, please open an issue or [contact us](mailto:r.langer@itv.rwth-aachen.de). 

## Available precompiled models

You can download individual files or clone all files. For each sub-model, there are CHEMKIN (.CKI, .THERM, .TRAN) and Cantera (.yaml) files, organized identically in all directories (`C0/`, `C1–C2/`, `C3–C4/`, `C5/`, `C6/`, `C7/`, `C8+/`):

- `Chemkin/`:
  - mechanism files `C3MechV4.0.1_*.CKI` (CHEMKIN‑PRO/OpenSMOKE++)
  - corresponding thermodynamic and transport files `C3MechV4.0.1_*.THERM` and `C3MechV4.0.1_*.TRAN`
- `Cantera/`:
  - Cantera/FlameMaster-compatible mechanism files `C3MechV4.0.1_*_Cantera.CKI`
  - Cantera `.yaml` files

The thermodynamic (`*.THERM`) and transport (`*.TRAN`) files are **identical** for both `*.CKI` variants and are therefore stored only once in `Chemkin/`. The `.CKI` files are provided as CHEMKIN‑PRO/OpenSMOKE++‑compatible versions and as Cantera/FlameMaster‑compatible versions (filenames containing `Cantera`).

Once you have chosen a sub-model in one of the tables below (for example, from the **Quick access table**), use its `Directory` and `MID(HT/LT‑HT)` together with the layout above to locate the corresponding CHEMKIN and Cantera files. We recommend citing the `MID` when using a sub-model of C3MechV4.0.1.

## Quick access table with commonly used sub-models

Use this table for typical/simple cases:

- Pick the row that matches your case (e.g., cyclopentadiene).
- Note the `Directory` and the desired MID from `MID(HT/LT-HT)` (HT or LT-HT).
- Use that `Directory` and MID to locate the CHEMKIN and Cantera files as described in **Available precompiled models** above.

The full C3MechV4.0.1 model corresponds to directory `C8+/` and MID `4HZZ`.

If you need a configuration that is not listed here (e.g. different selection of N, PAH, or CY sub-modules), ignore this table and use the detailed tables in the `C0/`, `C1-C2/`, ..., `C8+/` sections below.

| Fuels                      | Directory      | MID(HT/LT-HT) | C0 | C1-C2 | C3-C4 | C5 | C6-C8+ | C5CY | C6CY | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) |
|:--------------------------:|:--------------:|:-------------:|:--:|:-----:|:-----:|:--:|:------:|:----:|:----:|:-:|:---:|:------------:|:------------:|
| Hydrogen and ammonia       |[C0/](C0/)      |   2906/2906   | ✓  |       |       |    |        |      |      | ✓ |     |    43/43     |   273/273    |
| Methane                    |[C1-C2/](C1-C2/)|   3DI0/3DI0   | ✓  |   ✓   |       |    |        |      |      |   |     |   101/101    |   658/658    |
| C0-C4 fuels                |[C3-C4/](C3-C4/)|   3R00/44I0   | ✓  |   ✓   |   ✓   |    |        |      |      |   |     |   374/723    |  2512/3952   |
| Aromatic and cyclic fuels\*|[C6/](C6/)      |   3SO1/47U1   | ✓  |   ✓   |   ✓   |    |        |  ✓   |  ✓   |   |  ✓  |   597/1048   |  5835/7623   |
| Cyclopentadiene            |[C6/](C6/)      |   3X61/4GU1   | ✓  |   ✓   |   ✓   | ✓  |        |  ✓   |  ✓   |   |  ✓  |   746/1546   |  6738/9582   |
| TPRF\*\*                   |[C8+/](C8+/)    |   3XQP/4HZD   | ✓  |   ✓   |   ✓   | ✓  |   ✓    |  ✓   |  ✓   |   |  ✓  |  1495/4874   | 10247/20617  |

**\*Aromatic and cyclic fuels**: Benzene, toluene, phenol, indene, naphthalene, xylene, alpha-methylnaphthalene, C1–CY5 with PAHs

**\*\*TPRF**: Toluene Primary Reference Fuel

###  [C0/](C0/) (Number of carbon atoms: 0)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT) |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:-------------:|
| ✓  |       |       |    |    |    |     |      |      |        |   |     |    16/16     |    23/23     |   2900/2900   |
| ✓  |       |       |    |    |    |     |      |      |        | ✓ |     |    43/43     |   273/273    |   2906/2906   |

###  [C1-C2/](C1-C2/) (Number of carbon atoms: 1–2)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT) |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:-------------:|
| ✓  |   ✓   |       |    |    |    |     |      |      |        |   |     |   101/101    |   658/658    |   3DI0/3DI0   |
| ✓  |   ✓   |       |    |    |    |     |      |      |   ✓    |   |     |   108/108    |   696/696    |   3DIC/3DIC   |
| ✓  |   ✓   |       |    |    |    |     |      |      |        | ✓ |     |   249/268    |  1634/1660   |   3DI8/3DIA   |

###  [C3-C4/](C3-C4/) (Number of carbon atoms: 3–4)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT) |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:-------------:|
| ✓  |   ✓   |   ✓   |    |    |    |     |      |      |        |   |     |   374/723    |  2512/3952   |   3R00/44I0   |
| ✓  |   ✓   |   ✓   |    |    |    |     |      |      |        | ✓ |     |   495/861    |  3484/4950   |   3R08/44IA   |

###  [C5/](C5/) (Number of carbon atoms: 5)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT) |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:-------------:|
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |      |        |   |     |   426/841    |  2671/4352   |   3SI0/47I0   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |      |      |        |   |     |   544/1245   |  3422/5919   |   3VI0/4DI0   |
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |      |        | ✓ |     |   546/978    |  3643/5350   |   3SI8/47IA   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |      |        |   |     |   577/1341   |  3574/6311   |   3X00/4GI0   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |      |      |        | ✓ |     |   657/1372   |  4394/6917   |   3VI8/4DIA   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |      |        | ✓ |     |   690/1468   |  4546/7309   |   3X08/4GIA   |

###  [C6/](C6/) (Number of carbon atoms: 6)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT) |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:-------------:|
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |  ✓   |        |   |     |   456/907    |  2778/4566   |   3SO0/47U0   |
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |  ✓   |        | ✓ |     |   576/1044   |  3750/5564   |   3SO8/47UA   |
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |  ✓   |        |   |  ✓  |   597/1048   |  5835/7623   |   3SO1/47U1   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |  ✓   |        |   |     |   606/1406   |  3681/6525   |   3X60/4GU0   |
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |  ✓   |        | ✓ |  ✓  |   717/1185   |  6807/8621   |   3SO9/47UB   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |  ✓   |        | ✓ |     |   719/1533   |  4653/7523   |   3X68/4GUA   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |  ✓   |        |   |  ✓  |   746/1546   |  6738/9582   |   3X61/4GU1   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |      |      |        |   |     |   796/2297   |  4519/9402   |   3W00/4EI0   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |      |        |   |     |   829/2393   |  4671/9794   |   3XI0/4HI0   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |  ✓   |        |   |     |   855/2454   |  4778/10008  |   3XO0/4HU0   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |  ✓   |        | ✓ |  ✓  |   859/1673   |  7710/10580  |   3X69/4GUB   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |      |      |        | ✓ |     |   904/2413   |  5491/10400  |   3W08/4EIA   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |      |        | ✓ |     |   937/2509   |  5643/10792  |   3XI8/4HIA   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |  ✓   |        | ✓ |     |   963/2570   |  5750/11006  |   3XO8/4HUA   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |  ✓   |        |   |  ✓  |   994/2593   |  7837/13067  |   3XO1/4HU1   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |  ✓   |        | ✓ |  ✓  |  1102/2709   |  8809/14065  |   3XO9/4HUB   |

###  [C7/](C7/) (Number of carbon atoms: 7)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT) |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:-------------:|
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |      |      |        |   |     |   880/2731   |  4850/10749  |   3W20/4EM0   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |      |        |   |     |   913/2827   |  5002/11141  |   3XK0/4HM0   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |  ✓   |        |   |     |   938/2887   |  5109/11355  |   3XQ0/4HY0   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |      |      |        | ✓ |     |   983/2834   |  5822/11747  |   3W28/4EMA   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |      |        | ✓ |     |  1016/2930   |  5974/12139  |   3XK8/4HMA   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |  ✓   |        | ✓ |     |  1041/2990   |  6081/12353  |   3XQ8/4HYA   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |  ✓   |        |   |  ✓  |  1077/3026   |  8168/14414  |   3XQ1/4HY1   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |  ✓   |        | ✓ |  ✓  |  1180/3129   |  9140/15412  |   3XQ9/4HYB   |

###  [C8+/](C8+/) (Number of carbon atoms: 8+)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT) |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:-------------:|
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |      |      |        |   |     |  1298/4579   |  6912/16935  |   3W2O/4ENC   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |      |      |   ✓    |   |     |  1304/4585   |  6950/16973  |   3W30/4ENO   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |      |        |   |     |  1331/4675   |  7064/17327  |   3XKO/4HNC   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |      |   ✓    |   |     |  1337/4681   |  7102/17365  |   3XL0/4HNO   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |        |   |     |  1356/4735   |  7171/17541  |   3XQO/4HZC   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |   ✓    |   |     |  1362/4741   |  7209/17579  |   3XR0/4HZO   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |      |      |        | ✓ |     |  1401/4682   |  7884/17933  |   3W2W/4ENM   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |      |      |   ✓    | ✓ |     |  1407/4688   |  7922/17971  |   3W38/4ENY   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |      |        | ✓ |     |  1434/4778   |  8036/18325  |   3XKW/4HNM   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |      |   ✓    | ✓ |     |  1440/4784   |  8074/18363  |   3XL8/4HNY   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |        | ✓ |     |  1459/4838   |  8143/18539  |   3XQW/4HZM   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |   ✓    | ✓ |     |  1465/4844   |  8181/18577  |   3XR8/4HZY   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |        |   |  ✓  |  1495/4874   | 10247/20617  |   3XQP/4HZD   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |   ✓    |   |  ✓  |  1501/4880   | 10285/20655  |   3XR1/4HZP   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |        | ✓ |  ✓  |  1598/4977   | 11219/21615  |   3XQX/4HZN   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |   ✓    | ✓ |  ✓  |  1604/4983   | 11257/21653  |   3XR9/4HZZ   |
