"""Convert C3 LOWMX/LOWSP kinetics to native Cantera LMRR YAML.

The temporary ordinary-falloff form lets Cantera's CHEMKIN reader parse the
unchanged reactions, species and units. Original source-line numbers identify
exactly which falloff entries receive collider-specific linear-Burke data.
"""
from pathlib import Path
import argparse
import copy
import re
import tempfile

import cantera as ct
from cantera import ck2yaml
from ruamel.yaml import YAML

_COLLIDER_KEYWORDS = {'LOWMX', 'TROEMX', 'LOWSP', 'TROESP'}
_UNSUPPORTED = {'HIGHMX', 'HIGHSP'}
_NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][-+]?\d+)?'
_REACTION = re.compile(r'^(.*?)\s+(' + _NUMBER + r')\s+(' + _NUMBER +
                       r')\s+(' + _NUMBER + r')\s*$')
_KEYWORD = re.compile(r'^([A-Za-z]+)\s*/')
_EFFICIENCY = re.compile(r'([^\s/]+)\s*/\s*(' + _NUMBER + r')\s*/')


def _values(text):
    return tuple(float(word.replace('D', 'E').replace('d', 'e'))
                 for word in text.split())


def _sanitize(text):
    lines = text.splitlines(keepends=True)
    records = []
    current = None
    active = False
    for index, raw in enumerate(lines):
        content = raw.split('!', 1)[0].strip()
        if not content:
            continue
        if re.match(r'^(REAC|REACTIONS)\b', content, re.I):
            active = True
            current = None
            continue
        if re.match(r'^END\b', content, re.I):
            active = False
            current = None
            continue
        if not active:
            continue
        reaction = _REACTION.fullmatch(content)
        if reaction and '=' in reaction[1]:
            current = dict(line=index, equation=reaction[1], auxiliary={},
                           efficiencies={})
            records.append(current)
            continue
        keyword = _KEYWORD.match(content)
        name = keyword[1].upper() if keyword else ''
        if name in _UNSUPPORTED:
            raise ValueError('native LMRR conversion does not support ' + name)
        if name in _COLLIDER_KEYWORDS:
            if current is None:
                raise ValueError(name + ' has no preceding reaction')
            if content.count('/') != 2:
                raise ValueError('expected one slash-delimited ' + name + ' entry')
            body = content.split('/')[1].strip()
            species = None
            if name in {'LOWSP', 'TROESP'}:
                species, body = body.split(None, 1)
            key = (name, species)
            if key in current['auxiliary']:
                raise ValueError('duplicate collider entry: ' + str(key))
            values = _values(body)
            if name.startswith('LOW') and (len(values) != 3 or values[0] <= 0):
                raise ValueError(name + ' requires positive Arrhenius A and three parameters')
            if name.startswith('TROE') and len(values) not in {3, 4}:
                raise ValueError(name + ' requires three or four Troe parameters')
            current['auxiliary'][key] = values
            if name in {'LOWMX', 'TROEMX'}:
                plain = 'LOW' if name == 'LOWMX' else 'TROE'
                lines[index] = re.sub(name, plain, raw, count=1, flags=re.I)
            else:
                lines[index] = '\n'  # Preserve source-line identity for ck2yaml.
        elif current is not None:
            for match in _EFFICIENCY.finditer(content):
                species = match[1]
                value = _values(match[2])[0]
                if species in current['efficiencies']:
                    raise ValueError('duplicate third-body efficiency: ' + species)
                current['efficiencies'][species] = value
    mixture_records = {}
    for record in records:
        aux = record['auxiliary']
        if not aux:
            continue
        if ('LOWMX', None) not in aux:
            raise ValueError('collider-specific reaction lacks LOWMX: ' + record['equation'])
        for name, species in aux:
            if name == 'TROESP' and ('LOWSP', species) not in aux:
                raise ValueError('TROESP lacks corresponding LOWSP: ' + species)
        mixture_records[record['line']] = record
    return ''.join(lines), mixture_records


def _plain(value):
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _troe(values):
    return dict(zip(('A', 'T3', 'T1', 'T2'), values))


