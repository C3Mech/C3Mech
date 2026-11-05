# Species Dictionary

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

All species in the C3 chemical kinetic model are defined in
`species_dict.csv`. The comma-separated values (CSV) file has seven columns:

- `model_name`: name used in CHEMKIN files (uppercase ASCII string)
- `inchi`: International Chemical Identifier (InChI) string (ASCII)
- `smiles`: simplified molecular-input line-entry system (SMILES) string
  (ASCII)
- `excited`: `1` if excited, otherwise `0`
- `multiplicity`: energy-level multiplicity (`0` if unspecified, otherwise `2S+1`)
- `lumped`: `1` if one `model_name` maps to multiple structures, otherwise `0`
- `rdkit_stereochemistry`: `1` if stereochemistry is RDKit-compatible, otherwise `0`

The tuple (`inchi`, `excited`, `multiplicity`) must be unique per row.

## Setup

Run the commands in this README from `SPECIES_DICTIONARY/`.

Create the `c3-rmg` environment for species-dictionary generation:

```sh
mamba env create -f environment.yaml
```

`environment.yaml` provides the species-dictionary dependencies, including
RMG (module `rmgpy`) for optional lumped-species radical/resonance checks.

## Editing `species_dict.csv`

`species_dict.csv` is the only data file that should be edited.

Converts comma-separated SMILES strings to InChI strings. The converted
structures are printed to the terminal:

```sh
mamba run -n c3-rmg python smiles2inchi.py \
  "C=CCN([O])[O], C=C(C)N([O])[O]"
```

Converts semicolon-separated InChI strings to SMILES strings. The converted
structures are printed to the terminal:

```sh
mamba run -n c3-rmg python inchi2smiles.py \
  "InChI=1S/C3H7NO2/c1-3(2)4(5)6/h3H,1-2H3; InChI=1S/C2H4NO2/c1-2-5-3-4/h1-2H2"
```

## Use an existing model in CHEMKIN format

By default, `make_species_dict.py` obtains species names from the submodules
listed in `submodules.yaml`. To instead read the species names from the
`SPECIES` section of an existing CHEMKIN kinetics file, pass `--yaml ''` and
provide the file with `--kinetics`. Without `--yaml ''`, the species names are
obtained from the submodules listed in the YAML file.

## Generate `species_dict.pdf`

The PDF stored in this source directory is the earlier V4.0.1 snapshot.
Use the PDF supplied with the V4.2.0-rc.3 release for the current candidate,
or generate a new document from the current CSV using the commands below.

Generates species images and `output/species_dict.tex`. The terminal reports
the `pdflatex` command after successful generation:

```sh
mamba run -n c3-rmg python make_species_dict.py \
  --missing-definition-policy warning
```

The optional `--provenance` flag records the source commit, source dirty state,
and SHA-256 hash of the selected species dictionary CSV in the generated TeX
source. It also regenerates every species image. `pdflatex` transfers these
values into the PDF.

The mamba environment does not install `pdflatex`. With a separate TeX
installation that provides `pdflatex`, compile the generated TeX source from
`SPECIES_DICTIONARY/output/`:

```sh
(cd output && pdflatex species_dict.tex)
```

Successful compilation reports `Output written on species_dict.pdf`.

## Formatting

Use `yapf` for formatting Python files:

```sh
mamba run -n c3-rmg yapf make_species_dict.py \
  -i \
  --style='{based_on_style: pep8, indent_width: 2}'
```

The formatting command is silent on success.
