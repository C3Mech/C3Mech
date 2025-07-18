#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import argparse
import datetime
import yaml
import copy

from shutil import copyfile

VERSION = "4.0"
DIR = os.path.dirname(os.path.abspath(__file__))
HEADER = "C3MechV4.0_header.txt"
YAML = "submodules.yaml"
OUTPUT = "output"
PRUNE = True
elements = {'C': 1, 'H': 1, 'F': 1, 'N': 1, 'O': 1, 'HE': 1, 'AR': 1}
pruned_comment = "! AUTOMATIC PRUNING ! "

def make_species_list(directory, files_list):
  # start reading from first "kinetic_module" you find
  species_list = []
  for file in files_list:
    print(f"reading '{os.path.basename(file)}'")
    with open(os.path.join(directory, file), encoding='cp1252') as ckiblock:
      check_rxns = 0
      for line in ckiblock:
        if '!\KINETICS_MODULE' in line:
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
          print("ERROR: in ", composition[c:])
          quit()
        if composition[c:c + 2] in cur_compo:
          print("ERROR: element", composition[c:c + 2],
                "cannot be specified twice")
          quit()
        cur_compo[composition[c:c + 2]] = int(n.group(1))
      else:
        print("current characters: '" + composition[c:c + 5] + "'")
        print("composition: '" + composition + "'")
        raise Exception("ERROR: unknown element '" + composition[c:c + 2] +
                        "'")
        quit()
    else:
      if composition[c:c + 1] in elements:
        n = re.match("[a-zA-Z]+\\s*(\\d+)", composition[c:c + 5])
        if not n:
          print("ERROR: in ", composition[c:])
          quit()
        if composition[c:c + 1] in cur_compo:
          print("ERROR: element", composition[c:c + 1],
                "cannot be specified twice")
        cur_compo[composition[c:c + 1]] = int(n.group(1))
      else:
        print("current characters: '" + composition[c:c + 5] + "'")
        print("composition: '" + composition + "'")
        raise Exception("ERROR: unknown element '" + composition[c:c + 1] +
                        "'")
        quit()
  if (count_nothing == 4):
    print("composition: '" + composition + "'")
    print("ERROR: empty composition")
    quit()
  return cur_compo


def write_species_list(species_list, species_pruned, filename):
  # write spc str
  commentstr = '\n!+++++++++++++++++++++ '
  speciesallstr = '\n!\SPECIES_MODULE: ALL '
  speciesendstr = '\n!\END_SPECIES_MODULE: ALL '
  allspcstr = '\n'
  count = 0
  spcsperline = 3
  for spc in species_list:
    if spc in species_pruned:
      continue
    count += 1
    allspcstr += spc
    allspcstr += ' ' * (30 - len(spc))
    if count % spcsperline == 0:
      allspcstr += '\n'

  if len(species_pruned):
    allspcstr += '\n' + pruned_comment
  count = 0
  for spc in species_pruned:
    count += 1
    allspcstr += spc
    allspcstr += ' ' * (30 - len(spc))
    if count % spcsperline == 0:
      allspcstr += '\n' + pruned_comment

  total_str = commentstr + speciesallstr + commentstr + allspcstr + commentstr + speciesendstr + commentstr
  if filename:
    with open(filename, "w") as spcfile:
      spcfile.write(total_str)
  return total_str


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
      if sp_name in species_dict and not species_dict[
          sp_name] and i + 3 < len(thermlines):
        species_composition[sp_name] = parse_composition(thermlines[i][24:44], elements)
        species_dict[sp_name] = 1
        species_output[sp_name] = [l for l in thermlines[i:i+4]]
  for s, v in species_dict.items():
    if v == 0:
      print('{0} : thermochemistry data not found...'.format(s))

  return species_composition, species_output

def clean_therm(therm_output, species_list, species_pruned, species_output, datetime):
  print("writing '" + therm_output + "'")
  with open(therm_output, 'w') as thermfile:

    thermfile.writelines(
        insert_boiler_plate("Thermodynamic", submodules_files, datetime))

    thermfile.write('THERMO ALL\n')
    thermfile.write('300.   1000.   5000.\n')

    for s in species_list:
      addition = ""
      if s in species_pruned:
        addition = pruned_comment

      thermfile.write(addition + species_output[s][0])
      thermfile.write(addition + species_output[s][1])
      thermfile.write(addition + species_output[s][2])
      thermfile.write(addition + species_output[s][3])

    thermfile.write('END\n')


