import os
import sys
import yaml
import re
import copy

from . import reaction as rxn

elements = {'C': 1, 'H': 1, 'F': 1, 'N': 1, 'O': 1, 'HE': 1, 'AR': 1}


def make_species_list(directory, files_list):
  # start reading from first "kinetic_module" you find
  species_list = []
  for file in files_list:
    print(f"reading '{os.path.basename(file)}'")
    with open(os.path.join(directory, file), encoding='cp1252') as ckiblock:
      check_rxns = 0
      for line in ckiblock:
        if '!\\KINETICS_MODULE' in line:
          check_rxns = 1
        lineunc = line.split('!')[0].strip()
        if len(lineunc) > 0:
          if check_rxns == 1:
            # check different types of separators hierarchically
            sep = ''
            if '<=>' in lineunc:
              sep = '<=>'
            elif '=>' in lineunc:
              sep = '=>'
            elif '=' in lineunc:
              sep = '='

            if sep != '':
              rcts_rough, prds_rough = lineunc.split(sep)
              rcts = rcts_rough.strip().split('(+M)')[0].split('+')
              # hopefully reactants is enough
              prds = prds_rough.strip().split('(+M)')[0].split('+')
              spcs = rcts + prds
              #print(spcs)
              # species may contain spaces for how they were derived: remove
              for spc in spcs:
                spc_clean = spc.strip()
                if spc_clean[0] == '2':  # few reactants written as 2A = B
                  spc_clean = spc_clean[1:]
                # check it is actually a species
                if len(spc_clean.split()) > 1:
                  spc_clean = spc_clean.split(
                  )[0]  # only possible species is the first one - in case it is a float, it won't be included

                if spc_clean[0] in [
                    '0', '1', '3', '4', '5', '6', '7', '8', '9', '.'
                ]:
                  continue
                try:
                  float(spc_clean)  # try to convert to float after splitting
                except ValueError:
                  # if unclosed bracket: residue from a (+M) written with spaces perhaps
                  if spc_clean[-1] == '(':
                    spc_clean = spc_clean.split('(')[0]
                  elif spc_clean[-1] == ')' and '(' not in spc_clean:
                    spc_clean = spc_clean.split(')')[0]

                  if spc_clean not in species_list and spc_clean != 'M':
                    # print(spc_clean)
                    species_list.append(spc_clean)

  mandatory = ['HE', 'N2', 'AR', 'C2H6', 'CO2', 'CH4']
  for m in mandatory:
    if m not in species_list:
      species_list.insert(0, m)

  return species_list


def parse_composition(composition, elements):
  def fail(msg):
    raise ValueError(msg + " (composition: '" + composition + "')")

  cur_compo = {}
  count_nothing = 0
  for i in range(4):
    c = i * 5
    if re.match("[\\s0]+", composition[c:c + 5]):
      count_nothing += 1
    elif composition[c + 1] != ' ':
      if composition[c:c + 2] in elements:
        n = re.match("[a-zA-Z]+\\s*(\\d+)", composition[c:c + 5])
        if not n:
          fail("ERROR: malformed element/count near '" + composition[c:] + "'")
        if composition[c:c + 2] in cur_compo:
          fail("ERROR: element '" + composition[c:c + 2] +
               "' cannot be specified twice")
        cur_compo[composition[c:c + 2]] = int(n.group(1))
      else:
        print("current characters: '" + composition[c:c + 5] + "'")
        print("composition: '" + composition + "'")
        fail("ERROR: unknown element '" + composition[c:c + 2] + "'")
    else:
      if composition[c:c + 1] in elements:
        n = re.match("[a-zA-Z]+\\s*(\\d+)", composition[c:c + 5])
        if not n:
          fail("ERROR: malformed element/count near '" + composition[c:] + "'")
        if composition[c:c + 1] in cur_compo:
          fail("ERROR: element '" + composition[c:c + 1] +
               "' cannot be specified twice")
        cur_compo[composition[c:c + 1]] = int(n.group(1))
      else:
        print("current characters: '" + composition[c:c + 5] + "'")
        print("composition: '" + composition + "'")
        fail("ERROR: unknown element '" + composition[c:c + 1] + "'")
  if (count_nothing == 4):
    fail("ERROR: empty composition")
  return cur_compo


