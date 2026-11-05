import os
import sys
import yaml
import re
import copy
import codecs
from pathlib import Path

from . import reaction as rxn

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

from SPECIES_DICTIONARY.element_order import THERMO_SUM_FORMULA_ELEMENTS

elements = dict(THERMO_SUM_FORMULA_ELEMENTS)

_STOICH_OR_SPECIES_TOKEN = re.compile(
    r'^(\d+(?:\.\d*)?|\.\d+)\s*([\w\-\(\),\#]+)$')
_SIGNED_DECIMAL_TOKEN = re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$')
_SCIENTIFIC_DECIMAL_TOKEN = re.compile(
    r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)[eE][+-]?\d+$')
_SCIENTIFIC_STOICH_PREFIX = re.compile(r'^\d+(?:\.\d*)?[eE][+-]?\d')
_POSITIVE_DECIMAL_TOKEN = re.compile(r'^(?:\d+(?:\.\d*)?|\.\d+)$')


def _decode_text_bytes(raw, file_path):
  starts_with_utf8_bom = raw.startswith(codecs.BOM_UTF8)
  if raw.startswith(codecs.BOM_UTF8):
    try:
      text = raw.decode("utf-8-sig")
      if "\x00" not in text:
        return text, "utf-8-sig"
    except UnicodeDecodeError:
      pass

  raw_fallback = raw[len(codecs.BOM_UTF8):] if starts_with_utf8_bom else raw
  for encoding in ["utf-8", "cp1252", "latin-1"]:
    try:
      text = raw_fallback.decode(encoding)
    except UnicodeDecodeError:
      continue
    if "\x00" in text:
      # Reject UTF-16/UTF-32 style data decoded as single-byte text.
      continue
    return text, encoding

  raise ValueError("failed to decode text file '" + str(file_path) +
                   "' as utf-8/cp1252/latin-1 without null bytes")


def _read_text_lines(file_path):
  raw = Path(file_path).read_bytes()
  text, encoding = _decode_text_bytes(raw, file_path)
  if text and not text.endswith("\n"):
    text += "\n"
  return text.splitlines(True), encoding


def clean_reaction_species_token(token):
  """Normalize one raw reaction-side species token.

  Keeps original case and returns an empty string for non-species tokens.
  """
  spc_clean = token.strip()
  if not spc_clean:
    return ""

  parts = spc_clean.split()
  if len(parts) > 1:
    # Keep "coef species" together when written with spaces (for example
    # "1.2 A"), otherwise keep the first token (for example "A 1.0E+10").
    if (_POSITIVE_DECIMAL_TOKEN.fullmatch(parts[0])
        and (parts[1][0].isalpha() or parts[1][0] == '(')):
      spc_clean = parts[0] + parts[1]
    else:
      spc_clean = parts[0]

  if not spc_clean:
    return ""

  # Bare numeric token is not a species.
  if (_SIGNED_DECIMAL_TOKEN.fullmatch(spc_clean)
      or _SCIENTIFIC_DECIMAL_TOKEN.fullmatch(spc_clean)):
    return ""

  coeff_match = _STOICH_OR_SPECIES_TOKEN.match(spc_clean)
  if coeff_match:
    if _SCIENTIFIC_STOICH_PREFIX.match(spc_clean):
      raise ValueError("invalid stoichiometric token '" + token +
                       "' (scientific notation is not supported)")
    coeff = float(coeff_match.group(1))
    if coeff <= 0.0:
      raise ValueError(
          "non-positive stoichiometric coefficient in token '" + token + "'")
    spc_clean = coeff_match.group(2)
  elif (spc_clean[0].isdigit() or spc_clean[0] == '.' or spc_clean[0] == '+'
        or spc_clean[0] == '-'):
    if _SCIENTIFIC_DECIMAL_TOKEN.fullmatch(spc_clean):
      return ""
    if any(ch.isalpha() for ch in spc_clean):
      raise ValueError("invalid stoichiometric token '" + token +
                       "' (scientific notation is not supported)")
    return ""

  # if unclosed bracket: residue from a (+M) written with spaces perhaps
  if spc_clean[-1] == '(':
    spc_clean = spc_clean.split('(')[0]
  elif spc_clean[-1] == ')' and '(' not in spc_clean:
    spc_clean = spc_clean.split(')')[0]

  if spc_clean == 'M':
    return ""
  return spc_clean


_SECTION_PATTERN = re.compile(
    r"^(ELEM|ELEMENTS|SPEC|SPECIES|REAC|REACTIONS)\b", re.IGNORECASE)
_END_PATTERN = re.compile(r"^END\b", re.IGNORECASE)
_SPECIES_PRESSURE_PATTERN = re.compile(
    r"^(LOWSP|HIGHSP|TROESP)\s*/\s*([\w\-\(\),\#]+)(?=\s)",
    re.IGNORECASE)
_THIRD_BODY_PATTERN = re.compile(
    r"([\w\-\(\),\#]+)\s*/\s*([-+\d\.eE]+)\s*/", re.IGNORECASE)
_EXPLICIT_COLLIDER_PATTERN = re.compile(
    r"\(\s*\+\s*([\w\-\(\),\#]+)\s*\)", re.IGNORECASE)
