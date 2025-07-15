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


def write_species_list(species_list, filename):
  # write spc str
  commentstr = '\n!+++++++++++++++++++++ '
  speciesallstr = '\n!\SPECIES_MODULE: ALL '
  speciesendstr = '\n!\END_SPECIES_MODULE: ALL '
  allspcstr = '\n'
  count = 0
  spcsperline = 3
  for spc in species_list:
    count += 1
    allspcstr += spc
    allspcstr += ' ' * (30 - len(spc))
    if count % spcsperline == 0:
      allspcstr += '\n'

  total_str = commentstr + speciesallstr + commentstr + allspcstr + commentstr + speciesendstr + commentstr
  if filename:
    with open(filename, "w") as spcfile:
        spcfile.write(total_str)
  return total_str


def clean_therm(therm_file, therm_output, species_list, datetime):
  therm = open(therm_file, 'r', encoding="utf-8")
  thermlines = therm.readlines()
  therm.close()

  print("writing '" + therm_output + "'")
  with open(therm_output, 'w') as thermfile:
    thermfile.write('! Thermodynamic data for C3MechV' + VERSION +
                    ', generated on {0:%d/%m/%Y %H:%M:%S}.\n'.format(datetime))
    thermfile.write('THERMO ALL\n')
    thermfile.write('300.   1000.   5000.\n')

    species_dict = {s.upper(): 0 for s in species_list}

    for i in range(len(thermlines)):
      wrk_line = thermlines[i].split("!")[0]
      wrk_line = wrk_line.rstrip()
      if len(wrk_line) >= 80 and wrk_line[79] == '1':
        sp_name = wrk_line[0:25].split()[0].upper()
        if sp_name in species_dict and not species_dict[
            sp_name] and i + 3 < len(thermlines):
          thermfile.write(thermlines[i])
          thermfile.write(thermlines[i + 1])
          thermfile.write(thermlines[i + 2])
          thermfile.write(thermlines[i + 3])
          species_dict[sp_name] = 1

    for s, v in species_dict.items():
      if v == 0:
        print('{0} : thermochemistry data not found...'.format(s))

    thermfile.write('END\n')