def clean_tran(tran_file, tran_output, species_list, species_pruned, datetime):
  tran = open(tran_file, 'r', encoding="utf-8")
  tranlines = tran.readlines()
  tran.close()

  species_dict = {s.upper(): 0 for s in species_list}
  print("writing '" + tran_output + "'")
  with open(tran_output, 'w') as tranfile:
    tranfile.writelines(
        insert_boiler_plate("Transport", submodules_files, datetime))

    for i in range(len(tranlines)):
      wrk_line = tranlines[i].split("!")[0]
      wrk_line = wrk_line.rstrip()
      if wrk_line == '':
        continue
      sp_name = wrk_line.split()[0].upper()
      if sp_name in species_dict and not species_dict[sp_name]:
        species_dict[sp_name] = 1
        tran_component = tranlines[i].split()
        if ('!' in tranlines[i]):
          tranfile.write(
              '{0:18}    {1}    {2:8.2f}    {3:6.2f}    {4:6.2f}    {5:6.2f}    {6:6.2f}    {7}\n'
              .format(tran_component[0], tran_component[1],
                      float(tran_component[2]), float(tran_component[3]),
                      float(tran_component[4]), float(tran_component[5]),
                      float(tran_component[6]), ' '.join(tran_component[7:])))
        else:
          addition = ""
          if sp_name in species_pruned:
            addition = pruned_comment
          tranfile.write(addition +
              '{0:18}    {1}    {2:8.2f}    {3:6.2f}    {4:6.2f}    {5:6.2f}    {6:6.2f}\n'
              .format(tran_component[0], tran_component[1],
                      float(tran_component[2]), float(tran_component[3]),
                      float(tran_component[4]), float(tran_component[5]),
                      float(tran_component[6])))
        #tranfile.write('{0}\n'.format(tranlines[line].rstrip()))

    for s, v in species_dict.items():
      if v == 0:
        print('{0} : transport data not found...'.format(s))


def get_submodules_dir():
  return get_absolute_path(os.path.join("..", "SUBMODULES"))


def print_not_found(what, dir_or_file, path):
  print(what + " " + dir_or_file + " '" + path + "' does not exist")


def read_yaml_input(filename):
  """ returns a SubModulesFiles """
  yaml_input_options = None
  with open(filename) as inp:
    try:
      yaml_input_options = yaml.safe_load(inp)
    except ValueError as e:
      util.print_error("invalid syntax in yaml input '" + filename + "'")
  return yaml_input_options


def make_submodulefiles_from_yaml(filename, directory):
  """ 
      This routine returns a checked SubModulesFiles object if successful.
      Note: the routine may quit the script. 
  """
  if (not os.path.isfile(filename)):
    print_not_found("yaml input", "file", filename)
    quit()
  print("reading yaml file \'" + os.path.basename(filename) + "'")
  submodules = read_yaml_input(filename)
  submodules.insert_model_path(directory)

  if (not submodules.check()):
    print("error: invalid input")
    quit()

  return submodules


def get_species_list_submodule(yaml_filename):
  submodules_files = make_submodulefiles_from_yaml(yaml_filename,
                                                   get_submodules_dir())

  species_list = make_species_list('', submodules_files.get_files())

  species_dict = {k.upper(): 0 for k in species_list}
  for s in species_dict:
    species_dict[s] = 0
  return species_dict, submodules_files


class SubModulesFiles(yaml.YAMLObject):
  yaml_loader = yaml.SafeLoader
  yaml_tag = u'!SubModulesFiles'

  def __init__(self, core, submodules):
    self.core = copy.copy(core)
    self.submodules = copy.copy(submodules)
    if (submodules is None):
      self.submodules = []

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


def get_absolute_path(relative_path):

  # Merge the script directory with the relative path
  absolute_path = os.path.join(DIR, relative_path)

  return absolute_path


def insert_species_list(species_list, file_path, new_lines):
  with open(file_path, 'r') as file:
    lines = file.readlines()

  species_found = False
  end_found = False

  for line in lines:
    # Check for SPECIES keyword (case-insensitive)
    if line.strip().lower().startswith('species'):
      species_found = True
      new_lines.append(line)  # Copy the SPECIES line
      continue

    # If we have found SPECIES but not END yet, handle lines to replace
    if species_found and not end_found:
      if line.strip().lower().startswith('end'):
        end_found = True
        new_lines.append(species_list + "\n")  # Insert species_list before END
        new_lines.append(line)  # Copy the END line
        break

      # If we're in between SPECIES and END, skip these lines (to be replaced)
      continue

    # If we haven't found SPECIES or after END, copy other lines as is
    new_lines.append(line)

  return new_lines


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