_NON_SPECIES_AUXILIARY_KEYWORDS = {
    "REV", "LOW", "HIGH", "TROE", "LOWMX", "HIGHMX", "TROEMX",
    "PLOG", "TCHEB", "PCHEB", "CHEB", "DUP", "DUPLICATE"
}


class SpeciesList(list):
  """Ordered reaction species with collider-only species appended."""

  def __init__(self, species, collider_only=()):
    super().__init__(species)
    self.collider_only = tuple(collider_only)


def _section_name(line):
  match = _SECTION_PATTERN.match(line)
  if not match:
    return None
  token = match.group(1).upper()
  if token.startswith("ELEM"):
    return "ELEMENTS"
  if token.startswith("SPEC"):
    return "SPECIES"
  return "REACTIONS"


def iter_active_reaction_lines(lines, source_role, start_line_no=1):
  """Yield uncommented reaction data using the core or fragment contract."""
  if source_role not in {"core", "fragment"}:
    raise ValueError("source_role must be 'core' or 'fragment'")

  expected_sections = ["ELEMENTS", "SPECIES", "REACTIONS"]
  next_section = 0
  current_section = None

  for idx, line in enumerate(lines, start=start_line_no):
    lineunc = line.split('!', 1)[0].strip()
    if not lineunc:
      continue

    section = _section_name(lineunc)
    is_end = bool(_END_PATTERN.match(lineunc))

    if source_role == "fragment":
      if section is not None or is_end:
        raise ValueError("reaction fragment contains section record '" +
                         lineunc + "' at line " + str(idx))
      yield idx, lineunc
      continue

    if section is not None:
      if current_section is not None:
        raise ValueError("C0 core starts " + section + " before closing " +
                         current_section + " at line " + str(idx))
      if next_section >= len(expected_sections):
        raise ValueError("C0 core contains an extra " + section +
                         " section at line " + str(idx))
      expected = expected_sections[next_section]
      if section != expected:
        raise ValueError("C0 core expected " + expected + " but found " +
                         section + " at line " + str(idx))
      current_section = section
      next_section += 1
      continue

    if is_end:
      if current_section is None:
        raise ValueError("C0 core contains END outside a section at line " +
                         str(idx))
      current_section = None
      continue

    if current_section == "REACTIONS":
      yield idx, lineunc
    elif current_section is None:
      raise ValueError("C0 core contains content outside a section at line " +
                       str(idx) + ": '" + lineunc + "'")

  if source_role == "fragment":
    return

  if current_section is not None:
    raise ValueError("C0 core " + current_section +
                     " section is not closed by END")
  if next_section != len(expected_sections):
    raise ValueError("C0 core must contain ordered ELEMENTS, SPECIES, and "
                     "REACTIONS sections")


def iter_reaction_species_records(lines, source_role, start_line_no=1):
  """Yield line number, species, and whether it is a collider reference."""
  for idx, lineunc in iter_active_reaction_lines(lines, source_role,
                                                 start_line_no):
    sep = ''
    if '<=>' in lineunc:
      sep = '<=>'
    elif '=>' in lineunc:
      sep = '=>'
    elif '=' in lineunc:
      sep = '='

    if sep:
      reaction_eqn = remove_trailing_numbers(lineunc)
      for collider in _EXPLICIT_COLLIDER_PATTERN.findall(reaction_eqn):
        if collider.upper() != "M":
          yield idx, collider, True
      reaction_eqn = _EXPLICIT_COLLIDER_PATTERN.sub('', reaction_eqn)
      rcts_rough, prds_rough = reaction_eqn.split(sep, 1)
      rcts = rcts_rough.strip().split('+')
      prds = prds_rough.strip().split('+')
      for spc in rcts + prds:
        spc_clean = clean_reaction_species_token(spc)
        if spc_clean:
          yield idx, spc_clean, False
      continue

    pressure_match = _SPECIES_PRESSURE_PATTERN.match(lineunc)
    if pressure_match:
      yield idx, pressure_match.group(2), True
      continue

    head_parts = lineunc.split('/', 1)[0].strip().split()
    if not head_parts:
      continue
    head = head_parts[0].upper()
    if head in _NON_SPECIES_AUXILIARY_KEYWORDS:
      continue
    for species, _ in _THIRD_BODY_PATTERN.findall(lineunc):
      yield idx, species, True


def iter_reaction_species_with_sources(lines, source_role, start_line_no=1):
  """Yield every species referenced by active reaction data."""
  for idx, species, _ in iter_reaction_species_records(
      lines, source_role, start_line_no):
    yield idx, species


