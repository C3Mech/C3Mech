# Precompiled models 

This directory contains precompiled chemical kinetic sub-models of C3MechV4.0, tailored to specific fuel compositions and conditions, and the full version of C3MechV4.0. The sub-models were compiled from the sub-modules in the directory [`SUBMODULES/`](../SUBMODULES/). The reactions in the sub-modules are grouped based on the number of carbon atoms in the species (C0, C1-C2, C3-C4, C5, C6, C7, C8+, C5CY, C6CY), with aromatic species being managed separately. Here, 'CY' refers to non-aromatic, cyclic fuel components. Additionally, sub-modules for dimethyl carbonate and ethylene carbonate (DMC+EC), nitrogen-containing species (N), cross-reactions between nitrogen- and carbon-containing species (C-N), and polycyclic aromatic hydrocarbons (PAH) are available. The tables below list all precompiled sub-models, where in this subdirectory "N" refers to the combined N- and C-N sub-modules if a sub-model contains carbon atoms. 

Many sub-models are available as smaller high-temperature (HT) versions, which are suitable for simulations of unstretched premixed and counterflow flames, high-temperature flow reactors, and shock tubes. Low-temperature (LT) chemistry is, for example, required to simulate jet-stirred reactors, flow reactors under lower-temperature conditions, and rapid compression machine (RCM) experiments. The columns NS(HT/LT-HT) and NR(HT/LT-HT) in the tables below refer to the number of species and reactions in the respective sub-models. 

Each HT and LT-HT version is assigned a unique model ID (MID(HT/LT-HT)) that encodes the specific sub-module combination; if a single model is used across all temperatures, the counts (NS and NR) and MIDs are the same. If you need a combination not listed here, see [`COMPILER/`](../COMPILER/) directory for an easy-to-use script to create custom sub-models.

## Notes and recommendations 
- **Selecting a sub-model:** Selecting a sub-model with only the necessary sub-modules facilitates and speeds up kinetic simulations. 
- **User responsibility:** The user must select an _appropriate_ sub-model for a simulation case. 

For questions or suggestions, please open an issue or 
[contact us](mailto:r.langer@itv.rwth-aachen.de). 

## Available precompiled models 

You can download individual files in your web browser or clone all files. For each sub-model, there are CHEMKIN (.CKI, .THERM, and .TRAN) and Cantera (.yaml) files. The .CKI files are provided as CHEMKIN-PRO/OpenSMOKE++-compatible versions as well as Cantera/FlameMaster-compatible versions (filename contains the string 'Cantera'). Once you have found a suitable sub-model, you can use its `MID` to find the corresponding files. It is recommended to refer to a  model's `MID` when using a sub-model of C3MechV4.0. 

## Quick access table with commonly used sub-models

| Fuels                      | Directory      | MID(HT/LT-HT) | C0 | C1-C2 | C3-C4 | C5 | C6-C8+ | C5CY | C6CY | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) |
|:--------------------------:|:--------------:|:-------------:|:--:|:-----:|:-----:|:--:|:------:|:----:|:----:|:-:|:---:|:------------:|:------------:|
| Hydrogen and ammonia       |[C0/](C0/)      |   2906/2906   | ✓  |       |       |    |        |      |      | ✓ |     |    43/43     |   273/273    |
| Methane                    |[C1-C2/](C1-C2/)|   3DI0/3DI0   | ✓  |   ✓   |       |    |        |      |      |   |     |   108/108    |   663/663    |
| C0-C4 fuels                |[C3-C4/](C3-C4/)|   3R00/44I0   | ✓  |   ✓   |   ✓   |    |        |      |      |   |     |   380/729    |  2523/3964   |
| Aromatic and cyclic fuels\*|[C6/](C6/)      |   3SO1/47U1   | ✓  |   ✓   |   ✓   |    |        |  ✓   |  ✓   |   |  ✓  |   607/1060   |  5847/7637   |
| Cyclopentadiene            |[C6/](C6/)      |   3X61/4GU1   | ✓  |   ✓   |   ✓   | ✓  |        |  ✓   |  ✓   |   |  ✓  |   771/1556   |  6791/9594   |
| TPRF\*\*                   |[C8+/](C8+/)    |   3XQP/4HZD   | ✓  |   ✓   |   ✓   | ✓  |   ✓    |  ✓   |  ✓   |   |  ✓  |  1607/4935   | 10478/20778  |

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
| ✓  |   ✓   |       |    |    |    |     |      |      |        |   |     |   108/108    |   663/663    |   3DI0/3DI0   |
| ✓  |   ✓   |       |    |    |    |     |      |      |   ✓    |   |     |   115/115    |   701/701    |   3DIC/3DIC   |
| ✓  |   ✓   |       |    |    |    |     |      |      |        | ✓ |     |   250/269    |  1635/1661   |   3DI8/3DIA   |

###  [C3-C4/](C3-C4/) (Number of carbon atoms: 3–4)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT) |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:-------------:|
| ✓  |   ✓   |   ✓   |    |    |    |     |      |      |        |   |     |   380/729    |  2523/3964   |   3R00/44I0   |
| ✓  |   ✓   |   ✓   |    |    |    |     |      |      |        | ✓ |     |   501/867    |  3495/4962   |   3R08/44IA   |