def clean_tran(tran_file, tran_output, species_list, datetime):
  tran = open(tran_file, 'r', encoding="utf-8")
  tranlines = tran.readlines()
  tran.close()

  species_dict = {s.upper(): 0 for s in species_list}
  print("writing '" + tran_output + "'")
  with open(tran_output, 'w') as tranfile:
    tranfile.write('! Transport data for C3MechV' + VERSION +
                   ', generated on {0:%d/%m/%Y %H:%M:%S}.\n'.format(datetime))
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
          tranfile.write(
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


def insert_species_list(species_list, species_dict, file_path, new_lines):
  with open(file_path, 'r') as file:
    lines = file.readlines()

  normalized_reactions, normalized_reactions_check = {}, {}
  n_reaction, cantera_count, normalized_reactions, normalized_reactions_check, species_dict = count_reactions(lines, species_dict, normalized_reactions, normalized_reactions_check)

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
        continue

      # If we're in between SPECIES and END, skip these lines (to be replaced)
      continue

    # If we haven't found SPECIES or after END, copy other lines as is
    new_lines.append(line)

  return new_lines, n_reaction, cantera_count, normalized_reactions, normalized_reactions_check, species_dict


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
    match = re.search(r'\s+[+-]?((\d+\.\d*)|(\.\d+)|(\d+))([eE][+-]?\d+)?\s*$', line)
    if match:
        last_number = match.group().strip()
        if not is_float(last_number):
            raise ValueError(f"Invalid trailing number: {last_number}")
        modified_line = line[:match.start()].rstrip()  # Keep everything before the matched part
    else:
      raise Exception("Could not find the first floating point number (reading right to left, this is the activation energy) in '" + line + "'")

    # Remove second last number and check
    match = re.search(r'\s+[+-]?((\d+\.\d*)|(\.\d+)|(\d+))([eE][+-]?\d+)?\s*$', modified_line)
    if match:
        second_last_number = match.group().strip()
        if not is_float(second_last_number):
            raise ValueError(f"Invalid trailing number: {second_last_number}")
        modified_line = modified_line[:match.start()].rstrip()
    else:
      raise Exception("Could not find the second floating point number (pre-exponential factor) in '" + line + "'")

    # Remove third last number and check
    match = re.search(r'\s+[+-]?((\d+\.\d*)|(\.\d+)|(\d+))([eE][+-]?\d+)?\s*$', modified_line)
    if match:
        third_last_number = match.group().strip()
        if not is_float(third_last_number):
            raise ValueError(f"Invalid trailing number: {third_last_number}")
        modified_line = modified_line[:match.start()].rstrip()
    else:
      raise Exception("Could not find the third floating point number (reading right to left, this is the frequency factor) in '" + line + "'")

    return modified_line.rstrip()  # Return the cleaned line without leading/trailing whitespace

def convert_to_float_or_int(value):
    # Convert to float first
    float_value = float(value)
    
    # Check if the float value is close enough to an integer
    if abs(float_value - round(float_value)) < 1e-10:  # Tolerance level of 1e-10
        return str(int(round(float_value)))  # Return as int
    
    return f"{float_value:.6f}"  # Return as float

class ChemicalReaction:
  def __init__(self, reaction_string, species_dict):
    self.species_dict = species_dict
    self.reaction_string = reaction_string
    self.reaction_definition = ""
    self.inverted = False
    self.reactants = []
    self.products = []
    self.reaction_type = ""

    # Extract information from the provided reaction string
    self.extract_reaction(reaction_string)

  def __copy__(self):
     # Create a new ChemicalReaction object with copied attributes
     new_instance = ChemicalReaction(self.reaction_string, copy.copy(self.species_dict))
     
     # Copy other attributes explicitly
     new_instance.inverted = self.inverted
     new_instance.reactants = copy.deepcopy(self.reactants)
     new_instance.products= copy.deepcopy(self.products)
     new_instance.reaction_type= self.reaction_type
    
     return new_instance


  def make_irreversible(self):
    self.reaction_type='irreversible'

  def make_reversible(self):
    self.reaction_type='reversible'

  def invert(self):
    self.reactants, self.products = self.products, self.reactants
    self.inverted = not self.inverted

  def pretty(self):
      # Prepare reactant string without coefficients unless greater than one.
      reactant_parts= [f"{name}" if coef == 1.0 else f"{convert_to_float_or_int(coef)} {name}" for coef,name in sorted(self.reactants)]
      
      # Prepare product string without coefficients unless greater than one.
      product_parts= [f"{name}" if coef == 1.0 else f"{convert_to_float_or_int(coef)} {name}" for coef,name in sorted(self.products)]

      separator= " <=> " if self.reaction_type=='reversible' else " => "
      
      return " + ".join(reactant_parts) + separator + " + ".join(product_parts)

  def extract_species(self, species_part):
    """Extracts species (reactants or products) from a given part of the reaction."""
    species = []
    species_2_idx = {}
    for species_str in species_part.split('+'):
      stripped_species = species_str.strip()
      if stripped_species:  # Only process non-empty strings
        match = re.match(r'^\s*([\d\.]+)?\s*([\w\-\(\),\#]+)\s*$', stripped_species)
        if match:
          coefficient = match.group(1)
          name = match.group(2)
          if name in self.species_dict:
            stoichiometric_coefficient = float(coefficient) if coefficient else 1.0
            # this is wrong for A+A = B because A+A is not merged
            if name in species_2_idx:
              species[species_2_idx[name]][0] += stoichiometric_coefficient
            else:
              species_2_idx[name] = len(species)
              species.append([stoichiometric_coefficient, name])
          else:
            raise Exception("Invalid species: " + name + " in '" + species_part + "'")
        else:
          raise Exception("Could not match the species regex with '" + stripped_species + "'")

    return species


  def extract_reaction(self, line):
      # Remove special species M
      line = remove_trailing_numbers(line.strip())
      self.reaction_definition = line
      line = re.sub(r'\s*\(\s*\+\s*M\s*\)\s*', '', line)  # Matches "(+ M)"
      line = re.sub(r'\s*\+\s*M\s*', '', line)  # Matches "+ M" or "+   M"
      line = re.sub(r'\s*\(\s*\+\s*([\w\-\(\),\#]+)\s*\)\s*', r'+\1', line)  # Replace "(+N2)" with " + N2 "
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
      self.reactants = [reactant for reactant in self.reactants if reactant[0] > 1.0e-10]
      self.products = [product for product in self.products if product[0] > 1.0e-10]

  def canonical_representation(self):
      """Generates a canonical representation of a chemical reaction."""
      # Sort reactants and products
      sorted_reactants = sorted(self.reactants, key=lambda x: (x[1], round(x[0], 10)))  # Sort by species name, then coefficient
      sorted_products = sorted(self.products, key=lambda x: (x[1], round(x[0], 10)))  # Sort by species name, then coefficient

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

def count_reactions(lines, species_dict, normalized_reactions, normalized_reactions_check):
  cleaned_lines = [line.split('!', 1)[0].strip().upper() for line in lines]

  n_new_species = 0
  total_species = set()
  total_reactions = set()
  n_reactions_start = len(normalized_reactions)
  cantera_count = 0

  pattern_rev = r'REV\s*/([-+\d\.eE\s]+)/'
  pattern_low = r'LOW\s*/([-+\d\.eE\s]+)/'
  pattern_high = r'HIGH\s*/([-+\d\.eE\s]+)/'
  pattern_troe = r'TROE\s*/([-+\d\.eE\s]+)/'
  pattern_plog = r'PLOG\s*/([-+\d\.eE\s]+)/'
  pattern_tcheb = r'TCHEB\s*/([-+\d\.eE\s]+)/'
  pattern_pcheb = r'PCHEB\s*/([-+\d\.eE\s]+)/'
  pattern_cheb = r'CHEB\s*/([-+\d\.eE\s]+)/'
  pattern_tb = r'([\w\-\(\),\#]+)\s*/([-+\d\.eE\s]+)/'
  pattern_unknown = r'([^\s]+)\s*/([-+\d\.eE\s]+)/'
  pattern_dup = r'(DUP|DUPLICATE)'
  pattern_elem = r'(ELEM|ELEMENTS)'
  pattern_spec = r'(SPEC|SPECIES)'
  pattern_reac = r'(REAC|REACTIONS)'
  pattern_end = r'(END)'
  element_mode = False
  species_mode = False
  reaction_mode = False
  last_canon_str = ""
  for l in cleaned_lines:

    if l == "":
      continue

    match_rev = re.match(pattern_rev, l, re.IGNORECASE)
    match_low = re.match(pattern_low, l, re.IGNORECASE)
    match_high = re.match(pattern_high, l, re.IGNORECASE)
    match_troe = re.match(pattern_troe, l, re.IGNORECASE)
    match_plog = re.match(pattern_plog, l, re.IGNORECASE)
    match_tcheb = re.match(pattern_tcheb, l, re.IGNORECASE)
    match_pcheb = re.match(pattern_pcheb, l, re.IGNORECASE)
    match_cheb = re.match(pattern_cheb, l, re.IGNORECASE)
    match_unknown = re.match(pattern_unknown, l, re.IGNORECASE)
    match_dup = re.match(pattern_dup, l, re.IGNORECASE)
    match_elem = re.match(pattern_elem, l, re.IGNORECASE)
    match_species = re.match(pattern_spec, l, re.IGNORECASE)
    match_reac = re.match(pattern_reac, l, re.IGNORECASE)
    match_end = re.match(pattern_end, l, re.IGNORECASE)
    if "=" in l:
      cantera_count += 1
      #print(l)
      reaction = ChemicalReaction(l, species_dict)
      for nu, s in reaction.reactants:
        if species_dict[s] == 0:
          species_dict[s] = 1
          n_new_species += 1
        total_species.add(s)
      for nu, s in reaction.products:
        if species_dict[s] == 0:
          species_dict[s] = 1
          n_new_species += 1
        total_species.add(s)

      last_canon_str, last_canon_str_check = reaction.canonical_representation()
      if last_canon_str in normalized_reactions:
        normalized_reactions[last_canon_str].append(reaction)
        #print(last_canon_str + ": " + reaction.reaction_definition)
      else:
        normalized_reactions[last_canon_str] = [reaction]
        #print("new reaction" + ": " + reaction.reaction_definition)
      total_reactions.add(last_canon_str)

      if last_canon_str_check in normalized_reactions_check:
        if last_canon_str != normalized_reactions_check[last_canon_str_check][0]:
          old_reaction = normalized_reactions_check[last_canon_str_check][1]
          if False and ('irreversible' != reaction.reaction_type or 'irreversible' != old_reaction.reaction_type):
            print("#warning: found '" + last_canon_str + "' and '" + old_reaction.canonical_representation()[0] + "'")
            print("reaction string 1:", old_reaction.reaction_definition)
            print("reaction string 2:", reaction.reaction_definition)
      else:
        normalized_reactions_check[last_canon_str_check] = (last_canon_str, reaction)
      #reactants, products, reaction_type = extract_reaction(l, species_dict)
      #print(canonical_reaction(reactants, products, reaction_type))
    elif match_unknown:
      found = False
      if match_rev:
        #print("FOUND REV in '" + l + "'")
        #print("reaction is '" + normalized_reactions[last_canon_str][-1].reaction_string + "'")
        found = True
        old_reaction = copy.copy(normalized_reactions[last_canon_str][-1])
        if old_reaction.reaction_type == "irreversible":
          raise Exception("REV keyword incompatible with irreversible reaction in '" + l + "'")
        normalized_reactions[last_canon_str].pop()
        if len(normalized_reactions[last_canon_str]) == 0:
          del normalized_reactions[last_canon_str]
          total_reactions.remove(last_canon_str)

        old_reaction.make_irreversible()
        canon_old, canon_old_check = old_reaction.canonical_representation()
        if canon_old in normalized_reactions:
          normalized_reactions[old_reaction.canonical_representation()].append(old_reaction)
        else:
          normalized_reactions[old_reaction.canonical_representation()] = [old_reaction]
        total_reactions.add(old_reaction.canonical_representation())

        numbers_part = match_rev.group(1).strip()
        # Split by whitespace and filter out empty strings
        number_strings = [num for num in numbers_part.split() if num]
        
        # Convert to float and limit to up to three numbers
        number_array = []
        for num_str in number_strings[:3]:  # Limit to first three numbers only
            try:
                number_array.append(float(num_str))  # Convert string to float
            except ValueError:
                print(f"Could not convert '{num_str}' to float in REV //.")
        if number_array[0] != 0.0:
          cantera_count += 1
          new_reaction = copy.copy(old_reaction)
          new_reaction.invert()
          canon_new, canon_new_check = new_reaction.canonical_representation()
          if canon_new in normalized_reactions:
            normalized_reactions[new_reaction.canonical_representation()].append(new_reaction)
          else:
            normalized_reactions[new_reaction.canonical_representation()] = [new_reaction]
          total_reactions.add(new_reaction.canonical_representation())
        #print("after:", canon_old)
        #print("after:", canon_new)
        #quit()
      if match_low:
        found = True
      if match_high:
        found = True
      if match_troe:
        found = True
      if match_plog:
        found = True
      if match_tcheb:
        found = True
      if match_pcheb:
        found = True
      if match_cheb:
        found = True

      if not found:
        # Find all matches
        matches_tb = re.findall(pattern_tb, l)
        parsed_data_tb = [(match[0], float(match[1])) for match in matches_tb]
        ok = 0
        for tb, val in parsed_data_tb:
          if tb in species_dict:
            ok += 1
          else: 
            print("unknown keyword '" + tb + "'")
        if len(parsed_data_tb) == ok:
          found = True
        if not found:
          print("no match for:")
          print("'" + l + "'")
          quit()
      if not found:
        print("no match for //:")
        print("'" + l + "'")
        quit()
    elif match_dup:
      pass
    elif match_elem:
      element_mode = True
    elif match_species:
      species_mode = True
    elif match_reac:
      reaction_mode = True
    elif match_end:
      element_mode = False
      reaction_mode = False
      species_mode = False
    elif element_mode:
      pass
    elif species_mode:
      pass
    else:
      print("no match for:")
      print("'" + l + "'")
      quit()

  print("    new species in sub-module:", n_new_species)
  print("  total species in sub-module:", len(total_species))
  print("      reactions in sub-module:", len(normalized_reactions)-n_reactions_start)
  # print("total reactions in sub-module:", len(total_reactions))
  # print("number of reactions: ", len(normalized_reactions)-n_reactions_start)
  # print("number of ='s + number of REV's (cantera counting): ", cantera_count)
  return len(normalized_reactions)-n_reactions_start, cantera_count, normalized_reactions, normalized_reactions_check, species_dict

def merge_models(species_list, submodules_files, output_filename, datetime):
  species_section_str = write_species_list(species_list, '')
  new_lines = []

  header_path = os.path.join(DIR, YAML)
  with open(header_path,'r') as f:
    for line in f:
      new_lines.append(line)
    new_lines.append("\n")
    new_lines.append("\n")

  new_lines.append('! Kinetics data for C3MechV' + VERSION +
                   ', generated on {0:%d/%m/%Y %H:%M:%S}.\n'.format(datetime) +
                   '\n')
  new_lines.append(
      '! The following sub-modules were considered in this file:\n')
  new_lines.append('! - ' + os.path.basename(submodules_files.core) + '\n')
  for file_path in submodules_files.submodules:
    new_lines.append('! - ' + os.path.basename(file_path) + '\n')
  new_lines.append("\n")

  species_dict = {s:0 for s in species_list}
  for s in species_dict:
    if "+" in s:
      raise Exception("species name '" + s + "' contains a +")
    
    match = re.match(r'^[\w\-\(\),\#]+$', s)
    if not match:
      raise Exception("species name '" + s + "' does not match the species pattern")

  new_lines.append("! number of species: " + str(len(species_list)) + "\n")


  print("processing: '" + os.path.basename(submodules_files.core) + "'")
  new_lines, n_reaction, cantera_count, normalized_reactions, normalized_reactions_check, species_dict = insert_species_list(species_section_str, species_dict, submodules_files.core,
                                  new_lines)

  #base_names = sorted([os.path.basename(file_path) for file_path in submodules_files.submodules])
  aux_path = {os.path.basename(file_path):file_path for file_path in submodules_files.submodules}
  for base_name in aux_path:
    file_path = aux_path[base_name]
    print("processing: '" + base_name + "'")
    with open(file_path, 'r') as file:
      lines = file.readlines()
      n_reaction_i, cantera_count_i, normalized_reactions, normalized_reactions_check, species_dict = count_reactions(lines, species_dict, normalized_reactions, normalized_reactions_check)
      n_reaction += n_reaction_i
      cantera_count += cantera_count_i
      new_lines += lines

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

  new_lines.append("! number of reactions: " + str(len(normalized_reactions)) + "\n")
  print("merged model contains " + str(len(species_list)) 
        + " species and " + str(cantera_count)  + " (cantera count) / " 
        + str(len(normalized_reactions)) + " (normal count) reactions")

  new_lines.append("END\n\n")

  print("writing '" + output_filename + "'")
  with open(output_filename, 'w', encoding="utf-8") as file:
    file.writelines(new_lines)


if __name__ == "__main__":

  print("read input...")
  DATETIME = datetime.datetime.now()
  yaml_file_path = os.path.join(DIR, YAML)
  species_list, submodules_files = get_species_list_submodule(yaml_file_path)
  print("\ngenerate output...")
  merge_models(species_list, submodules_files,
               os.path.join(DIR, OUTPUT, "C3Mech.CKI"), DATETIME)
  therm_input = os.path.join(get_submodules_dir(), "SOURCE-C3Mech.THERM")
  clean_therm(therm_input, os.path.join(DIR, OUTPUT, "C3Mech.THERM"),
              species_list, DATETIME)
  trans_input = os.path.join(get_submodules_dir(), "SOURCE-C3Mech.TRAN")
  clean_tran(trans_input, os.path.join(DIR, OUTPUT, "C3Mech.TRAN"), species_list,
             DATETIME)