def make_species_list(directory, files_list):
  if not files_list:
    raise ValueError("at least one C0 core file is required")
  reaction_species = []
  reaction_seen = set()
  collider_species = []
  collider_seen = set()
  for file_idx, file in enumerate(files_list):
    print(f"reading '{os.path.basename(file)}'")
    lines, _ = _read_text_lines(os.path.join(directory, file))
    source_role = "core" if file_idx == 0 else "fragment"
    for _, spc_clean, collider in iter_reaction_species_records(
        lines, source_role):
      if collider:
        if spc_clean not in collider_seen:
          collider_seen.add(spc_clean)
          collider_species.append(spc_clean)
      elif spc_clean not in reaction_seen:
        reaction_seen.add(spc_clean)
        reaction_species.append(spc_clean)

  mandatory = ['HE', 'N2', 'AR', 'C2H6', 'CO2', 'CH4']
  for m in mandatory:
    if m not in collider_seen:
      collider_seen.add(m)
      collider_species.append(m)

  collider_only = [
      species for species in collider_species
      if species not in reaction_seen
  ]
  return SpeciesList(reaction_species + collider_only, collider_only)


def parse_composition(composition, elements):
  # Primary format reference:
  # CHEMKIN-III manual (Kee et al., Sandia SAND96-8216), Table III.
  # Line-1 composition slots are fixed-width `2A1,I3`:
  #   - columns 25-44: 4 slots
  #   - columns 74-78: optional 5th slot
  # Legacy files in this chemical kinetic model also use dotted integer counts
  # (for example ` 5.` or `0.0`) in those 3-count columns; accepted.
  #
  # Parser intent:
  # - enforce fixed-column parsing exactly at 5-char slot boundaries;
  # - reject normalization heuristics that could reinterpret shifted symbols;
  # - keep compiler and validator behavior deterministic for malformed headers.

  def fail(msg):
    raise ValueError(msg + " (composition: '" + composition + "')")

  def parse_count_token(cnt):
    token = cnt.strip()
    if token == "":
      fail("ERROR: malformed element/count near '" + composition[c:] + "'")

    if re.fullmatch(r"[+-]?\d+", token):
      return int(token)

    if re.fullmatch(r"[+-]?(?:\d+\.\d*|\.\d+)", token):
      value = float(token)
      if not value.is_integer():
        fail("ERROR: non-integer element/count near '" + composition[c:] + "'")
      return int(value)

    fail("ERROR: malformed element/count near '" + composition[c:] + "'")

  cur_compo = {}
  count_nothing = 0
  if len(composition) % 5 != 0:
    fail("ERROR: malformed composition field length")

  n_fields = len(composition) // 5
  if n_fields not in [4, 5]:
    fail("ERROR: malformed number of composition fields")

  for i in range(n_fields):
    c = i * 5
    field = composition[c:c + 5]
    if field == "     ":
      count_nothing += 1
    else:
      # Strict fixed-width CHEMKIN composition field `2A1,I3`:
      # - 2 columns for element symbol (one-letter symbols must not be shifted)
      # - 3 columns for integer element count
      sym = field[:2]
      cnt = field[2:]

      count = parse_count_token(cnt)

      if sym == "  ":
        if count == 0:
          count_nothing += 1
          continue
        fail("ERROR: malformed element/count near '" + composition[c:] + "'")

      if not sym[0].isalpha():
        fail("ERROR: malformed element/count near '" + composition[c:] + "'")
      if not sym[0].isupper():
        fail("ERROR: element symbol must be uppercase near '" +
             composition[c:] + "'")

      if not (sym[1].isalpha() or sym[1] == ' '):
        fail("ERROR: malformed element/count near '" + composition[c:] + "'")
      if sym[1].isalpha() and not sym[1].isupper():
        fail("ERROR: element symbol must be uppercase near '" +
             composition[c:] + "'")

      symbol = sym[0] + (sym[1] if sym[1].isalpha() else '')

      if symbol not in elements:
        fail("ERROR: unknown element '" + symbol + "'")

      if count < 0 and symbol != "E":
        fail("ERROR: negative element/count only allowed for 'E'")

      if symbol in cur_compo:
        fail("ERROR: element '" + symbol + "' cannot be specified twice")

      cur_compo[symbol] = count
  if (count_nothing == n_fields):
    fail("ERROR: empty composition")
  return cur_compo


def _looks_like_optional_5th_composition_field(field):
  # Optional 5th composition slot uses the same fixed-width `2A1,I3` pattern
  # as the first four slots (Sandia SAND96-8216, Table III, columns 74-78).
  # This check is intentionally strict: field5 is included only when it is a
  # syntactically valid composition slot; otherwise it is ignored here and
  # validated explicitly in the thermochemistry validator.
  if len(field) != 5 or field == "     ":
    return False

  sym = field[:2]
  cnt = field[2:]

  token = cnt.strip()
  if token == "":
    return False

  try:
    if re.fullmatch(r"[+-]?\d+", token):
      count = int(token)
    elif re.fullmatch(r"[+-]?(?:\d+\.\d*|\.\d+)", token):
      value = float(token)
      if not value.is_integer():
        return False
      count = int(value)
    else:
      return False
  except ValueError:
    return False

  if sym == "  ":
    return count == 0

  if not sym[0].isalpha():
    return False
  if not sym[0].isupper():
    return False
  if not (sym[1].isalpha() or sym[1] == ' '):
    return False
  if sym[1].isalpha() and not sym[1].isupper():
    return False
  return True