class ChemicalReaction:

  def __init__(self, reaction_string, reaction_string_orig, species_dict):
    self.species_dict = species_dict
    self.reaction_string = reaction_string
    self.reaction_string_orig = reaction_string_orig
    self.empty_chemkin = False
    self.reaction_intro = []
    self.reaction_string_aux = []
    self.reaction_definition = ""
    self.inverted = False
    self.reactants = []
    self.products = []
    # A+Ar=B+Ar adds an explicit dependence on Ar
    self.explicit_dependence = set()
    self.tb_efficiencies = {}
    self.reaction_type = ""

    # Extract information from the provided reaction string
    self.extract_reaction(reaction_string)

  def __copy__(self):
    # Create a new ChemicalReaction object with copied attributes
    new_instance = ChemicalReaction(self.reaction_string, 
                                    self.reaction_string_orig, 
                                    self.species_dict)

    # Copy other attributes explicitly
    new_instance.inverted = self.inverted
    new_instance.reactants = copy.deepcopy(self.reactants)
    new_instance.products = copy.deepcopy(self.products)
    new_instance.reaction_type = copy.deepcopy(self.reaction_type)
    new_instance.reaction_string_orig = copy.deepcopy(self.reaction_string_orig)
    new_instance.reaction_string_aux = copy.deepcopy(self.reaction_string_aux)
    new_instance.reaction_intro = copy.deepcopy(self.reaction_intro)
    new_instance.explicit_dependence = copy.deepcopy(self.explicit_dependence)
    new_instance.empty_chemkin = self.empty_chemkin

    return new_instance

  def add_reaction_info(self, line):
    self.reaction_string_aux.append(line)

  def add_intro(self, line):
    self.reaction_intro.append(line)

  def with_rev_keyword(self):
    CHEMKIN_text = self.reaction_intro + [self.reaction_string_orig] + self.reaction_string_aux
    has_rev = False
    rev_match = re.compile(r'REV\s*/([-+\d\.eE\s]+)/', re.IGNORECASE)
    for test_line in CHEMKIN_text:
      if rev_match.match(test_line):
        has_rev = True
        break
    return has_rev

  def get_orignal_CHEMKIN_text(self):
    CHEMKIN_text = self.reaction_intro + [self.reaction_string_orig] + self.reaction_string_aux
    #has_rev = self.with_rev_keyword()

    #if has_rev:
    #  print("REV reaction:")
    #  for test_line in CHEMKIN_text:
    #    print(test_line.strip())
    if self.empty_chemkin:
      #print("return nothing!!")
      return [""]
    #elif has_rev:
    #  print("return full model")
    return CHEMKIN_text

  def make_irreversible(self):
    self.reaction_type = 'irreversible'

  def make_reversible(self):
    self.reaction_type = 'reversible'

  def invert(self):
    self.reactants, self.products = self.products, self.reactants
    self.inverted = not self.inverted

  def pretty(self):
    # Prepare reactant string without coefficients unless greater than one.
    reactant_parts = [
        f"{name}" if coef == 1.0 else f"{convert_to_float_or_int(coef)} {name}"
        for coef, name in sorted(self.reactants)
    ]

    # Prepare product string without coefficients unless greater than one.
    product_parts = [
        f"{name}" if coef == 1.0 else f"{convert_to_float_or_int(coef)} {name}"
        for coef, name in sorted(self.products)
    ]

    separator = " <=> " if self.reaction_type == 'reversible' else " => "

    return " + ".join(reactant_parts) + separator + " + ".join(product_parts)

  def extract_species(self, species_part):
    """Extracts species (reactants or products) from a given part of the reaction."""
    species = []
    species_2_idx = {}
    for species_str in species_part.split('+'):
      stripped_species = species_str.strip()
      if stripped_species:  # Only process non-empty strings
        match = re.match(r'^\s*([\d\.]+)?\s*([\w\-\(\),\#]+)\s*$',
                         stripped_species)
        if match:
          coefficient = match.group(1)
          name = match.group(2)
          if name in self.species_dict:
            stoichiometric_coefficient = float(
                coefficient) if coefficient else 1.0
            # this is wrong for A+A = B because A+A is not merged
            if name in species_2_idx:
              species[species_2_idx[name]][0] += stoichiometric_coefficient
            else:
              species_2_idx[name] = len(species)
              species.append([stoichiometric_coefficient, name])
          else:
            raise Exception("Invalid species: " + name + " in '" +
                            species_part + "'")
        else:
          raise Exception("Could not match the species regex with '" +
                          stripped_species + "'")

    return species

  def check_elem_conservation(self, species_compo_dict, tol=1.0e-3):
    def compute_elem(reac_prod):
      atoms = {}
      for nu, spc in reac_prod:
        #print(species_compo_dict[spc])
        for elem, count in species_compo_dict[spc].items():
          if elem not in atoms and count != 0.0:
            atoms[elem] = 0.0
          if count != 0.0:
            atoms[elem] += count*nu
      return atoms

    # Compute elemental compositions for reactants and products separately
    reac_atoms = compute_elem(self.reactants)
    prod_atoms = compute_elem(self.products)

    # Gather all elements appearing in either reactants or products
    all_elems = set(reac_atoms.keys()).union(prod_atoms.keys())
    
    # Compare element counts within the tolerance
    for elem in all_elems:
        reac_val = reac_atoms.get(elem, 0.0)
        prod_val = prod_atoms.get(elem, 0.0)
        if abs(reac_val - prod_val) > tol:
            # If difference is too large, print details and return True
            print(self.pretty() + ":")
            # Print sorted dictionaries by element name
            print("Reactants:", dict(sorted(reac_atoms.items())))
            print("Products:", dict(sorted(prod_atoms.items())))
            return True
    return False

  def extract_reaction(self, line):

    # Remove special species M
    line = remove_trailing_numbers(line.strip())
    self.reaction_definition = line
    line = re.sub(r'\s*\(\s*\+\s*M\s*\)\s*', '', line)  # Matches "(+ M)"
    line = re.sub(r'\s*\+\s*M\s*', '', line)  # Matches "+ M" or "+   M"
    line = re.sub(r'\s*\(\s*\+\s*([\w\-\(\),\#]+)\s*\)\s*', r'+\1',
                  line)  # Replace "(+N2)" with " + N2 "
    # Determine reaction type and split into reactants and products
    if '<=>' in line:
      self.reaction_type = 'reversible'
      reactants_part, products_part = line.split('<=>')
    elif '=>' in line:
      self.reaction_type = 'irreversible'
      reactants_part, products_part = line.split('=>')
    elif '=' in line:
      self.reaction_type = 'reversible'
      reactants_part, products_part = line.split('=')
    else:
      raise Exception("No valid separator found for the reaction.")
    # Extract reactants and products using the new subroutine
    self.reactants = self.extract_species(reactants_part)
    self.products = self.extract_species(products_part)
    for i_r in range(len(self.reactants)):
      nu_r, s_r = self.reactants[i_r]
      for i_p in range(len(self.products)):
        nu_p, s_p = self.products[i_p]
        if s_r == s_p:
          substract = min(nu_r, nu_p)
          self.reactants[i_r][0] -= substract
          self.products[i_p][0] -= substract
    
    pruned_reactants = []
    for reactant in self.reactants:
      if reactant[0] > 1.0e-10:
        pruned_reactants.append(reactant)
      else:
        self.explicit_dependence.add(reactant[1])
    self.reactants = pruned_reactants

    pruned_products = []
    for product in self.products:
      if product[0] > 1.0e-10:
        pruned_products.append(product)
      else:
        self.explicit_dependence.add(product[1])
    self.products = pruned_products


  def canonical_representation(self):
    """Generates a canonical representation of a chemical reaction."""
    # Sort reactants and products
    sorted_reactants = sorted(
        self.reactants, key=lambda x:
        (x[1], round(x[0], 10)))  # Sort by species name, then coefficient
    sorted_products = sorted(
        self.products, key=lambda x:
        (x[1], round(x[0], 10)))  # Sort by species name, then coefficient

    # Create canonical representations as strings
    reactant_str = '+'.join(f"{coef}{name}" for coef, name in sorted_reactants)
    product_str = '+'.join(f"{coef}{name}" for coef, name in sorted_products)

    if self.reaction_type == 'reversible':
      if reactant_str < product_str:
        return f"{reactant_str}={product_str}", f"{reactant_str}?{product_str}"
      else:
        return f"{product_str}={reactant_str}", f"{product_str}?{reactant_str}"
    elif self.reaction_type == 'irreversible':
      if reactant_str < product_str:
        return f"{reactant_str}=>{product_str}", f"{reactant_str}?{product_str}"
      else:
        return f"{reactant_str}=>{product_str}", f"{product_str}?{reactant_str}"
    else:
      raise Exception("reaction_type must be 'reversible' or 'irreversible'")

  def set_consumed(self, consumed, species2reaction, increment):
    affected = set()
    for nu, s in self.reactants:
      if s not in consumed:
        consumed[s] = 0
      consumed[s] += increment
      affected.add(s)
      #if increment < 0:
      #  print("deactivating consumption:", s, consumed[s])
      if increment > 0:
        if s not in species2reaction:
          species2reaction[s] = set()
        species2reaction[s].add(self.canonical_representation()[0])
    if self.reaction_type == 'reversible':
      for nu, s in self.products:
        if s not in consumed:
          consumed[s] = 0
        consumed[s] += increment
        affected.add(s)
        #if increment < 0:
        #  print("deactivating consumption:", s, consumed[s])
    if increment > 0:
      for nu, s in self.products:
        if s not in species2reaction:
          species2reaction[s] = set()
        species2reaction[s].add(self.canonical_representation()[0])
    return affected

  def set_produced(self, produced, species2reaction, increment):
    affected = set()
    for nu, s in self.products:
      if s not in produced:
        produced[s] = 0
      produced[s] += increment
      affected.add(s)
      #if increment < 0:
      #  print("deactivating production:", s, produced[s])
      if increment > 0:
        if s not in species2reaction:
          species2reaction[s] = set()
        species2reaction[s].add(self.canonical_representation()[0])
    if self.reaction_type == 'reversible':
      for nu, s in self.reactants:
        if s not in produced:
          produced[s] = 0
        produced[s] += increment
        affected.add(s)
        #if increment < 0:
        #  print("deactivating production:", s, produced[s])
    if increment > 0:
      for nu, s in self.products:
        if s not in species2reaction:
          species2reaction[s] = set()
        species2reaction[s].add(self.canonical_representation()[0])
    return affected

