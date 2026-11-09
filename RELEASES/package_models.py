"""Package generated public models; scientific validation remains internal."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def full_model_record(inventory):
    included = {module['key'] for module in inventory['included_submodules']}
    matches = [model for model in inventory['models']
               if set(model['modules']) == included
               and model['temperature_range'] == 'LT-HT']
    if len(matches) != 1:
        raise ValueError('Expected one complete low- and high-temperature model')
    return matches[0]


def copy_full_model(models, package, model, model_name):
    names = {
        'chemkin_reactions': model_name + '.CKI',
        'thermochemistry': model_name + '.THERM',
        'transport': model_name + '.TRAN',
        'cantera_yaml': model_name + '.yaml',
        'legacy_ic_reactions': 'LEGACY/' + model_name + '_IC.CKI',
    }
    artifacts = {}
    for kind, artifact in model['artifacts'].items():
        relative = Path('FULL_MODEL') / names[kind]
        destination = package / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(models / artifact['path'], destination)
        artifacts[kind] = dict(artifact, path=relative.as_posix())
    return dict(model, directory='FULL_MODEL', artifacts=artifacts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models-dir', type=Path, required=True,
                        help='Output of compile_c3mech.py --generate-all')
    parser.add_argument('--species-pdf', type=Path, required=True,
                        help='Species dictionary generated from this source')
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='New directory for the package and ZIP')
    args = parser.parse_args()
    models = args.models_dir.resolve()
    output = args.output_dir.resolve()
    pdf = args.species_pdf.resolve()
    if output == models or models in output.parents:
        parser.error('--output-dir must be outside --models-dir')
    if not pdf.is_file():
        parser.error('--species-pdf must name an existing PDF')
    inventory = json.loads((models / 'MODEL_MANIFEST.json').read_text())
    configuration = yaml.safe_load((ROOT / 'RELEASES/V4.2.0/c3mech.yaml').read_text())
    release = yaml.safe_load((ROOT / 'RELEASES/V4.2.0/release.yaml').read_text())
    version = configuration['model']['version']
    if inventory['model_version'] != version:
        parser.error('Generated models and release metadata use different versions')
    full_model = full_model_record(inventory)
    output.mkdir(parents=True, exist_ok=False)
    package = output / inventory['model_name']
    shutil.copytree(models, package, ignore=shutil.ignore_patterns('.gitignore'))
    full_model = copy_full_model(models, package, full_model,
                                 inventory['model_name'])
    catalog = package / 'MODEL_CATALOG.md'
    heading, _, body = catalog.read_text().partition('\n')
    catalog.write_text(heading + '\n\nThe complete model is available in '
                       '[FULL_MODEL/](FULL_MODEL/) with simple filenames.\n\n'
                       + body.lstrip('\n'))
    for source, destination in [
        ('RELEASES/DISTRIBUTION_README.md', 'README.md'),
        ('RELEASES/V4.2.0/RELEASE_NOTES.md', 'RELEASE_NOTES.md'),
        ('RELEASES/V4.2.0/USAGE_TERMS.md', 'USAGE_TERMS.md'),
        ('LICENSE', 'LICENSE'),
        ('CITATION.cff', 'CITATION.cff'),
        ('SPECIES_DICTIONARY/species_dict.csv', 'SPECIES_DICTIONARY/species_dict.csv'),
    ]:
        destination = package / destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, destination)
    shutil.copyfile(pdf, package / 'SPECIES_DICTIONARY/species_dict.pdf')
    files = [dict(path=path.relative_to(package).as_posix(), sha256=sha256(path))
             for path in sorted(package.rglob('*')) if path.is_file()]
    manifest = dict(schema_version=2, model_name=inventory['model_name'],
                    model_version=version,
                    release_candidate=release['release_candidate'],
                    source_commit=inventory['source_commit'],
                    source_tree=inventory['source_tree'],
                    source_dirty=inventory['source_dirty'],
                    compiler_version=inventory['compiler_version'],
                    maximum_carbon_count=inventory['maximum_carbon_count'],
                    cantera_yaml_generated=inventory['cantera_yaml_generated'],
                    models=inventory['models'], full_model=full_model,
                    files=files)
    (package / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    archive = output / (inventory['model_name'] + '.zip')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(package.rglob('*')):
            if path.is_file():
                zipped.write(path, path.relative_to(output).as_posix())
    checksum = archive.with_suffix('.zip.sha256')
    checksum.write_text(sha256(archive) + '  ' + archive.name + '\n')
    print('Public model package written to ' + str(archive))
    print('Archive checksum written to ' + str(checksum))


if __name__ == '__main__':
    main()