def extract_therm_line1_composition_slots(line):
  """Extract THERM line-1 composition fields using compiler parsing contract.

  Always returns columns 25-44 and appends columns 74-78 only when that field
  is a syntactically valid optional 5th composition slot.

  Reference:
  CHEMKIN-III (Kee et al., Sandia SAND96-8216), Table III.

  Note:
  Thermochemistry validator policy and compiler parsing are independent.
  The validator may reject non-empty field5 by policy, while compiler/species-
  dictionary parsing still supports this CHEMKIN format feature for
  compatibility with existing files.
  """
  wrk_line = line.split("!")[0].rstrip()
  if len(wrk_line) < 44:
    raise ValueError("ERROR: malformed THERM header line (too short)")

  composition = wrk_line[24:44]
  field_5 = wrk_line[73:78] if len(wrk_line) >= 78 else ""
  if _looks_like_optional_5th_composition_field(field_5):
    composition += field_5
  return composition


def process_therm(therm_file, species_list):
  thermlines, _ = _read_text_lines(therm_file)

  species_composition = {}
  species_output = {}

  species_dict = {s.upper(): 0 for s in species_list}
  duplicate_therm_entries = {}

  for i in range(len(thermlines)):
    wrk_line = thermlines[i].split("!")[0]
    wrk_line = wrk_line.rstrip()
    if len(wrk_line) >= 80 and wrk_line[79] == '1':
      sp_name = wrk_line[0:25].split()[0].upper()
      if sp_name in species_dict and i + 3 < len(thermlines):
        if not species_dict[sp_name]:
          field_5 = wrk_line[73:78] if len(wrk_line) >= 78 else ""
          if _looks_like_optional_5th_composition_field(field_5):
            print("#warning: optional 5th THERM composition field used for '" +
                  sp_name + "' at line " + str(i + 1))
          composition = extract_therm_line1_composition_slots(wrk_line)
          species_composition[sp_name] = parse_composition(
              composition, elements)
          species_dict[sp_name] = 1
          species_output[sp_name] = [l for l in thermlines[i:i + 4]]
        else:
          if sp_name not in duplicate_therm_entries:
            duplicate_therm_entries[sp_name] = 0
          duplicate_therm_entries[sp_name] += 1
  if duplicate_therm_entries:
    duplicate_species = sorted(duplicate_therm_entries.keys())
    duplicate_entries = sum(duplicate_therm_entries.values())
    print("#warning: duplicate thermochemistry entries detected for " +
          str(len(duplicate_species)) + " compiler-selected species (" +
          str(duplicate_entries) +
          " extra entries); keeping first matching entry per species")
    preview_limit = 10
    preview = ", ".join(duplicate_species[:preview_limit])
    if len(duplicate_species) > preview_limit:
      preview += ", ..."
    print("          species with duplicates: " + preview)
  for s, v in species_dict.items():
    if v == 0:
      print('{0} : thermochemistry data not found...'.format(s))

  return species_composition, species_output


def require_species_data(therm_file, tran_file, species_list):
  """Fail if required species lack thermochemistry or transport records.

  Require four-line thermochemistry records and seven-field transport records.
  Numerical and physical validation remains in the independent validators.
  """
  required_species = {species.upper() for species in species_list}
  _, therm_records = process_therm(therm_file, sorted(required_species))
  incomplete_therm = sorted(
      name for name, record in therm_records.items()
      if any(len(line.split("!", 1)[0].rstrip()) < 80 or
             line[79] != str(index) or not line[:75].strip()
             for index, line in enumerate(record[1:], start=2)))
  transport_species = set()
  incomplete_transport = set()
  with open(tran_file, encoding="utf-8") as transport:
    for line in transport:
      fields = line.split("!", 1)[0].split()
      if fields and fields[0].upper() not in {"TRANSPORT", "END"}:
        name = fields[0].upper()
        transport_species.add(name)
        if name in required_species and len(fields) != 7:
          incomplete_transport.add(name)

  errors = []
  for label, source, available in (
      ("thermochemistry", therm_file, therm_records),
      ("transport", tran_file, transport_species)):
    absent = sorted(required_species - set(available))
    if absent:
      errors.append("missing " + label + " records in '" + str(source) +
                    "': " + ", ".join(absent))
  for label, source, incomplete in (
      ("thermochemistry", therm_file, incomplete_therm),
      ("transport", tran_file, sorted(incomplete_transport))):
    if incomplete:
      errors.append("incomplete " + label + " records in '" + str(source) +
                    "': " + ", ".join(incomplete))
  if errors:
    _raise_user_input_error("\n".join(errors))


def print_not_found(what, dir_or_file, path):
  print(what + " " + dir_or_file + " '" + path + "' does not exist")


def print_error(msg):
  print("\n#error: " + msg)


def _raise_user_input_error(msg):
  """Raise the compiler's user-input error without an import-time cycle."""
  if __package__ and "." in __package__:
    from .. import c3mech_data as c3mech
  else:
    import c3mech_data as c3mech
  raise c3mech.UserInputError(msg)


def read_yaml_input(filename):
  """ returns a SubModulesFiles """
  yaml_input_options = None
  with open(filename, encoding="utf-8") as inp:
    try:
      yaml_input_options = yaml.load(inp, Loader=SubModulesLoader)
    except yaml.YAMLError as exc:
      _raise_user_input_error("invalid syntax in yaml input '" + filename +
                              "'")
  if yaml_input_options is None:
    _raise_user_input_error("yaml input '" + filename + "' is empty")
  return yaml_input_options