def _process_reaction_line(line, line_orig, species_dict, normalized_reactions,
                           normalized_reactions_check, total_species,
                           total_reactions):
  """
    Handles the logic for lines that contain a reaction definition (i.e., 
    lines that contain '=').
    Extracts the reaction, updates species and reaction dictionaries.
    """

  reaction = ChemicalReaction(line, line_orig, species_dict)

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


def _handle_rev_keyword(line, match, species_dict, normalized_reactions,
                        normalized_reactions_check, total_reactions,
                        last_canon_str, cantera_count):
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
  #print("stop")
  #quit()
  if old_reaction.reaction_type == "irreversible":
    raise Exception(
        f"REV keyword incompatible with irreversible reaction in '{line}'")

  # Remove the old reaction from the dictionary
  old_reaction_list.pop()
  if not old_reaction_list:
    del normalized_reactions[last_canon_str]
    total_reactions.discard(last_canon_str)

  # Make the existing reaction 'irreversible' and re-store it under its new canonical string
  old_reaction.make_irreversible()
  canon_old, _ = old_reaction.canonical_representation()
  if canon_old not in normalized_reactions:
    normalized_reactions[canon_old] = []
  normalized_reactions[canon_old].append(old_reaction)
  total_reactions.add(canon_old)

  # Check for numeric data in REV line (e.g. Arrhenius parameters)
  numbers_part = match.group(1).strip()  # e.g., "1.0 2.0 3.0"
  number_strings = [num for num in numbers_part.split() if num]

  # Convert to float and limit to up to three numbers
  number_array = []
  for num_str in number_strings[:3]:  # Limit to first three numbers only
    try:
      number_array.append(float(num_str))  # Convert string to float
    except ValueError:
      print(f"Could not convert '{num_str}' to float in REV //.")

  # If the first number != 0, then add the reverse rate coefficient
  if number_array[0] != 0.0:
    cantera_count += 1
    new_reaction = copy.copy(old_reaction)
    new_reaction.invert()
    new_reaction.empty_chemkin = True
    canon_new, _ = new_reaction.canonical_representation()
    if canon_new not in normalized_reactions:
      normalized_reactions[canon_new] = []
    normalized_reactions[canon_new].append(new_reaction)
    total_reactions.add(canon_new)

  return cantera_count, canon_old


