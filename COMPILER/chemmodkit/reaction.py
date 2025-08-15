import re
import copy

from typing import List

from . import input as inp


def compute_elem(reac_prod, species_compo_dict):
  atoms = {}
  for nu, spc in reac_prod:
    for elem, count in species_compo_dict[spc].items():
      if elem not in atoms and count != 0.0:
        atoms[elem] = 0.0
      if count != 0.0:
        atoms[elem] += count * nu
  return atoms


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
    self.reactant_set = set()
    self.products = []
    self.product_set = set()
    self.reacting = set()
    # A+Ar=B+Ar adds an explicit dependence on Ar
    self.explicit_dependence = set()
    self.tb_efficiencies = {}
    self.reaction_type = ""
    self.submodule_filename = ""

    # Extract information from the provided reaction string
    self.extract_reaction(reaction_string)

    self.canonical_reactants = None
    self.canonical_products = None
    self.idx = -1
    self.increment = {}
    self.reac_most_elem = {}
    self.prod_most_elem = {}
    self.reac_atoms = {}
    self.prod_atoms = {}

  def __copy__(self):
    # Create a new ChemicalReaction object with copied attributes
    new_instance = ChemicalReaction(self.reaction_string,
                                    self.reaction_string_orig,
                                    self.species_dict)

    # Copy other attributes explicitly
    new_instance.inverted = self.inverted
    new_instance.reactants = copy.deepcopy(self.reactants)
    new_instance.reactant_set = copy.deepcopy(self.reactant_set)
    new_instance.products = copy.deepcopy(self.products)
    new_instance.product_set = copy.deepcopy(self.product_set)
    new_instance.reacting = copy.deepcopy(self.reacting)
    new_instance.reaction_type = copy.deepcopy(self.reaction_type)
    new_instance.reaction_string_orig = copy.deepcopy(
        self.reaction_string_orig)
    new_instance.reaction_string_aux = copy.deepcopy(self.reaction_string_aux)
    new_instance.reaction_intro = copy.deepcopy(self.reaction_intro)
    new_instance.explicit_dependence = copy.deepcopy(self.explicit_dependence)
    new_instance.empty_chemkin = self.empty_chemkin

    return new_instance

  def prod_permutations(self):
    return permute(self.canonical_products)

  def reac_permutations(self):
    return permute(self.canonical_reactants)

  def update_history_spcs(self, history_spcs, producing_spcs, fb):
    produced_spcs = None
    if fb == "f":
      produced_spcs = self.canonical_products
    elif fb == "b":
      produced_spcs = self.canonical_reactants
    else:
      raise ValueError("unknown direction '" + str(fb) + "'")

    hist_prod_spcs = {}
    for s in producing_spcs:
      for e in history_spcs[s]:
        if e == "reaction":
          continue
        if e not in hist_prod_spcs:
          hist_prod_spcs[e] = 0
        # distance to the reactions is largest distance
        # of all producing species
        hist_prod_spcs[e] = max(hist_prod_spcs[e], history_spcs[s][e])

    # print("history_spcs:")
    # for s in history_spcs:
    #   print("{0:15s} {1:s}".format(s, str(history_spcs[s])))
    print("hist_prod_spcs", hist_prod_spcs, "of", producing_spcs)

    global _empty_spc_history
    updated_species = set()
    for s in produced_spcs:
      add_s = False
      if s not in history_spcs:
        history_spcs[s] = copy.copy(_empty_spc_history)
        history_spcs[s]["reaction"] = []

      for e in history_spcs[s]:
        if e == "reaction":
          continue
        new_increment = max(0, self.element_increment(fb,
                                                      e)) + hist_prod_spcs[e]
        if history_spcs[s][e] > new_increment:
          history_spcs[s][e] = new_increment
          add_s = True

      if add_s:
        print("new species:", s)
        updated_species.add(s)

        history_spcs[s]["reaction"].append(self)
        print("added", self.pretty(), "to", s)
        print("history_spcs of", s, "is", history_spcs[s])
      else:
        print("history_spcs of", s, "remains", history_spcs[s])
    return updated_species

  def is_produced(self, fb, spcs):
    if fb == "f":
      return bool(spcs & self.product_set)
    elif fb == "b":
      return bool(spcs & self.reactant_set)
    else:
      raise ValueError("unknown direction '" + str(fb) + "'")

  def produced(self, fb, history_spcs) -> List[str]:
    if fb == "f":
      print("returning produced " + str(list(self.canonical_products)))
      return self.canonical_products
    elif fb == "b":
      print("returning produced " + str(list(self.canonical_reactants)))
      return self.canonical_reactants
    else:
      raise ValueError("unknown direction '" + str(fb) + "'")

  def compute_element_increment(self, species_compo_dict, species_heavy):
    for nu, spc in self.reactants:
      for elem, count in species_compo_dict[spc].items():
        if count > 0.0:
          self.reac_most_elem[elem] = 0
          self.prod_most_elem[elem] = 0

    for nu, spc in self.reactants:
      if spc in species_heavy:
        for elem, count in species_compo_dict[spc].items():
          if count > 0.0:
            self.reac_most_elem[elem] = max(count, self.reac_most_elem[elem])

    for nu, spc in self.products:
      if spc in species_heavy:
        for elem, count in species_compo_dict[spc].items():
          if count > 0.0:
            self.prod_most_elem[elem] = max(count, self.prod_most_elem[elem])

    for elem in self.reac_most_elem:
      self.increment[
          elem] = self.prod_most_elem[elem] - self.reac_most_elem[elem]

  def element_increment(self, fb, elem) -> int:
    if elem not in self.increment:
      return 0

    if fb == "f":
      return self.increment[elem]
    elif fb == "b":
      return -self.increment[elem]
    else:
      return ValueError("unknown direction '" + str(fb) + "'")

  def c_increment(self, fb) -> int:
    return self.element_increment(fb, "C")

  def h_increment(self, fb) -> int:
    return self.element_increment(fb, "H")

  def o_increment(self, fb) -> int:
    return self.element_increment(fb, "O")

  def n_increment(self, fb) -> int:
    return self.element_increment(fb, "N")

  def set_idx(self, idx):
    self.idx = idx

  def get_idx(self):
    return self.idx

  def set_submodule_file(self, submodule_filename):
    self.submodule_filename = submodule_filename

  def get_submodule_file(self):
    return self.submodule_filename

  def add_reaction_info(self, line):
    self.reaction_string_aux.append(line)

  def add_intro(self, line):
    self.reaction_intro.append(line)

  def with_rev_keyword(self):
    CHEMKIN_text = self.reaction_intro + [self.reaction_string_orig
                                          ] + self.reaction_string_aux
    has_rev = False
    rev_match = re.compile(r'REV\s*/([-+\d\.eE\s]+)/', re.IGNORECASE)
    for test_line in CHEMKIN_text:
      if rev_match.match(test_line):
        has_rev = True
        break
    return has_rev

  def get_orignal_CHEMKIN_text(self):
    CHEMKIN_text = self.reaction_intro + [self.reaction_string_orig
                                          ] + self.reaction_string_aux
    if self.empty_chemkin:
      return [""]
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

  def canonical_species_tuple(self, reac_prod):
    return tuple(
        sorted([spc
                for nu, spc in reac_prod] + list(self.explicit_dependence)))

  def init_species_tuples(self):
    self.canonical_reactants = self.canonical_species_tuple(self.reactants)
    self.canonical_products = self.canonical_species_tuple(self.products)

  def check_elem_conservation(self, species_compo_dict, tol=1.0e-3):

    # Compute elemental compositions for reactants and products separately
    self.reac_atoms = compute_elem(self.reactants, species_compo_dict)
    self.prod_atoms = compute_elem(self.products, species_compo_dict)

    # Gather all elements appearing in either reactants or products
    all_elems = set(self.reac_atoms.keys()).union(self.prod_atoms.keys())

    # Compare element counts within the tolerance
    for elem in all_elems:
      reac_val = self.reac_atoms.get(elem, 0.0)
      prod_val = self.prod_atoms.get(elem, 0.0)
      if abs(reac_val - prod_val) > tol:
        # If difference is too large, print details and return True
        print(self.pretty() + ":")
        # Print sorted dictionaries by element name
        print("Reactants:", dict(sorted(self.reac_atoms.items())))
        print("Products:", dict(sorted(self.prod_atoms.items())))
        return True
    return False

  def extract_reaction(self, line):

    # Remove special species M
    line = inp.remove_trailing_numbers(line.strip())
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
        self.reactant_set.add(reactant[1])
      else:
        self.explicit_dependence.add(reactant[1])
    self.reactants = pruned_reactants

    pruned_products = []
    for product in self.products:
      if product[0] > 1.0e-10:
        pruned_products.append(product)
        self.product_set.add(product[1])
      else:
        self.explicit_dependence.add(product[1])
    self.products = pruned_products
    self.reacting = self.reactant_set | self.product_set

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


def get_cons_prod_counter(reactions, increment):
  consumed = {}
  produced = {}
  species2reaction = {}
  for r in reactions:
    for rr in reactions[r]:
      rr.set_consumed(consumed, species2reaction, increment)
      rr.set_produced(produced, species2reaction, increment)
  return consumed, produced, species2reaction