def make_submodulefiles_from_yaml(filename, directory):
  """ 
      This routine returns a checked SubModulesFiles object if successful.
      Note: the routine may quit the script. 
  """
  if (not os.path.isfile(filename)):
    _raise_user_input_error("yaml input file does not exist: '" + filename +
                            "'")
  print("reading yaml file \'" + os.path.basename(filename) + "'")
  submodules = read_yaml_input(filename)

  if not isinstance(submodules, SubModulesFiles):
    _raise_user_input_error("invalid yaml input in '" + filename +
                            "': expected top-level tag '!SubModulesFiles'")

  allowed_yaml_keys = {"core", "submodules"}
  yaml_keys = set(vars(submodules).keys())
  unknown_yaml_keys = sorted(yaml_keys - allowed_yaml_keys)
  if unknown_yaml_keys:
    _raise_user_input_error("unknown key(s) in yaml input '" + filename +
                            "': " + ", ".join(unknown_yaml_keys))

  missing_yaml_keys = sorted(allowed_yaml_keys - yaml_keys)
  if missing_yaml_keys:
    _raise_user_input_error("missing required key(s) in yaml input '" +
                            filename + "': " + ", ".join(missing_yaml_keys))

  if not isinstance(submodules.core, str) or submodules.core.strip() == "":
    _raise_user_input_error("invalid yaml input in '" + filename +
                            "': key 'core' must be a non-empty string")

  if not isinstance(submodules.submodules, list):
    _raise_user_input_error("invalid yaml input in '" + filename +
                            "': key 'submodules' must be a list")
  for idx, item in enumerate(submodules.submodules):
    if not isinstance(item, str) or item.strip() == "":
      _raise_user_input_error(
          "invalid yaml input in '" + filename +
          "': key 'submodules' must contain non-empty strings (index " +
          str(idx) + ")")

  submodules.insert_model_path(directory)

  if (not submodules.check()):
    _raise_user_input_error("invalid sub-module paths in yaml input '" +
                            filename + "'")

  return submodules


class SubModulesLoader(yaml.SafeLoader):
  """Keep the compiler selection constructor local to this module."""


class SubModulesFiles(yaml.YAMLObject):
  yaml_loader = SubModulesLoader
  yaml_tag = u'!SubModulesFiles'

  def __init__(self, core, submodules):
    self.core = os.path.normcase(os.path.normpath(
        copy.copy(core))) if core is not None else ""
    if submodules is None:
      self.submodules = []
    else:
      self.submodules = copy.copy(
          [os.path.normcase(os.path.normpath(f)) for f in submodules])

  def check(self):
    ok = True
    if (not os.path.isfile(self.core)):
      print_not_found("coremech", "file", self.core)
      ok = False
    for filename in self.submodules:
      if (not os.path.isfile(filename)):
        print_not_found("submodules", "file", filename)
        ok = False
    return ok

  def insert_model_path(self, directory):
    self.core = os.path.join(directory, self.core)
    if self.submodules:
      self.submodules = [os.path.join(directory, f) for f in self.submodules]
    else:
      self.submodules = []

  def get_files(self):
    return [self.core] + self.submodules


def remove_trailing_numbers(line):
  # Use regex to find trailing numbers (positive or negative integers, floats, or scientific notation)
  # The pattern looks for three groups of numbers separated by spaces at the end of the line

  # Function to check if a string can be parsed as a float
  def is_float(value):
    try:
      float(value)
      return True
    except ValueError:
      return False

  # Remove last number and check
  match = re.search(r'\s+[+-]?((\d+\.\d*)|(\.\d+)|(\d+))([eE][+-]?\d+)?\s*$',
                    line)
  if match:
    last_number = match.group().strip()
    if not is_float(last_number):
      raise ValueError(f"Invalid trailing number: {last_number}")
    modified_line = line[:match.start()].rstrip(
    )  # Keep everything before the matched part
  else:
    raise Exception(
        "Could not find the first floating point number (reading right to left, this is the activation energy) in '"
        + line + "'")

  # Remove second last number and check
  match = re.search(r'\s+[+-]?((\d+\.\d*)|(\.\d+)|(\d+))([eE][+-]?\d+)?\s*$',
                    modified_line)
  if match:
    second_last_number = match.group().strip()
    if not is_float(second_last_number):
      raise ValueError(f"Invalid trailing number: {second_last_number}")
    modified_line = modified_line[:match.start()].rstrip()
  else:
    raise Exception(
        "Could not find the second floating point number (pre-exponential factor) in '"
        + line + "'")

  # Remove third last number and check
  match = re.search(r'\s+[+-]?((\d+\.\d*)|(\.\d+)|(\d+))([eE][+-]?\d+)?\s*$',
                    modified_line)
  if match:
    third_last_number = match.group().strip()
    if not is_float(third_last_number):
      raise ValueError(f"Invalid trailing number: {third_last_number}")
    modified_line = modified_line[:match.start()].rstrip()
  else:
    raise Exception(
        "Could not find the third floating point number (reading right to left, this is the frequency factor) in '"
        + line + "'")

  return modified_line.rstrip(
  )  # Return the cleaned line without leading/trailing whitespace