def _handle_unrecognized_line(line):
  """
    This is your fallback handling for lines that don't match any known pattern or mode.
    """
  raise ValueError(f"Unrecognized line: {line}")


def _process_special_keywords(line, patterns, species_dict,
                              normalized_reactions, normalized_reactions_check,
                              total_reactions, last_canon_str, cantera_count):
  """
    Handles lines that might match special keywords, like REV, LOW, HIGH, TROE, etc.
    If the line is recognized, modifies the data structures accordingly. 
    """
  # Try each important pattern
  match_rev = patterns['rev'].match(line)
  if match_rev:
    cantera_count, last_canon_str = _handle_rev_keyword(line, match_rev, species_dict,
                                        normalized_reactions,
                                        normalized_reactions_check,
                                        total_reactions, last_canon_str,
                                        cantera_count)
    return cantera_count, last_canon_str

  # If not REV, check the others in turn
  for key in ['low', 'high', 'troe', 'plog', 'tcheb', 'pcheb', 'cheb']:
    if patterns[key].match(line):
      # You might do special handling for each one if needed
      return cantera_count, last_canon_str

  # Maybe parse the unknown pattern.
  match_tb = patterns['tb'].findall(line)
  if match_tb:
    err = _handle_tb_pattern(match_tb, species_dict, normalized_reactions, last_canon_str)
    if err:
      raise Exception(f"Error in TB pattern in '{line}'")
    return cantera_count, last_canon_str

  # If no recognized patterns matched, we handle as an unknown line.
  _handle_unrecognized_line(line)