def process_therm(therm_file, species_list):
  therm = open(therm_file, 'r', encoding="utf-8")
  thermlines = therm.readlines()
  therm.close()

  species_composition = {}
  species_output = {}

  species_dict = {s.upper(): 0 for s in species_list}

  for i in range(len(thermlines)):
    wrk_line = thermlines[i].split("!")[0]
    wrk_line = wrk_line.rstrip()
    if len(wrk_line) >= 80 and wrk_line[79] == '1':
      sp_name = wrk_line[0:25].split()[0].upper()
      if sp_name in species_dict and not species_dict[sp_name] and i + 3 < len(
          thermlines):
        species_composition[sp_name] = parse_composition(
            thermlines[i][24:44], elements)
        species_dict[sp_name] = 1
        species_output[sp_name] = [l for l in thermlines[i:i + 4]]
  for s, v in species_dict.items():
    if v == 0:
      print('{0} : thermochemistry data not found...'.format(s))

  return species_composition, species_output


def print_not_found(what, dir_or_file, path):
  print(what + " " + dir_or_file + " '" + path + "' does not exist")


def print_error(msg):
  print("\n#error: " + msg)


def read_yaml_input(filename):
  """ returns a SubModulesFiles """
  yaml_input_options = None
  with open(filename, encoding="utf-8") as inp:
    try:
      yaml_input_options = yaml.safe_load(inp)
    except yaml.YAMLError as exc:
      raise ValueError("invalid syntax in yaml input '" + filename + "'") from exc
  if yaml_input_options is None:
    raise ValueError("yaml input '" + filename + "' is empty")
  return yaml_input_options


def make_submodulefiles_from_yaml(filename, directory):
  """ 
      This routine returns a checked SubModulesFiles object if successful.
      Note: the routine may quit the script. 
  """
  if (not os.path.isfile(filename)):
    print_not_found("yaml input", "file", filename)
    sys.exit(1)
  print("reading yaml file \'" + os.path.basename(filename) + "'")
  try:
    submodules = read_yaml_input(filename)
  except ValueError as exc:
    print_error(str(exc))
    sys.exit(1)

  if not isinstance(submodules, SubModulesFiles):
    print_error("invalid yaml input in '" + filename +
                "': expected top-level tag '!SubModulesFiles'")
    sys.exit(1)

  submodules.insert_model_path(directory)

  if (not submodules.check()):
    print("error: invalid input")
    sys.exit(1)

  return submodules


class SubModulesFiles(yaml.YAMLObject):
  yaml_loader = yaml.SafeLoader
  yaml_tag = u'!SubModulesFiles'

  def __init__(self, core, submodules):
    self.core = os.path.normcase(os.path.normpath(copy.copy(core))) if core is not None else ""
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
    # For clarity, this is left mostly as the original logic
    _, old_reaction = normalized_reactions_check[canon_check]
    # You might handle conflicts or duplicates here
    if False and ('irreversible' != reaction.reaction_type
                  or 'irreversible' != old_reaction.reaction_type):
      print("#warning: found '" + last_canon_str + "' and '" +
            old_reaction.canonical_representation()[0] + "'")
      print("reaction string 1:", old_reaction.reaction_definition)
      print("reaction string 2:", reaction.reaction_definition)
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

  # Convert to float and limit to up to three numbers
  number_array = []
  for num_str in number_strings[:3]:  # Limit to first three numbers only
    try:
      number_array.append(float(num_str))  # Convert string to float
    except ValueError as exc:
      raise ValueError("Syntax error in REV keyword (invalid number '" +
                       num_str + "') in line: '" + line + "'") from exc

  if not number_array:
    raise ValueError("Syntax error in REV keyword (no valid numeric parameter): '"
                     + line + "'")

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

  # If not REV, check the others in turn
  for key in [
      'low', 'high', 'troe', 'lowmx', 'highmx', 'troemx', 'lowsp', 'highsp',
      'troesp', 'plog', 'tcheb', 'pcheb', 'cheb'
  ]:
    if patterns[key].match(line):
      # You might do special handling for each one if needed
      return cantera_count, last_canon_str

  # Maybe parse the unknown pattern.
  match_tb = patterns['tb'].findall(line)
  if match_tb:
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