def convert_to_float_or_int(value):
  # Convert to float first
  float_value = float(value)

  # Check if the float value is close enough to an integer
  if abs(float_value - round(float_value)) < 1e-10:  # Tolerance level of 1e-10
    return str(int(round(float_value)))  # Return as int

  return f"{float_value:.6f}"  # Return as float


def _process_reaction_line(submodule_filename, line, line_orig, species_dict,
                           new_canon_str, normalized_reactions,
                           normalized_reactions_check, total_species,
                           total_reactions):
  """
    Handles the logic for lines that contain a reaction definition (i.e., 
    lines that contain '=').
    Extracts the reaction, updates species and reaction dictionaries.
    """

  reaction = rxn.ChemicalReaction(line, line_orig, species_dict)
  reaction.set_submodule_file(submodule_filename)

  n_spec = 0
  # Insert species from reactants/products into species_dict and total_species
  for coeff, spc in (reaction.reactants + reaction.products):
    total_species.add(spc)
    # If species is not yet used, set to 1
    if species_dict.get(spc, 0) == 0:
      species_dict[spc] = 1
      n_spec += 1

  # Get canonical representation
  canon_str, canon_check = reaction.canonical_representation()

  # add sub-module file to the canon_str
  if canon_str not in new_canon_str:
    new_canon_str.add(canon_str)
    if canon_str in normalized_reactions:
      prev = normalized_reactions[canon_str][-1].get_submodule_file()
      print("canonical string '" + canon_str +
            "' found in previous sub-module file '" + prev +
            "'. Current reaction '" + reaction.reaction_definition + "'")

  # Update normalized_reactions
  if canon_str not in normalized_reactions:
    normalized_reactions[canon_str] = []
  normalized_reactions[canon_str].append(reaction)

  total_reactions.add(canon_str)

  # Update normalized_reactions_check
  if canon_check in normalized_reactions_check:
    # Optional logic verifying if the newly added reaction conflicts, etc.
    # Keep first instance as reference for stable canonical checks.
    pass
  else:
    normalized_reactions_check[canon_check] = (canon_str, reaction)

  return canon_str, n_spec


def _handle_rev_keyword(line, match, species_dict, new_canon_str,
                        normalized_reactions, normalized_reactions_check,
                        total_reactions, last_canon_str, cantera_count):
  """
    Processes a line that has 'REV /.../' 
    """
  if not last_canon_str or last_canon_str not in normalized_reactions:
    raise Exception(f"Encountered a REV line with no preceding reaction. "
                    f"Line causing error: '{line}'")

  old_reaction_list = normalized_reactions[last_canon_str]
  if not old_reaction_list:
    raise Exception(
        f"Encountered a REV line but look up of the canonical reaction string '"
        + last_canon_str + "' failed" + f"Line causing error: '{line}'")

  # Grab the last reaction from that list
  old_reaction = copy.copy(old_reaction_list[-1])
  if old_reaction.reaction_type == "irreversible":
    raise Exception(
        f"REV keyword incompatible with irreversible reaction in '{line}'")

  # Remove the old reaction from the dictionary
  old_reaction_list.pop()
  if not old_reaction_list:
    del normalized_reactions[last_canon_str]
    new_canon_str.remove(last_canon_str)
    total_reactions.discard(last_canon_str)

  # Make the existing reaction 'irreversible' and re-store it under its new canonical string
  old_reaction.make_irreversible()
  canon_old, _ = old_reaction.canonical_representation()
  if canon_old not in normalized_reactions:
    normalized_reactions[canon_old] = []
    new_canon_str.add(canon_old)
  normalized_reactions[canon_old].append(old_reaction)
  total_reactions.add(canon_old)

  # Check for numeric data in REV line (e.g. Arrhenius parameters)
  numbers_part = match.group(1).strip()  # e.g., "1.0 2.0 3.0"
  number_strings = [num for num in numbers_part.split() if num]
  if not number_strings:
    raise ValueError("Syntax error in REV keyword (no numeric parameters): '" +
                     line + "'")
  if len(number_strings) != 3:
    raise ValueError(
        "Syntax error in REV keyword (expected exactly 3 numeric parameters): '"
        + line + "'")

  # Convert to float
  number_array = []
  for num_str in number_strings:
    try:
      number_array.append(float(num_str))  # Convert string to float
    except ValueError as exc:
      raise ValueError("Syntax error in REV keyword (invalid number '" +
                       num_str + "') in line: '" + line + "'") from exc

  # If the first number != 0, then add the reverse rate coefficient
  if number_array[0] != 0.0:
    cantera_count += 1
    new_reaction = copy.copy(old_reaction)
    new_reaction.invert()
    new_reaction.empty_chemkin = True
    canon_new, _ = new_reaction.canonical_representation()
    if canon_new not in normalized_reactions:
      normalized_reactions[canon_new] = []
      new_canon_str.add(canon_new)
    normalized_reactions[canon_new].append(new_reaction)
    total_reactions.add(canon_new)

  return cantera_count, canon_old