def _handle_tb_pattern(matches_tb, species_dict, normalized_reactions, last_canon_str):
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
        old_val = normalized_reactions[last_canon_str][-1].tb_efficiencies[s]
        print(f"Duplicate third body efficiencies for {species} ({value_str} and {old_val})")
        error = True
        continue
      normalized_reactions[last_canon_str][-1].tb_efficiencies[species] = float_val
    else:
      print(f"Unknown keyword or species in TB pattern: {species}")
      error = True
  return error


def count_reactions(lines, species_dict, normalized_reactions,
                    normalized_reactions_check):
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
      'high': re.compile(r'HIGH\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'troe': re.compile(r'TROE\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'plog': re.compile(r'PLOG\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'tcheb': re.compile(r'TCHEB\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'pcheb': re.compile(r'PCHEB\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'cheb': re.compile(r'CHEB\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'tb': re.compile(r'([\w\-\(\),\#]+)\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'unknown': re.compile(r'([^\s]+)\s*/([-+\d\.eE\s]+)/', re.IGNORECASE),
      'dup': re.compile(r'(DUP|DUPLICATE)', re.IGNORECASE),
      'elem': re.compile(r'(ELEM|ELEMENTS)', re.IGNORECASE),
      'spec': re.compile(r'(SPEC|SPECIES)', re.IGNORECASE),
      'reac': re.compile(r'(REAC|REACTIONS)', re.IGNORECASE),
      'end': re.compile(r'(END)', re.IGNORECASE),
  }

  element_mode = False
  species_mode = False
  reaction_mode = False
  reaction_only = True
  last_canon_str = ""

  idx_line = -1
  intro = []
  for l in cleaned_lines:
    idx_line += 1
    #print(lines[idx_line])

    if l not in lines[idx_line].strip().upper():
      raise Exception("l = '" + l + "' line = '" + lines[idx_line].strip().upper()  + "'")

    if patterns['elem'].match(l):
      element_mode = True
      reaction_only = False
      continue
    elif patterns['spec'].match(l):
      species_mode = True
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

    if (reaction_mode or reaction_only) and not "=" in l and last_canon_str == "":
      intro.append(lines[idx_line])

    if not "=" in l and last_canon_str != "":
      if last_canon_str not in normalized_reactions:
        print(l)
      #print("")
      #print(idx_line)
      #print("appending: '" + lines[idx_line].strip() + "' to " + last_canon_str)
      #if n_new_species == 1 and len(normalized_reactions[last_canon_str]) == 1:
      normalized_reactions[last_canon_str][-1].add_reaction_info(lines[idx_line])

    if "=" in l:
      cantera_count += 1

      last_canon_str, n_spec = _process_reaction_line(
          l, lines[idx_line], species_dict, normalized_reactions, normalized_reactions_check,
          total_species, total_reactions)

      if n_new_species == 0 and len(normalized_reactions[last_canon_str]) == 1:
        for intro_line in intro:
          normalized_reactions[last_canon_str][-1].add_intro(intro_line)
        intro_line = []

      n_new_species += n_spec
    elif patterns['unknown'].match(l):
      # Step through relevant matches
      cantera_count, last_canon_str = _process_special_keywords(l, patterns, species_dict,
                                                normalized_reactions,
                                                normalized_reactions_check,
                                                total_reactions,
                                                last_canon_str, cantera_count)
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


def insert_header(lines):
  header_path = os.path.join(DIR, HEADER)
  with open(header_path, 'r') as f:
    for line in f:
      lines.append(line)
    lines.append("\n")
    lines.append("\n")


def insert_time(lines, filetype, datetime):
  lines.append('! ' + filetype + ' data for C3MechV' + VERSION +
               ', generated on {0:%d/%m/%Y %H:%M:%S}.\n'.format(datetime) +
               '\n')


def insert_submodule_list(lines, submodules_files):
  lines.append('! The following sub-modules were considered in this file:\n')
  lines.append('! - ' + os.path.basename(submodules_files.core) + '\n')
  for file_path in submodules_files.submodules:
    lines.append('! - ' + os.path.basename(file_path) + '\n')
  lines.append("\n")


def insert_boiler_plate(filetype, submodules_files, datetime):
  lines = []
  insert_header(lines)
  insert_time(lines, filetype, datetime)
  insert_submodule_list(lines, submodules_files)
  return lines

def print_kinetics_file(species_list, species_pruned, submodules_files, output_filename, 
                        datetime, reactions, reactions_pruned):
  species_section_str = write_species_list(species_list, species_pruned, '')
  new_lines = insert_boiler_plate("Kinetics", submodules_files, datetime)
  n_species = len(species_list)
  # no pruned species (my be empty)
  n_species -= len(species_pruned)
  new_lines.append("! number of species: " + str(n_species) + "\n")
  new_lines.append("! number of species: " + str(n_species) + "\n")
  insert_reaction_count = len(new_lines)

  new_lines = insert_species_list(species_section_str, submodules_files.core, new_lines)

  new_lines.append("REACTIONS\n")
  n_reaction = len(reactions)
  n_reaction -= len(reactions_pruned)

  #this does not account for pruning
  # new_lines.insert(
  #    insert_reaction_count + 1, "! number of reactions: " +
  #    str(cantera_count) + " (number of reactions given by cantera)\n\n")


  for r in reactions:
    for rr in reactions[r]:
      #print("\n\n\n")
      #print(rr.pretty() + ":")
      for p_line in rr.get_orignal_CHEMKIN_text():
        if r in reactions_pruned and p_line != "":
          new_lines.append(pruned_comment + p_line)
        else:
          new_lines.append(p_line)

  new_lines.append("END\n\n")
  
  print("writing '" + output_filename + "'")
  with open(output_filename, 'w', encoding="utf-8") as file:
    file.writelines(new_lines)

def merge_models(species_list, submodules_files):

  species_dict = {s: 0 for s in species_list}
  for s in species_dict:
    if "+" in s:
      raise Exception("species name '" + s + "' contains a +")

    match = re.match(r'^[\w\-\(\),\#]+$', s)
    if not match:
      raise Exception("species name '" + s +
                      "' does not match the species pattern")


  print("processing: '" + os.path.basename(submodules_files.core) + "'")

  with open(submodules_files.core, 'r') as file:
    lines = file.readlines()
  normalized_reactions, normalized_reactions_check = {}, {}
  n_reaction, cantera_count, normalized_reactions, normalized_reactions_check, species_dict = count_reactions(
      lines, species_dict, normalized_reactions, normalized_reactions_check)

  #base_names = sorted([os.path.basename(file_path) for file_path in submodules_files.submodules])
  aux_path = {
      os.path.basename(file_path): file_path
      for file_path in submodules_files.submodules
  }
  for base_name in aux_path:
    file_path = aux_path[base_name]
    print("processing: '" + base_name + "'")
    with open(file_path, 'r') as file:
      lines = file.readlines()
      n_reaction_i, cantera_count_i, normalized_reactions, normalized_reactions_check, species_dict = count_reactions(
          lines, species_dict, normalized_reactions,
          normalized_reactions_check)
      n_reaction += n_reaction_i
      cantera_count += cantera_count_i

  print_reactions = False
  if print_reactions:
    print("reactions:")
    for r in normalized_reactions:
      for rr in normalized_reactions[r]:
        print(count, rr.pretty())

  insert_species = set()
  for s, val in species_dict.items():
    if val == 0:
      insert_species.add(s)
  if len(insert_species):
    print(len(insert_species), "inert species:")
    for s in insert_species:
      print(s)

  print("merged model contains " + str(len(species_list)) + " species and " +
        str(cantera_count) + " (cantera count) / " +
        str(len(normalized_reactions)) + " (normal count) reactions")

  return normalized_reactions

def get_cons_prod_counter(reactions, increment):
    consumed = {}
    produced = {}
    species2reaction = {}
    for r in reactions:
      for rr in reactions[r]:
        rr.set_consumed(consumed, species2reaction, increment)
        rr.set_produced(produced, species2reaction, increment)
    return consumed, produced, species2reaction

def prune_model(reactions):
  never_consumed = set()
  never_produced = set()
  count = 1
  consumed, produced, species2reaction = get_cons_prod_counter(reactions, 1)
  removed_reaction = set()
  active_species = set([s for s in species2reaction])
  if PRUNE:
    print("start pruning...")
  while PRUNE:
    print("round " + str(count) + " with " + str(len(active_species)) + " species")
    #if len(active_species) < 100:
    #  print("active_species:", active_species)
    new_never_consumed = set()
    new_never_produced = set()

    for s in active_species:
      if s not in consumed and s in produced and s not in never_consumed:
        new_never_consumed.add(s)
      if s not in produced and s in consumed and s not in never_produced:
        new_never_produced.add(s)

    remove_species = new_never_consumed.union(new_never_produced)
    #print("remove_species:", remove_species)
    active_species = set()
    for s in remove_species:
      for r in species2reaction[s]:
        if r in removed_reaction:
          continue
        removed_reaction.add(r)
        for rr in reactions[r]:

          affected = rr.set_consumed(consumed, species2reaction, -1)
          for s_remove in affected:
            if abs(consumed[s_remove]) < 1.0e-5:
              del consumed[s_remove]
              if s_remove not in remove_species:
                #print("new removal (previously consumed):", s_remove)
                active_species.add(s_remove)

          affected = rr.set_produced(produced, species2reaction, -1)
          for s_remove in affected:
            if abs(produced[s_remove]) < 1.0e-5:
              del produced[s_remove]
              if s_remove not in remove_species:
                #print("new removal (previously produced):", s_remove)
                active_species.add(s_remove)
          #print("removing:", rr.pretty())
        
    never_consumed = never_consumed.union(new_never_consumed)
    never_produced = never_produced.union(new_never_produced)

    # debug code
    for s, v in consumed.items():
      if v <= 0.00001:
        raise Exception("consumed is " + str(v) + " for " + s)
    for s, v in produced.items():
      if v <= 0.00001:
        raise Exception("produced is " + str(v) + " for " + s)
    count += 1

    if len(new_never_consumed) == 0 and len(new_never_produced) == 0:
      print("identified species and reactions to prune")
      break
  
  return never_consumed, never_produced, removed_reaction

if __name__ == "__main__":

  print("read input...")
  DATETIME = datetime.datetime.now()
  yaml_file_path = os.path.join(DIR, YAML)
  species_list, submodules_files = get_species_list_submodule(yaml_file_path)
  print("\nprocess input...")
  reactions = merge_models(species_list, submodules_files)

  therm_input = os.path.join(get_submodules_dir(), "SOURCE-C3Mech.THERM")
  species_compo_dict, species_nasa_output = process_therm(therm_input, species_list)

  for r in reactions:
    for rr in reactions[r]:
      rr.check_elem_conservation(species_compo_dict)

  never_consumed, never_produced, removed_reaction = prune_model(reactions)
  if len(never_consumed) or len(never_produced):
    print("\n")
  if len(never_consumed):
    print("\n")
    print(len(never_consumed), "species are produced but never consumed:")
    for s in never_consumed:
      print(s)
  if len(never_produced):
    print("\n")
    print(len(never_produced), "species are consumed but never produced:")
    for s in never_produced:
      print(s)

  count = 1
  if len(removed_reaction):
    print("\n")
    print(len(removed_reaction), "pruned reactions:")
    for r in removed_reaction:
      for rr in reactions[r]:
        print(f"{rr.reaction_definition}")
        count += 1
    print("\n")

  print("\ngenerate output...")
  species_pruned = never_consumed.union(never_produced)
  output_filename = os.path.join(DIR, OUTPUT, "C3Mech.CKI") 
  print_kinetics_file(species_list, species_pruned, 
                      submodules_files, output_filename, DATETIME, 
                      reactions, removed_reaction)
  clean_therm(os.path.join(DIR, OUTPUT, "C3Mech.THERM"), species_list, species_pruned, species_nasa_output, DATETIME)
  trans_input = os.path.join(get_submodules_dir(), "SOURCE-C3Mech.TRAN")
  clean_tran(trans_input, os.path.join(DIR, OUTPUT, "C3Mech.TRAN"),
             species_list, species_pruned, DATETIME)
