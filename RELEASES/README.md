# Generate the public release candidate

The public repository contains the compiler and inputs needed to generate
all supported public submodels. Generated models belong in the release ZIP,
not in the source repository. Scientific validation and release audits are
performed internally. The commands here compile models, generate the species
dictionary and package the results. They do not push branches, create tags or
publish releases.

Run these commands from the repository root in the `c3-compiler` environment.
Create that environment using `COMPILER/environment.yaml`. A separate TeX
installation must provide `pdflatex` to generate the species PDF.

## Compile all model combinations

Create a new empty output directory, then compile every supported combination.

```sh
mkdir -p RELEASES/build/V4.2.0-rc.3/models
python COMPILER/compile_c3mech.py \
  --generate-all \
  --no-prune \
  --output-dir RELEASES/build/V4.2.0-rc.3/models
```

The compiler writes the main CHEMKIN and native LMRR Cantera models, legacy
IC CHEMKIN mechanism files, `MODEL_CATALOG.md` and
`MODEL_MANIFEST.json`. Normal parsing and Cantera conversion remain part of
compilation. No `VALIDATION` or `CHECKS` directory is required.

## Generate the current species dictionary

```sh
mkdir -p RELEASES/build/V4.2.0-rc.3/species
python SPECIES_DICTIONARY/make_species_dict.py \
  --output_dir RELEASES/build/V4.2.0-rc.3/species \
  --disable-rmg-lumped-checks
```

Compile the generated document from its output directory.

```sh
(cd RELEASES/build/V4.2.0-rc.3/species && pdflatex -interaction=batchmode -halt-on-error species_dict.tex)
```

When generating from a committed Git checkout, add `--provenance` to the
species-generation command to record its source identity. Keep the same
source snapshot for model and dictionary generation.

## Package the models

The package destination must be a new directory. Existing output is never
removed or replaced by this helper.

```sh
python RELEASES/package_models.py \
  --models-dir RELEASES/build/V4.2.0-rc.3/models \
  --species-pdf RELEASES/build/V4.2.0-rc.3/species/species_dict.pdf \
  --output-dir RELEASES/build/V4.2.0-rc.3/distribution
```

The helper copies the models, current species CSV and PDF, release notes,
public terms, license and citation file into `C3MechV4.2.0/`. It creates
`C3MechV4.2.0.zip`, a checksum file and a manifest of the package contents.
The ZIP includes `FULL_MODEL/` with the simple filenames
`C3MechV4.2.0.CKI`, `.THERM`, `.TRAN` and `.yaml`, plus
`FULL_MODEL/LEGACY/C3MechV4.2.0_IC.CKI`. These files are byte-for-byte copies
of the complete low- and high-temperature model in the generated collection.
The other model folders and their catalogue retain the generated filenames.
Internal scientific checks and publication review are separate steps.

The fixed public candidate is `V4.2.0-rc.3`. The public `main` branch remains
the stable model until the ammonia paper is accepted and the model is
finalized. The preprint citation will be added when the manuscript is archived.