def _handle_unrecognized_line(line):
  """
    This is your fallback handling for lines that don't match any known pattern or mode.
    """
  raise ValueError(f"Unrecognized line: {line}")


def _process_special_keywords(line, patterns, species_dict, new_canon_str,
                              normalized_reactions, normalized_reactions_check,
                              total_reactions, last_canon_str, cantera_count):
  """
    Handles lines that might match special keywords, like REV, LOW, HIGH, TROE, etc.
    If the line is recognized, modifies the data structures accordingly. 
    """
  # Try each important pattern
  match_rev = patterns['rev'].match(line)
  if re.match(r'REV\b', line, re.IGNORECASE) and not match_rev:
    raise ValueError("Syntax error in REV keyword: '" + line + "'")
  if match_rev:
    cantera_count, last_canon_str = _handle_rev_keyword(
        line, match_rev, species_dict, new_canon_str, normalized_reactions,
        normalized_reactions_check, total_reactions, last_canon_str,
        cantera_count)
    return cantera_count, last_canon_str

  def _require_previous_reaction(keyword):
    if (not last_canon_str or last_canon_str not in normalized_reactions
        or len(normalized_reactions[last_canon_str]) == 0):
      raise ValueError("Syntax error: '" + keyword +
                       "' found without a preceding reaction in line '" + line +
                       "'")

  # If not REV, check the others in turn
  for key in [
      'low', 'high', 'troe', 'lowmx', 'highmx', 'troemx', 'lowsp', 'highsp',
      'troesp', 'plog', 'tcheb', 'pcheb', 'cheb'
  ]:
    if patterns[key].match(line):
      _require_previous_reaction(key.upper())
      # You might do special handling for each one if needed
      return cantera_count, last_canon_str

  # Maybe parse the unknown pattern.
  match_tb = patterns['tb'].findall(line)
  if match_tb:
    _require_previous_reaction("third-body efficiency")
    err = _handle_tb_pattern(match_tb, species_dict, normalized_reactions,
                             last_canon_str)
    if err:
      raise Exception(f"Error in TB pattern in '{line}'")
    return cantera_count, last_canon_str

  # If no recognized patterns matched, we handle as an unknown line.
  _handle_unrecognized_line(line)


def _handle_tb_pattern(matches_tb, species_dict, normalized_reactions,
                       last_canon_str):
  """
    Handles the third body pattern lines like "N2/ 1.0/"
    """
  error = False
  if (not last_canon_str or last_canon_str not in normalized_reactions
      or len(normalized_reactions[last_canon_str]) == 0):
    raise ValueError("Syntax error: third-body efficiency found without a "
                     "preceding reaction")
  for (species, value_str) in matches_tb:
    try:
      float_val = float(value_str)
    except ValueError:
      print(f"Error converting {value_str} to float in TB pattern.")
      error = True
      continue

    if species in species_dict:
      if species in normalized_reactions[last_canon_str][-1].tb_efficiencies:
        old_val = normalized_reactions[last_canon_str][-1].tb_efficiencies[
            species]
        print(
            f"Duplicate third body efficiencies for {species} ({value_str} and {old_val})"
        )
        error = True
        continue
      normalized_reactions[last_canon_str][-1].tb_efficiencies[
          species] = float_val
    else:
      print(f"Unknown keyword or species in TB pattern: {species}")
      error = True
  return error