###  [C5/](C5/) (Number of carbon atoms: 5)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT) |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:-------------:|
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |      |        |   |     |   431/845    |  2676/4356   |   3SI0/47I0   |
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |      |        | ✓ |     |   551/982    |  3648/5354   |   3SI8/47IA   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |      |      |        |   |     |   563/1247   |  3467/5921   |   3VI0/4DI0   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |      |        |   |     |   597/1343   |  3620/6313   |   3X00/4GI0   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |      |      |        | ✓ |     |   676/1374   |  4439/6919   |   3VI8/4DIA   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |      |        | ✓ |     |   710/1470   |  4592/7311   |   3X08/4GIA   |

###  [C6/](C6/) (Number of carbon atoms: 6)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT) |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:-------------:|
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |  ✓   |        |   |     |   461/914    |  2783/4573   |   3SO0/47U0   |
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |  ✓   |        | ✓ |     |   581/1051   |  3755/5571   |   3SO8/47UA   |
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |  ✓   |        |   |  ✓  |   607/1060   |  5847/7637   |   3SO1/47U1   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |  ✓   |        |   |     |   626/1411   |  3727/6530   |   3X60/4GU0   |
| ✓  |   ✓   |   ✓   |    |    |    |     |  ✓   |  ✓   |        | ✓ |  ✓  |   727/1197   |  6819/8635   |   3SO9/47UB   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |  ✓   |        | ✓ |     |   739/1538   |  4699/7528   |   3X68/4GUA   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |  ✓   |        |   |  ✓  |   771/1556   |  6791/9594   |   3X61/4GU1   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |      |      |        |   |     |   832/2299   |  4584/9407   |   3W00/4EI0   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |      |        |   |     |   866/2395   |  4737/9799   |   3XI0/4HI0   |
| ✓  |   ✓   |   ✓   | ✓  |    |    |     |  ✓   |  ✓   |        | ✓ |  ✓  |   884/1683   |  7763/10592  |   3X69/4GUB   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |  ✓   |        |   |     |   892/2459   |  4844/10016  |   3XO0/4HU0   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |      |      |        | ✓ |     |   940/2415   |  5556/10405  |   3W08/4EIA   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |      |        | ✓ |     |   974/2511   |  5709/10797  |   3XI8/4HIA   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |  ✓   |        | ✓ |     |  1000/2575   |  5816/11014  |   3XO8/4HUA   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |  ✓   |        |   |  ✓  |  1035/2602   |  7908/13080  |   3XO1/4HU1   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  |    |     |  ✓   |  ✓   |        | ✓ |  ✓  |  1143/2718   |  8880/14078  |   3XO9/4HUB   |

###  [C7/](C7/) (Number of carbon atoms: 7)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT) |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:-------------:|
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |      |      |        |   |     |   935/2741   |  4934/10768  |   3W20/4EM0   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |      |        |   |     |   969/2837   |  5087/11160  |   3XK0/4HM0   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |  ✓   |        |   |     |   994/2900   |  5194/11377  |   3XQ0/4HY0   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |      |      |        | ✓ |     |  1038/2844   |  5906/11766  |   3W28/4EMA   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |      |        | ✓ |     |  1072/2940   |  6059/12158  |   3XK8/4HMA   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |  ✓   |        | ✓ |     |  1097/3003   |  6166/12375  |   3XQ8/4HYA   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |  ✓   |        |   |  ✓  |  1137/3043   |  8258/14441  |   3XQ1/4HY1   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |     |  ✓   |  ✓   |        | ✓ |  ✓  |  1240/3146   |  9230/15439  |   3XQ9/4HYB   |

###  [C8+/](C8+/) (Number of carbon atoms: 8+)

| C0 | C1-C2 | C3-C4 | C5 | C6 | C7 | C8+ | C5CY | C6CY | DMC+EC | N | PAH | NS(HT/LT-HT) | NR(HT/LT-HT) | MID(HT/LT-HT) |
|:--:|:-----:|:-----:|:--:|:--:|:--:|:---:|:----:|:----:|:------:|:-:|:---:|:------------:|:------------:|:-------------:|
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |      |      |        |   |     |  1407/4635   |  7154/17105  |   3W2O/4ENC   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |      |      |   ✓    |   |     |  1413/4641   |  7192/17143  |   3W30/4ENO   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |      |        |   |     |  1441/4731   |  7307/17497  |   3XKO/4HNC   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |      |   ✓    |   |     |  1447/4737   |  7345/17535  |   3XL0/4HNO   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |        |   |     |  1466/4794   |  7414/17714  |   3XQO/4HZC   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |   ✓    |   |     |  1472/4800   |  7452/17752  |   3XR0/4HZO   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |      |      |        | ✓ |     |  1510/4738   |  8126/18103  |   3W2W/4ENM   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |      |      |   ✓    | ✓ |     |  1516/4744   |  8164/18141  |   3W38/4ENY   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |      |        | ✓ |     |  1544/4834   |  8279/18495  |   3XKW/4HNM   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |      |   ✓    | ✓ |     |  1550/4840   |  8317/18533  |   3XL8/4HNY   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |        | ✓ |     |  1569/4897   |  8386/18712  |   3XQW/4HZM   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |   ✓    | ✓ |     |  1575/4903   |  8424/18750  |   3XR8/4HZY   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |        |   |  ✓  |  1607/4935   | 10478/20778  |   3XQP/4HZD   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |   ✓    |   |  ✓  |  1613/4941   | 10516/20816  |   3XR1/4HZP   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |        | ✓ |  ✓  |  1710/5038   | 11450/21776  |   3XQX/4HZN   |
| ✓  |   ✓   |   ✓   | ✓  | ✓  | ✓  |  ✓  |  ✓   |  ✓   |   ✓    | ✓ |  ✓  |  1716/5044   | 11488/21814  |   3XR9/4HZZ   |