def _native_data(record, template, energy_units, species_names):
    if not isinstance(template.rate, ct.TroeRate):
        raise ValueError('native LOWMX conversion requires Troe falloff data: ' + template.equation)
    aux = record['auxiliary']
    reference = aux['LOWMX', None]
    default_shape = aux.get(('TROEMX', None))
    rate = _plain(template.rate.input_data)
    colliders = [dict(name='M', **rate)]
    names = set(record['efficiencies']) | {
        species for name, species in aux if name == 'LOWSP'}
    for species in sorted(names):
        if species not in species_names:
            raise ValueError('collider is absent from the model species list: ' + species)
        if ('LOWSP', species) in aux:
            values = aux['LOWSP', species]
            efficiency = dict(A=values[0]/reference[0],
                              b=values[1]-reference[1],
                              Ea=energy_units.convert_activation_energy_to(
                                  values[2]-reference[2], 'J/kmol'))
            own = copy.deepcopy(rate)
            own['low-P-rate-constant'] = dict(
                A=template.rate.low_rate.pre_exponential_factor * values[0]/reference[0],
                b=values[1],
                Ea=energy_units.convert_activation_energy_to(values[2], 'J/kmol'))
            shape = aux.get(('TROESP', species), default_shape)
            if shape is None:
                own.pop('Troe', None)
            else:
                own['Troe'] = _troe(shape)
            colliders.append(dict(name=species, efficiency=efficiency, **own))
        else:
            colliders.append(dict(name=species, efficiency=dict(
                A=record['efficiencies'][species], b=0., Ea=0.)))
    data = dict(equation=template.equation, type='linear-Burke',
                units={'length': 'm', 'quantity': 'kmol',
                       'activation-energy': 'J/kmol'},
                colliders=colliders)
    for field in ('duplicate', 'orders', 'negative-orders',
                  'nonreactant-orders', 'note'):
        if field in template.input_data:
            data[field] = _plain(template.input_data[field])
    return data


def convert(kinetics, thermochemistry, transport, output):
    """Write and load one native LMRR YAML; retain all non-mixture reactions."""
    if tuple(int(v) for v in ct.__version__.split('.')[:2]) < (3, 1):
        raise ValueError('native LMRR requires Cantera 3.1 or later')
    kinetics = Path(kinetics)
    thermochemistry = Path(thermochemistry)
    transport = Path(transport)
    output = Path(output)
    if output.exists():
        raise FileExistsError('refuse to replace existing YAML: ' + str(output))
    sanitized, records = _sanitize(kinetics.read_text())
    with tempfile.TemporaryDirectory(prefix='c3_lmrr_') as temporary:
        temporary = Path(temporary)
        raw_kinetics = temporary / kinetics.name
        raw_yaml = temporary / 'reference_falloff.yaml'
        raw_kinetics.write_text(sanitized)
        parser, _ = ck2yaml.Parser.convert_mech(
            str(raw_kinetics), str(thermochemistry), str(transport),
            out_name=str(raw_yaml), quiet=True, permissive=False)
        yaml = YAML()  # YAML 1.2; retain literal multiline provenance headers.
        with raw_yaml.open() as stream:
            data = yaml.load(stream)
        reference = ct.Solution(str(raw_yaml))
        units = ct.UnitSystem(data.get('units', {}))
        if len(parser.reactions) != reference.n_reactions:
            raise ValueError('Cantera reaction inventory differs from CHEMKIN parser')
        changed = []
        matched = set()
        for index, parsed in enumerate(parser.reactions):
            line = parsed.line_number
            if line not in records:
                continue
            if line in matched:
                raise ValueError('LOWMX reaction expands into multiple parser entries')
            record = records[line]
            data['reactions'][index] = _native_data(
                record, reference.reaction(index), units,
                set(reference.species_names))
            matched.add(line)
            changed.append(dict(index=index, equation=reference.reaction(index).equation,
                                source_line=line+1))
        if matched != set(records):
            raise ValueError('some LOWMX source reactions were not mapped')
        data['generator'] = 'c3mech-lmrr'
        data['input-files'] = [kinetics.name, thermochemistry.name, transport.name]
        candidate = temporary / 'native.yaml'
        yaml.default_flow_style = False
        yaml.width = 1000000
        with candidate.open('x') as stream:
            yaml.dump(data, stream)
        gas = ct.Solution(str(candidate))
        if gas.species_names != reference.species_names or gas.n_reactions != reference.n_reactions:
            raise ValueError('native conversion changed species or reaction inventory')
        for item in changed:
            if gas.reaction(item['index']).rate.type != 'linear-Burke':
                raise ValueError('native LMRR rate missing after YAML reload')
        with output.open('xb') as stream:
            stream.write(candidate.read_bytes())
    return dict(species=gas.n_species, reactions=gas.n_reactions,
                native_lmrr_reactions=changed, cantera_version=ct.__version__)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--thermo', required=True)
    parser.add_argument('--transport', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = convert(args.input, args.thermo, args.transport, args.output)
    print('Mechanism contains ' + str(result['species']) + ' species and ' +
          str(result['reactions']) + ' reactions.')
    print('Validating mechanism...')
    print('PASSED')


if __name__ == '__main__':
    main()