def count_reactions(lines,
                    submodule_filename,
                    species_dict,
                    normalized_reactions,
                    normalized_reactions_check,
                    print_summary=True):
  """
  """

  # 1) Preprocess and store only the main content (strip comments, uppercase).
  cleaned_lines = [line.split('!', 1)[0].strip().upper() for line in lines]

  # 2) Counters and data structures.
  n_new_species = 0
  total_species = set()
  total_reactions = set()
  n_reactions_start = len(normalized_reactions)
  source_offset = 1 + max(
      (rr.source_order for group in normalized_reactions.values() for rr in group),
      default=-1)
  cantera_count = 0

  # 3) Compile regular expressions for clarity and easy maintenance.
  #    This dictionary approach keeps them organized in one place.
  patterns = {
      'rev': re.compile(r'REV\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'low': re.compile(r'LOW\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'lowmx': re.compile(r'LOWMX\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'lowsp': re.compile(r'LOWSP\s*/([^!]+)/', re.IGNORECASE),
      'high': re.compile(r'HIGH\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'highmx': re.compile(r'HIGHMX\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'highsp': re.compile(r'HIGHSP\s*/([^!]+)/', re.IGNORECASE),
      'troe': re.compile(r'TROE\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'troemx': re.compile(r'TROEMX\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'troesp': re.compile(r'TROESP\s*/([^!]+)/', re.IGNORECASE),
      'plog': re.compile(r'PLOG\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'tcheb': re.compile(r'TCHEB\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'pcheb': re.compile(r'PCHEB\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'cheb': re.compile(r'CHEB\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'tb': re.compile(r'([\w\-\(\),\#]+)\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'unknown': re.compile(r'([^\s]+)\s*/([^!]+)/', re.IGNORECASE),
      'dup': re.compile(r'(DUP|DUPLICATE)', re.IGNORECASE),
      'elem': re.compile(r'^(ELEM|ELEMENTS)\b', re.IGNORECASE),
      'spec': re.compile(r'^(SPEC|SPECIES)\b', re.IGNORECASE),
      'reac': re.compile(r'^(REAC|REACTIONS)\b', re.IGNORECASE),
      'end': re.compile(r'^END\b', re.IGNORECASE),
  }

  # Some mechanism files do not contain an explicit REACTIONS block marker.
  # In that case, we must keep the first comment block as intro for the first
  # reaction. If REACTIONS exists, only keep comments from within that block.
  has_reactions_marker = any(patterns['reac'].match(l) for l in cleaned_lines)

  element_mode = False
  species_mode = False
  reaction_mode = False
  last_canon_str = ""

  idx_line = -1
  intro = []

  new_canon_str = set()
  for l in cleaned_lines:
    idx_line += 1
    #print(lines[idx_line])

    if patterns['elem'].match(l):
      element_mode = True
      reaction_mode = False
      continue
    elif patterns['spec'].match(l):
      species_mode = True
      reaction_mode = False
      continue
    elif patterns['reac'].match(l):
      reaction_mode = True
      element_mode = False
      species_mode = False
      continue
    elif patterns['end'].match(l):
      element_mode = False
      reaction_mode = False
      species_mode = False
      last_canon_str = ""
      continue

    in_reaction_block = reaction_mode or (not has_reactions_marker
                                          and not element_mode
                                          and not species_mode)

    if (not "=" in l and last_canon_str == "" and not element_mode
        and not species_mode):
      if in_reaction_block:
        intro.append(lines[idx_line])

    if not "=" in l and last_canon_str != "" and in_reaction_block:
      if last_canon_str not in normalized_reactions:
        print(l)
      #print("")
      #print(idx_line)
      #print("appending: '" + lines[idx_line].strip() + "' to " + last_canon_str)
      #if n_new_species == 1 and len(normalized_reactions[last_canon_str]) == 1:
      normalized_reactions[last_canon_str][-1].add_reaction_info(
          lines[idx_line])

    if "=" in l:
      if not in_reaction_block:
        raise ValueError("reaction-like line outside active REACTIONS section: '"
                         + lines[idx_line].strip() + "'")
      cantera_count += 1

      last_canon_str, n_spec = _process_reaction_line(
          submodule_filename, l, lines[idx_line], species_dict, new_canon_str,
          normalized_reactions, normalized_reactions_check, total_species,
          total_reactions)

      normalized_reactions[last_canon_str][-1].source_order = source_offset + idx_line

      if n_new_species == 0:
        for intro_line in intro:
          normalized_reactions[last_canon_str][-1].add_intro(intro_line)
        intro = []

      n_new_species += n_spec
    elif patterns['unknown'].match(l):
      if not in_reaction_block:
        raise ValueError("keyword-style line outside active REACTIONS section: '"
                         + lines[idx_line].strip() + "'")
      # Step through relevant matches
      cantera_count, last_canon_str = _process_special_keywords(
          l, patterns, species_dict, new_canon_str, normalized_reactions,
          normalized_reactions_check, total_reactions, last_canon_str,
          cantera_count)
    elif patterns['dup'].match(l):
      if not in_reaction_block:
        raise ValueError("DUP/DUPLICATE outside active REACTIONS section: '" +
                         lines[idx_line].strip() + "'")
      pass
    elif element_mode:
      pass
    elif species_mode:
      pass
    else:
      if l == "":
        continue
      # If no recognized patterns matched, we handle as an unknown line.
      _handle_unrecognized_line(l)

  # for r in normalized_reactions:
  #   for rr in normalized_reactions[r]:
  #     print("\n\n\n")
  #     print(rr.pretty() + ":")
  #     for p_line in rr.get_orignal_CHEMKIN_text():
  #       print(p_line.strip())

  # print("setting '" + submodule_filename + "':")
  # for r in new_canon_str:
  #   for rr in normalized_reactions[r]:
  #     print(rr.reaction_definition)
  #     rr.set_submodule_file(submodule_filename)

  if print_summary:
    print("    new species in sub-module:", n_new_species)
    print("  total species in sub-module:", len(total_species))
    print("      reactions in sub-module:",
          len(normalized_reactions) - n_reactions_start)
  # print("total reactions in sub-module:", len(total_reactions))
  # print("number of reactions: ", len(normalized_reactions)-n_reactions_start)
  # print("number of ='s + number of REV's (cantera counting): ", cantera_count)
  return len(
      normalized_reactions
  ) - n_reactions_start, cantera_count, normalized_reactions, normalized_reactions_check, species_dict


def parse_reactions_file(file_path, species_list, print_summary=False):
  """Parse one CHEMKIN file into normalized reaction objects."""
  lines, _ = _read_text_lines(file_path)
  species_dict = {s: 0 for s in species_list}
  reactions, reactions_check = {}, {}
  count_reactions(lines,
                  os.path.basename(file_path),
                  species_dict,
                  reactions,
                  reactions_check,
                  print_summary=print_summary)
  return reactions
