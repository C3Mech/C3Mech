# Chemical kinetic model compilation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This directory provides the workflow to compile sub-modules into CHEMKIN and
Cantera YAML formats.

## Setup

Run all commands in this README from `COMPILER/`.

Create the `c3-compiler` environment:

```sh
mamba env create -f environment.yaml
```

Use `c3-compiler` for compiler runs. Do not run compiler jobs in `c3-rmg`.
The species-dictionary environment (`c3-rmg`) is separate and can use
different package versions.

## How to use

1. **Select sub-modules**

   Open and edit `submodules.yaml` to specify the sub-modules you want to include
   in the final chemical kinetic model.

   Paired source files identify collider formulations. `_IC.MECH` uses the
   independent-collider (IC) formulation. The unsuffixed counterpart contains
   collider-specific `LOWMX/LOWSP` input for the linear mixture rule in reduced
   pressure (LMR-R, or LMRR) or in pressure (LMR-P, or LMRP), as selected by the
   solver. The adopted ammonia chemistry was optimized using LMR-R reaction
   rates. These labels describe the formulation rather than restricting the
   choice of simulation software.

   We recommend the [linear mixture rule in reduced pressure (LMRR)](https://doi.org/10.1016/j.proci.2016.06.068).
   The default source selection uses LOWMX/LOWSP input. Generated Cantera YAML
   models use native LMRR (`linear-Burke`) and require Cantera 3.1 or later.
   When selecting a model by its identifier, `--mid-ic` selects the IC source
   variant; `--no-mid-ic` selects LOWMX/LOWSP input and is the default. The
   former `--mid-cantera` and `--no-mid-cantera` options remain accepted aliases.
   IC source selections generate a CHEMKIN mechanism file, without a Cantera YAML file.

2. **Compile the chemical kinetic model**

   Run the following command in the terminal:

   ```sh
   mamba run -n c3-compiler python compile_c3mech.py
   ```

The command writes `.CKI`, `.THERM`, `.TRAN` and native LMRR `.yaml` files
under `output/` when Cantera conversion is enabled. With `--generate-all`,
each submodel also has `LEGACY/<model>_IC.CKI`. This file supports simulation
software that reads mechanisms in CHEMKIN format but does not support LMRR.
It uses the `.THERM` and `.TRAN` files in its parent directory. No separate
IC Cantera YAML file is supplied.

For more information, use:

```sh
mamba run -n c3-compiler python compile_c3mech.py -h
```

### Reaction order

By default, reactions are grouped by canonical representation (`--reorder true`).
To preserve their source order, including reaction-class comment blocks, run:

```sh
mamba run -n c3-compiler python compile_c3mech.py --reorder false
```

This changes only output order; reaction matching and pruning remain enabled
according to their existing options. It also applies to `--generate-all`.

### Historical model identifiers

A model identifier (MID) encodes a submodule selection within a C3Mech version.
Submodule selections retain their MIDs when submodules are added in later V4
versions. The `--model-version` option restricts MID decoding to the
submodules supported by the selected C3Mech version. Using a V4.0.1 MID with the
current default inputs compiles that selection from the current submodules,
thermochemistry, and transport data. To reproduce a historical release,
provide its corresponding submodules, thermochemistry, transport data, and
header.

## Public submodule inventory

This snapshot supplies the existing public C0 through C7, LLNL, DMC/EC,
ammonia, carbon-nitrogen and aromatic modules. Default compilation, model
identifier selection and `--generate-all` use this public inventory. The
identifier coding table is preserved; an identifier requiring a module that
is not supplied produces an explanatory error.

## Generate all models

Create a dedicated empty output directory. The directory must exist and be empty, apart from an optional `.gitignore`
file. Use a separate output directory for each generation.

```sh
mkdir output/V4.2.0-rc.3
```

Generate every supported combination of the supplied public submodules and
generate native LMRR Cantera YAML.

```sh
mamba run -n c3-compiler python compile_c3mech.py \
  --generate-all \
  --output-dir output/V4.2.0-rc.3
```

The final terminal line reports that `MODEL_CATALOG.md` was written. The catalog
is the completion marker. Its absence means that generation or solver conversion
failed.

To generate only carbon-zero models, create a separate empty output directory.

```sh
mkdir output/V4.2.0-rc.3-maxC0
```

Generate every carbon-zero selection.

```sh
mamba run -n c3-compiler python compile_c3mech.py \
  --generate-all \
  --max-c 0 \
  --output-dir output/V4.2.0-rc.3-maxC0
```

The final terminal line again reports that `MODEL_CATALOG.md` was written.

## Notes and recommendations

- **Selecting necessary sub-modules:** Selecting only the necessary sub-modules
  facilitates and speeds up kinetic simulations.
- **User responsibility:** The user must select appropriate sub-modules for a
  simulation case.

If you have further questions or need additional help, please feel free to open
an issue or [contact us](mailto:r.langer@itv.rwth-aachen.de).