def count_reactions(lines, submodule_filename, species_dict,
                    normalized_reactions, normalized_reactions_check):
  """
  """

  # 1) Preprocess and store only the main content (strip comments, uppercase).
  cleaned_lines = [line.split('!', 1)[0].strip().upper() for line in lines]

  # 2) Counters and data structures.
  n_new_species = 0
  total_species = set()
  total_reactions = set()
  n_reactions_start = len(normalized_reactions)
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
      'elem': re.compile(r'(ELEM|ELEMENTS)', re.IGNORECASE),
      'spec': re.compile(r'(SPEC|SPECIES)', re.IGNORECASE),
      'reac': re.compile(r'(REAC|REACTIONS)', re.IGNORECASE),
      'end': re.compile(r'(END)', re.IGNORECASE),
  }

  # Some mechanism files do not contain an explicit REACTIONS block marker.
  # In that case, we must keep the first comment block as intro for the first
  # reaction. If REACTIONS exists, only keep comments from within that block.
  has_reactions_marker = any(patterns['reac'].match(l) for l in cleaned_lines)

  element_mode = False
  species_mode = False
  reaction_mode = False
  reaction_only = True
  last_canon_str = ""

  idx_line = -1
  intro = []

  new_canon_str = set()
  for l in cleaned_lines:
    idx_line += 1
    #print(lines[idx_line])

    if l not in lines[idx_line].strip().upper():
      raise Exception("l = '" + l + "' line = '" +
                      lines[idx_line].strip().upper() + "'")

    if patterns['elem'].match(l):
      element_mode = True
      if has_reactions_marker:
        reaction_only = False
      continue
    elif patterns['spec'].match(l):
      species_mode = True
      if has_reactions_marker:
        reaction_only = False
      continue
    elif patterns['reac'].match(l):
      reaction_mode = True
      continue
    elif patterns['end'].match(l):
      element_mode = False
      reaction_mode = False
      species_mode = False
      continue

    if (not "=" in l and last_canon_str == "" and not element_mode
        and not species_mode):
      if reaction_mode or (reaction_only and not has_reactions_marker):
        intro.append(lines[idx_line])

    if not "=" in l and last_canon_str != "":
      if last_canon_str not in normalized_reactions:
        print(l)
      #print("")
      #print(idx_line)
      #print("appending: '" + lines[idx_line].strip() + "' to " + last_canon_str)
      #if n_new_species == 1 and len(normalized_reactions[last_canon_str]) == 1:
      normalized_reactions[last_canon_str][-1].add_reaction_info(
          lines[idx_line])

    if "=" in l:
      cantera_count += 1

      last_canon_str, n_spec = _process_reaction_line(
          submodule_filename, l, lines[idx_line], species_dict, new_canon_str,
          normalized_reactions, normalized_reactions_check, total_species,
          total_reactions)

      if n_new_species == 0:
        for intro_line in intro:
          normalized_reactions[last_canon_str][-1].add_intro(intro_line)
        intro = []

      n_new_species += n_spec
    elif patterns['unknown'].match(l):
      # Step through relevant matches
      cantera_count, last_canon_str = _process_special_keywords(
          l, patterns, species_dict, new_canon_str, normalized_reactions,
          normalized_reactions_check, total_reactions, last_canon_str,
          cantera_count)
    elif patterns['dup'].match(l):
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
