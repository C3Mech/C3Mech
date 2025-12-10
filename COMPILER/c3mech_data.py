import os
import re
import sys
from itertools import combinations
from collections import defaultdict
import string
import ntpath as _p  # Windows semantics on all OSes
from typing import Dict, Iterable, List, Sequence, Tuple

VERSION = "4.0.1"
DMC_EC_FEW = True
# Default to Cantera-compatible sub-modules for ambiguous keys (C0, C1-C2)
CANTERA_MODE = True

DEPENDENCIES = {
    # note that the order of the keys matters!!
    # always append new keys at the end to preserve old model ids
    "C0": set([]),
    "C1-C2": set(["C0"]),
    "C3-C4": set(["C0", "C1-C2"]),
    "C5": set(["C0", "C1-C2", "C3-C4"]),
    "C5cy": set(["C0", "C1-C2", "C3-C4"]),  # , "C5"
    "C6": set(["C0", "C1-C2", "C3-C4", "C5"]),
    "C6cy": set(["C0", "C1-C2", "C3-C4", "C5cy"]),  # , "C5"
    "C7": set(["C0", "C1-C2", "C3-C4", "C5", "C6"]),
    "LLNL_BLOCK": set(["C0", "C1-C2", "C3-C4", "C5", "C6", "C7"]),
    "LLNL_BLOCK_DMC_EC": set(["C0", "C1-C2"]),
    "UOG_N": set(["C0"]),
    "UOG_C-N": set(["C0", "C1-C2", "UOG_N"]),
    "PAH_BLOCK": set(["C0", "C1-C2", "C3-C4", "C5cy", "C6cy"]),  # , "C5"
}


def init_identifier_max(dependencies):
  return tuple(dependencies.keys())


# If a key was binary (or ternary), keep its base fixed forever.
ORDERED_KEYS = init_identifier_max(DEPENDENCIES)
BINARY_KEYS = {'LLNL_BLOCK_DMC_EC', 'C1-C2', 'PAH_BLOCK', 'C0', 'UOG_N'}

carbon_map = {
    'C0': 0,
    'C1-C2': 2,
    'C3-C4': 4,
    'C5': 5,
    'C5cy': 5,
    'C6': 6,
    'C6cy': 6,
    'C7': 7,
    'LLNL_BLOCK': 8,  # Use >7 as 8 for sorting
}

columns = [
    ('C0', 'C0'),
    ('C1-C2', 'C1-C2'),
    ('C3-C4', 'C3-C4'),
    ('C5', 'C5'),
    ('C6', 'C6'),
    ('C7', 'C7'),
    ('LLNL_BLOCK', 'C8+'),
    ('C5cy', 'C5CY'),
    ('C6cy', 'C6CY'),
    ('LLNL_BLOCK_DMC_EC', 'DMC+EC'),
    #('UOG_C-N', ''), # handled separately
    ('UOG_N', 'N'),
    ('PAH_BLOCK', 'PAH')
]

key_to_display = dict(columns)
cyclic_keys = ['C5cy', 'C6cy']


def print_not_found(what, dir_or_file, path):
  print(what + " " + dir_or_file + " '" + path + "' does not exist")


def get_submodules_dir(abs_dir):
  return os.path.normcase(
      os.path.normpath(os.path.join(abs_dir, os.path.join("..",
                                                          "SUBMODULES"))))


# Helper to get max carbon in a combination
def max_carbon(combo):
  return max([carbon_map.get(b, -1) for b in combo if b in carbon_map] + [0])


def get_base_modules():
  return ["C1-C2", "C3-C4", "C5", "C5cy", "C6", "C6cy", "C7"]


def get_ht_htlt_modules(abs_dir):
  """
  returns the sub-module filesnames in an unspecified order;
  file paths are absolute and normalized
  """
  global CANTERA_MODE

  # choose the C0 and C1-C2 variant depending on the global mode
  c0_rel = os.path.join("UOG", "LT-HT", "UOG_C0_LT-HT_Cantera.MECH") if CANTERA_MODE \
           else os.path.join("UOG", "LT-HT", "UOG_C0_LT-HT.MECH")
  c12_rel = os.path.join("UOG", "LT-HT", "UOG_C1-C2_LT-HT_Cantera.MECH") if CANTERA_MODE \
            else os.path.join("UOG", "LT-HT", "UOG_C1-C2_LT-HT.MECH")

  base_modules_UOG_HTLT = [c0_rel] + [
      (c12_rel if b == "C1-C2" else os.path.join("UOG", "LT-HT", "UOG_" + b +
                                                 "_LT-HT.MECH"))
      for b in get_base_modules()
  ]
  base_modules_UOG_HT = base_modules_UOG_HTLT[:2] + [
      os.path.join("UOG", "HT", "UOG_" + b + "_HT.MECH")
      for b in get_base_modules()[1:]
  ]
  LLNL_base_modules_HT = [os.path.join("LLNL", "LLNL_BLOCK_HT.CKI")]
  LLNL_base_modules_HTLT = [os.path.join("LLNL", "LLNL_BLOCK.CKI")]

  #optional_modules_HT = [
  #    os.path.join("UOG", "HT", "UOG_" + "N" + "_HT.MECH")
  #]

  #optional_modules_HTLT = [
  #    os.path.join("UOG", "LT-HT", "UOG_" + "N" + "_LT-HT.MECH")
  #]
  optional_modules = [
      os.path.join("UOG", "LT-HT", "UOG_N_LT-HT.MECH"),
      os.path.join("ITV_POLIMI", "PAH_BLOCK.CKI"),
      os.path.join("LLNL", "LLNL_BLOCK_DMC_EC.CKI")
  ]

  required_extension_HT = [
      os.path.join("UOG", "HT", "UOG_" + "C-N" + "_HT.MECH")
  ]
  required_extension_HTLT = [
      os.path.join("UOG", "LT-HT", "UOG_" + "C-N" + "_LT-HT.MECH")
  ]

  modules_ht = base_modules_UOG_HT + LLNL_base_modules_HT + optional_modules + required_extension_HT  # + optional_modules_HT
  modules_htlt = base_modules_UOG_HTLT + LLNL_base_modules_HTLT + optional_modules + required_extension_HTLT  #  + optional_modules_HTLT

  ok = True
  modules_ht_final = []
  for f in modules_ht:
    cur_path = os.path.join(get_submodules_dir(abs_dir), f)
    if (not os.path.isfile(cur_path)):
      print_not_found("", "file", cur_path)
      ok = False
    modules_ht_final.append(
        os.path.normcase(os.path.abspath(os.path.normpath(cur_path))))
  modules_htlt_final = []
  for f in modules_htlt:
    cur_path = os.path.join("..", get_submodules_dir(abs_dir), f)
    if (not os.path.isfile(cur_path)):
      print_not_found("", "file", cur_path)
      ok = False
    modules_htlt_final.append(
        os.path.normcase(os.path.abspath(os.path.normpath(cur_path))))
  if not ok:
    raise Exception("could not find all files")

  return modules_ht_final, modules_htlt_final


def lump_main_chain(combo):
  main_chain_keys = ['C0', 'C1-C2', 'C3-C4', 'C5', 'C6', 'C7',
                     'LLNL_BLOCK']  # LLNL_BLOCK is C8+
  # Find which main chain blocks are present
  present = [k for k in main_chain_keys if k in combo]
  if not present:
    return []
  first_idx = main_chain_keys.index(present[0])
  last_idx = max(main_chain_keys.index(k) for k in present)
  # Lump as range from first to last block *present*
  return main_chain_keys[first_idx:last_idx + 1]


def sanitize_filename(combo):
  s_combo = set(combo)
  # Lumping main chain
  lumped_blocks = lump_main_chain(s_combo)

  # Display names for lumped part
  if lumped_blocks:
    first_disp = key_to_display[lumped_blocks[0]]
    last_disp = key_to_display[lumped_blocks[-1]]
    # If only one block: just "C0"
    if len(lumped_blocks) == 1:
      lump_str = f"{first_disp}"
    else:
      lump_str = f"{first_disp}-{last_disp}"
    parts = [lump_str]
  else:
    parts = []

  # Add explicit cyclics if present (always explicit!)
  for cyc_key in cyclic_keys:
    if cyc_key in s_combo:
      parts.append(key_to_display[cyc_key])

  # Add any other modules that aren't already included, using display names and column order
  used_keys = set(lumped_blocks + cyclic_keys)
  rest_modules = [
      key_to_display[k] for k, _ in columns
      if k not in used_keys and k in s_combo
  ]

  parts += rest_modules

  return "_".join(parts)


def sort_key(combo):
  s = set(combo)
  return (
      max_carbon(s),
      ('UOG_N' in s),
      ('UOG_C-N' in s),
      ('LLNL_BLOCK_DMC_EC' in s),
      ('PAH_BLOCK' in s),
      sorted(s)  # To break ties lexicographically
  )


def match_submodules(submodules, modules_ht, modules_htlt):
  """
    For each submodule in `submodules`, find and assign its best match in
    `modules_ht` and `modules_htlt`. Returns two dictionaries mapping submodule names.
    """

  def find_match(smod, modules_list, label):
    matched_mod = None
    smod_l = smod.lower()
    smod_u = smod.upper()

    # Auxiliary token for LLNL special cases
    aux_l = smod_l + "."
    if smod_u == "LLNL_BLOCK":
      aux_l = "llnl_block_ht" if label == "HT" else "llnl_block."

    # First pass: prefer UOG files when name contains "<key>_" and "UOG"
    for mod in modules_list:
      mod_l = mod.lower()
      if (smod_l + "_") in mod_l and "uog" in mod_l:
        if matched_mod is not None:
          raise Exception(f"second match '{smod}' in {label}")
        matched_mod = mod

    # Second pass: fallback to any occurrence of aux_l (covers LLNL and others)
    if matched_mod is None:
      for mod in modules_list:
        mod_l = mod.lower()
        if aux_l in mod_l:
          if matched_mod is not None:
            raise Exception(f"second match '{smod}' in {label}")
          matched_mod = mod

    if matched_mod is None:
      print(f"no match for {label}: {smod}")

    return matched_mod

  submodules_ht = {}
  submodules_htlt = {}

  for smod in submodules:
    ht_match = find_match(smod, modules_ht, "HT")
    if ht_match:  # Only add if found
      submodules_ht[smod] = ht_match

    htlt_match = find_match(smod, modules_htlt, "HTLT")
    if htlt_match:  # Only add if found
      submodules_htlt[smod] = htlt_match

  return submodules_ht, submodules_htlt


def get_submodule_filenames(abs_dir):
  """
  returns a map from sub-modules to filenames in the order
  of ORDERED_KEYS
  """
  submodules = {}
  for dep in ORDERED_KEYS:
    for base in DEPENDENCIES[dep]:
      if base not in DEPENDENCIES:
        raise Exception("base:" + base)
    submodules[dep] = ""
  modules_ht, modules_htlt = get_ht_htlt_modules(abs_dir)
  submodules_ht, submodules_htlt = match_submodules(submodules, modules_ht,
                                                    modules_htlt)

  # Ensure every key in ORDERED_KEYS was matched for both HT and LT-HT
  missing_ht = [k for k in ORDERED_KEYS if k not in submodules_ht]
  missing_ltht = [k for k in ORDERED_KEYS if k not in submodules_htlt]

  if missing_ht or missing_ltht:
    print("ERROR: could not find sub-module file matches for:")
    if missing_ht:
      print(" HT   :", ", ".join(missing_ht))
    if missing_ltht:
      print(" LT-HT:", ", ".join(missing_ltht))
    print("Check your SUBMODULES directory and expected filenames.")
    sys.exit(1)

  submodules_filenames = {
      "HT": submodules_ht,
      "LT-HT": submodules_htlt,
  }

  return submodules_filenames


def is_ht(filenames, submodules_dir):
  submodules_filenames = get_submodule_filenames(submodules_dir)
  ht_files = set(list(submodules_filenames["HT"].values()))
  filenames = get_relative_submodule_paths(filenames, submodules_dir)
  ht_files = get_relative_submodule_paths(ht_files, submodules_dir)
  for f in filenames:
    if f not in ht_files:
      return False
  return True


def is_ltht(filenames, submodules_dir):
  submodules_filenames = get_submodule_filenames(submodules_dir)
  ltht_files = set(list(submodules_filenames["LT-HT"].values()))
  filenames = get_relative_submodule_paths(filenames, submodules_dir)
  ltht_files = get_relative_submodule_paths(ltht_files, submodules_dir)
  for f in filenames:
    if f not in ltht_files:
      return False
  return True


def generate_submodels(options):

  submodules_filenames = get_submodule_filenames(options.submodules_dir)

  ht_files = set(list(submodules_filenames["HT"].values()))
  ltht_files = set(list(submodules_filenames["LT-HT"].values()))
  temp_independent = ht_files & ltht_files

  print("high-temperature sub-modules:")
  for k, v in submodules_filenames["HT"].items():
    if v not in temp_independent:
      print("{:<20} {}".format(k, v))
  print("")
  print("low- and high-temperature sub-modules:")
  for k, v in submodules_filenames["LT-HT"].items():
    if v not in temp_independent:
      print("{:<20} {}".format(k, v))
  print("temperature-independent:")
  for k, v in submodules_filenames["HT"].items():
    if v in temp_independent:
      print("{:<20} {}".format(k, v))
  print("")

  def generate_valid_combinations(dependencies):
    keys = list(dependencies)
    ORDER_IDX = {k: i for i, k in enumerate(ORDERED_KEYS)}  # O(1) lookup

    valid_combos = []

    # Try all possible subsets
    for i in range(1, len(keys) + 1):
      for combo in combinations(keys, i):
        s = set(combo)
        if all(dependencies[k].issubset(s) for k in s):
          # sort by ORDERED_KEYS instead of simple sorted()
          ordered_combo = sorted(s, key=ORDER_IDX.get)
          valid_combos.append(ordered_combo)
    return valid_combos

  combinations_list = generate_valid_combinations(DEPENDENCIES)
  combinations_final = []
  for combo in combinations_list:
    #print(combo)
    has_carbon = False
    if (set(get_base_modules()) & set(combo)
        or set(["LLNL_BLOCK", "LLNL_BLOCK_DMC_EC", "PAH_BLOCK"]) & set(combo)):
      has_carbon = True

    if (has_carbon and "UOG_N" in combo) and not "UOG_C-N" in combo:
      continue
    if DMC_EC_FEW and ((
        (max_carbon(combo) > 2 or "UOG_N" in combo) and max_carbon(combo) < 8)
                       and "LLNL_BLOCK_DMC_EC" in combo):
      continue

    else:
      combinations_final.append(combo)

  sorted_combos = sorted(combinations_final, key=sort_key)
  n = len(sorted_combos)
  print(
      "Found", n, "possible combinations (" + str(len(combinations_list) - n) +
      " options excluded)")
  # for combo in sorted_combos:
  #  print(combo)
  # print("stop")
  # sys.exit(1)
  carbon_block_names = {
      0: "C0",
      2: "C1-C2",
      4: "C3-C4",
      5: "C5",
      6: "C6",
      7: "C7",
      8: "C8+"
  }

  midgen = MID(ORDERED_KEYS, BINARY_KEYS, version=VERSION)
  grouped_combos = defaultdict(dict)
  for module_set in sorted_combos:
    cnum = max_carbon(module_set)
    if cnum > options.max_c:
      continue

    if cnum not in grouped_combos:
      grouped_combos[cnum] = {}
      dir_name = carbon_block_names.get(cnum, f"C{cnum}")
      outdir_path = os.path.join(options.output_dir, dir_name)
      grouped_combos[cnum]["output_dir"] = outdir_path
      os.makedirs(outdir_path, exist_ok=True)

      grouped_combos[cnum]["modules"] = []
      grouped_combos[cnum]["mid"] = []
      grouped_combos[cnum]["output_chunks"] = []
      grouped_combos[cnum]["temperature"] = []

    data_dict = grouped_combos[cnum]
    for temperature in submodules_filenames:
      data_dict["modules"].append({smod: temperature for smod in module_set})
      data_dict["output_chunks"].append(
          sanitize_filename(data_dict["modules"][-1]) + "_" + temperature)
      data_dict["mid"].append(midgen.combo_to_id(data_dict["modules"][-1]))
      data_dict["temperature"].append(temperature)
  return submodules_filenames, grouped_combos


class MID:
  """
    A class that maps model combinations to model IDs (MIDs) and vice versa,
    supporting mixed-radix encoding (binary for some keys, ternary for others).
    """
  # These should be set globally before using the class:
  #   - ORDERED_KEYS: list of all keys in order
  #   - BINARY_KEYS: set of keys that are only present/absent (HT/LT-HT treated the same)

  BASE = 36
  CHARS = string.digits + string.ascii_lowercase
  START = ""
  WITH_VERSION = False

  def __init__(self, ordered_keys, binary_keys, version):
    self.ORDERED_KEYS = ordered_keys
    self.BINARY_KEYS = binary_keys
    self.BASES = [2 if k in self.BINARY_KEYS else 3 for k in self.ORDERED_KEYS]
    self.key_to_idx = {k: i for i, k in enumerate(self.ORDERED_KEYS)}
    self.version = version
    if self.version != "4.0.1":
      raise ValueError(
          "MID is currently assumed to only be used for C3MechV4.0.1")

  def max_mixed_radix_number(self):
    n = 0
    for base in self.BASES:
      n = n * base + (base - 1)
    return n

  def max_mid(self):
    n = 0
    for base in self.BASES:
      n = n * base + (base - 1)
    id_body = self.int_to_base36(n).upper()
    mid_str = f"{self.version}.{id_body}"
    return mid_str

  def combo_to_id(self, selection):
    """combo_keys: set of selected keys; selection: dict mapping key -> 'HT'/'LT-HT'"""
    n = 0
    for smod in selection:
      if smod not in self.ORDERED_KEYS:
        raise ValueError("Invalid sub-module '" + smod + "'")
    for idx, key in enumerate(self.ORDERED_KEYS):
      base = self.BASES[idx]
      if key not in selection:
        digit = 0
      elif base == 2:
        digit = 1  # treat both HT and LT-HT as just "present"
      else:
        digit = 1 if selection[key] == 'HT' else 2
      n = n * base + digit
    id_str = self.int_to_base36(n)
    if self.WITH_VERSION:
      id_str = f"{self.version}_{id_str}"
    return self.START + f"{id_str.upper()}"

  def int_to_base36(self, n):
    chars = self.CHARS
    if n == 0:
      return chars[0]
    result = ""
    while n > 0:
      result = chars[n % self.BASE].lower() + result
      n //= self.BASE
    return result

  def base36_to_int(self, s):
    s = s.lower()
    chars = self.CHARS
    char_to_val = {c: i for i, c in enumerate(chars)}
    n = 0
    for c in s:
      n = n * self.BASE + char_to_val[c]
    return n

  def id_to_combo(self, id_str):
    """Decode an ID back to (combo_keys_set, selection_dict)"""
    if len(id_str) <= 1:
      raise ValueError(f"id_str='{id_str}' is too short")

    if self.START and id_str[0] != self.START:
      raise ValueError(f"first character in id_str='{id_str}' must be '" +
                       self.START + "'")
    if not re.fullmatch(r'[a-z0-9]+', id_str.lower()):
      print("#error: MID '" + id_str.lower() + "' contains invalid characters")
      sys.exit(1)
    if self.START:
      id_str = id_str[1:]
    try:
      if self.WITH_VERSION:
        prefix, id_body = id_str.split('_', 1)
        ver = prefix
      else:
        id_body = id_str
        ver = self.version
    except Exception:
      raise ValueError(f"Invalid MID format: {id_str}")

    n = self.base36_to_int(id_body.lower())

    digits = []

    # Unpack into digits from rightmost to leftmost KEY,
    # using mixed radix.
    for base in reversed(self.BASES):
      digits.append(n % base)
      n //= base

    digits.reverse()

    selection = {}

    for idx, (key, digit) in enumerate(zip(self.ORDERED_KEYS, digits)):
      base = self.BASES[idx]
      if digit == 0:
        continue
      if base == 2:
        selection[key] = 'LT-HT'
      elif digit == 1:
        selection[key] = 'HT'
      elif digit == 2:
        selection[key] = 'LT-HT'

    return selection


def get_grouped_combos_mid(options):
  print("Generating model from MID '" + options.mid + "'")
  midgen = MID(ORDERED_KEYS, BINARY_KEYS, version=VERSION)

  # Decide which physical sub-modules to map to ambiguous keys (C0, C1-C2)
  global CANTERA_MODE
  CANTERA_MODE = bool(options.mid_cantera)

  selection = midgen.id_to_combo(options.mid)

  print("MID '" + options.mid + "' decoded as:")
  for key, temp in selection.items():
    print(f"{key:<20} {temp}")
  if 'C0' not in selection:
    print(
        "Required sub-module 'C0' is missing. Please double check the provided MID '"
        + options.mid + "'")
    sys.exit(1)

  if "UOG_C-N" in selection:
    if not "UOG_N" in selection:
      print("#warning: using UOG_C-N sub-module without UOG_N")
    if max_carbon(selection.keys()) == 0:
      print(
          "#warning: using UOG_C-N sub-module without carbon containing sub-module"
      )

  if "PAH_BLOCK" in selection:
    min_PAH = ["C0", "C1-C2", "C3-C4"]
    for dep in min_PAH:
      if dep not in selection:
        print("#warning: using PAH_BLOCK without '" + dep +
              "' is not recommended.")

  all_ht = True
  all_lt_ht = True
  n_temp_independent = 0

  submodules_filenames = get_submodule_filenames(options.submodules_dir)

  ht_files = set(list(submodules_filenames["HT"].values()))
  ltht_files = set(list(submodules_filenames["LT-HT"].values()))
  temp_independent = ht_files & ltht_files

  for key, temp in selection.items():
    if temp == "HT" and submodules_filenames["HT"][key] not in temp_independent:
      #print(key, "NOT LT-HT")
      all_lt_ht = False
    elif temp == "LT-HT" and submodules_filenames["LT-HT"][
        key] not in temp_independent:
      #print(key, "NOT HT")
      all_ht = False
    elif temp != "HT" and temp != "LT-HT":
      raise Exception("Unexpected key '" + temp + "'")
    else:
      #print(key, "temperature-independent")
      n_temp_independent += 1

  if n_temp_independent == len(selection):
    all_ht = False
    all_lt_ht = False
  elif all_lt_ht and all_ht:
    raise Exception("all HT and all LT-HT is impossible. There is a bug here.")

  grouped_combos = defaultdict(dict)
  cnum = max_carbon(selection.keys())
  grouped_combos[cnum]["modules"] = [selection]
  grouped_combos[cnum]["mid"] = [options.mid]
  temp_str = ""
  if all_ht:
    temp_str = "_HT"
    print("MID '" + options.mid + "' is a HT model")
    grouped_combos[cnum]["temperature"] = ["HT"]
  elif all_lt_ht:
    temp_str = "_LT-HT"
    print("MID '" + options.mid + "' is a LT-HT model")
    grouped_combos[cnum]["temperature"] = ["LT-HT"]
  else:
    if n_temp_independent == len(selection):
      print("MID '" + options.mid +
            "' combines temperature-independent sub-modules")
    else:
      print("MID '" + options.mid + "' combines HT and LT-HT sub-modules")
    grouped_combos[cnum]["temperature"] = [""]

  grouped_combos[cnum]["output_chunks"] = [
      sanitize_filename(list(selection.keys())) + temp_str
  ]

  #print("output_chunks", grouped_combos[cnum]["output_chunks"])
  grouped_combos[cnum]["output_dir"] = options.output_dir
  return grouped_combos


def check_duplicate(used_paths):
  # Find duplicates
  seen = set()
  duplicates = set()
  for path in used_paths:
    if path in seen:
      duplicates.add(path)
    else:
      seen.add(path)

  if duplicates:
    print("duplicate paths found:")
    for dup in duplicates:
      print(dup)
    print(f"#error: duplicate file paths detected in yaml input")
    sys.exit(1)


def get_relative_submodule_paths(used_paths, submodules_dir):
  if submodules_dir[-1] != os.sep:
    submodules_dir += os.sep
  used_paths_rel = {}
  # Remove the prefix to get the short (relative) path
  for p_abs in used_paths:
    if not p_abs.startswith(submodules_dir):
      raise Exception(
          f"Used path {p_abs} does not start with submodules dir {submodules_dir}"
      )
    p_rel = p_abs[len(submodules_dir):]
    if p_rel in used_paths_rel:
      raise Exception("Unexpected duplicate '" + p_rel + "'")
    used_paths_rel[p_rel] = p_abs
  return used_paths_rel


def construct_path_to_key_temp(submodules_filenames, submodules_dir):
  # --- Build mapping of file paths to keys and temperatures ---
  path_to_key_temp = {}
  # IMPORTANT: submodules_filenames is ORDERED!
  for temp in submodules_filenames:
    for key, p in submodules_filenames[temp].items():
      p_rel = get_relative_submodule_paths([p], submodules_dir)
      path_to_key_temp[list(p_rel.keys())[0]] = (key, temp)

  # Also accept both variants of C0 and C1-C2 (Cantera and non-Cantera) as aliases
  alias_candidates = [
      (os.path.join("UOG", "LT-HT", "UOG_C0_LT-HT.MECH"), ("C0", "LT-HT")),
      (os.path.join("UOG", "LT-HT",
                    "UOG_C0_LT-HT_Cantera.MECH"), ("C0", "LT-HT")),
      (os.path.join("UOG", "LT-HT",
                    "UOG_C1-C2_LT-HT.MECH"), ("C1-C2", "LT-HT")),
      (os.path.join("UOG", "LT-HT",
                    "UOG_C1-C2_LT-HT_Cantera.MECH"), ("C1-C2", "LT-HT")),
  ]
  for rel_hint, key_temp in alias_candidates:
    abs_path = os.path.normcase(
        os.path.abspath(
            os.path.normpath(os.path.join(submodules_dir, rel_hint))))
    if os.path.isfile(abs_path):
      rel_map = get_relative_submodule_paths([abs_path], submodules_dir)
      rel_path = list(rel_map.keys())[0]
      # Don't overwrite if it already exists with same meaning
      if rel_path not in path_to_key_temp:
        path_to_key_temp[rel_path] = key_temp

  return path_to_key_temp


def check_HT_and_LT_HT_combi(used_paths_rel, path_to_key_temp, yaml_file_path):
  seen_keys = {}
  for p in used_paths_rel:
    if p not in path_to_key_temp:
      print("unknown sub-module '" + used_paths_rel[p] +
            "'. Check your input or update the compiler script.")
      sys.exit(1)
    smod = path_to_key_temp[p][0]
    if smod in seen_keys:
      print("#error: HT and LT-HT version of the sub-module '" + smod +
            "' must not be combined.")
      print("        Conflicting files:")
      print("        '" + used_paths_rel[p] + "'")
      print("        '" + seen_keys[path_to_key_temp[p][0]] + "'")
      print("check your YAML input file '" + yaml_file_path + "'")
      sys.exit(1)
    seen_keys[path_to_key_temp[p][0]] = used_paths_rel[p]


def normalize_and_check_submodule_paths(submodules_files, submodules_dir,
                                        yaml_file_path):
  global CANTERA_MODE

  # Normalize directory path
  submodules_dir_copy = os.path.normcase(
      os.path.abspath(os.path.normpath(submodules_dir)))

  # Normalize input file paths
  submodules_files.core = os.path.normcase(
      os.path.abspath(os.path.normpath(submodules_files.core)))
  for i in range(len(submodules_files.submodules)):
    submodules_files.submodules[i] = os.path.normcase(
        os.path.abspath(os.path.normpath(submodules_files.submodules[i])))

  # Decide Cantera mode from the core BEFORE building the mapping
  core_rel_map = get_relative_submodule_paths([submodules_files.core],
                                              submodules_dir_copy)
  core_rel = list(core_rel_map.keys())[0]
  core_name = os.path.basename(core_rel).lower()
  if core_name.endswith("uog_c0_lt-ht_cantera.mech"):
    CANTERA_MODE = True
  elif core_name.endswith("uog_c0_lt-ht.mech"):
    CANTERA_MODE = False
  else:
    print("#error: core file does not look like a recognized C0 sub-module:")
    print("       '" + core_rel + "'")
    sys.exit(1)

  # Build mapping AFTER CANTERA_MODE is set (self-consistent mapping)
  submodules_filenames = get_submodule_filenames(submodules_dir_copy)

  # Validate and classify used paths
  used_paths = [submodules_files.core] + submodules_files.submodules
  check_duplicate(used_paths)

  path_to_key_temp = construct_path_to_key_temp(submodules_filenames,
                                                submodules_dir_copy)
  used_paths_rel = get_relative_submodule_paths(used_paths,
                                                submodules_dir_copy)
  check_HT_and_LT_HT_combi(used_paths_rel, path_to_key_temp, yaml_file_path)

  # Forbid mixing Cantera/non-Cantera C1-C2 variants against selected core
  has_c12_can = any(
      os.path.basename(k).lower().endswith("uog_c1-c2_lt-ht_cantera.mech")
      for k in used_paths_rel.keys())
  has_c12_non = any(
      os.path.basename(k).lower().endswith("uog_c1-c2_lt-ht.mech")
      for k in used_paths_rel.keys())

  if has_c12_can and has_c12_non:
    print(
        "#error: Both Cantera and non-Cantera versions of C1-C2 were selected."
    )
    print("       Please select only one of:")
    print("         UOG/LT-HT/UOG_C1-C2_LT-HT.MECH")
    print("         UOG/LT-HT/UOG_C1-C2_LT-HT_Cantera.MECH")
    print("       YAML file: '" + yaml_file_path + "'")
    sys.exit(1)

  if CANTERA_MODE and has_c12_non:
    print(
        "#error: Cantera-compatible C0 core requires the Cantera-compatible C1-C2 sub-module."
    )
    print("       Selected core : UOG/LT-HT/UOG_C0_LT-HT_Cantera.MECH")
    print("       Incompatible : UOG/LT-HT/UOG_C1-C2_LT-HT.MECH")
    print("       YAML file: '" + yaml_file_path + "'")
    sys.exit(1)
  if (not CANTERA_MODE) and has_c12_can:
    print(
        "#error: Non-Cantera C0 core must not be combined with a Cantera-compatible C1-C2."
    )
    print("       Selected core : UOG/LT-HT/UOG_C0_LT-HT.MECH")
    print("       Incompatible : UOG/LT-HT/UOG_C1-C2_LT-HT_Cantera.MECH")
    print("       YAML file: '" + yaml_file_path + "'")
    sys.exit(1)

  # Build selection and sorted submodules using the used paths and path_to_key_temp
  selection = {}
  selected_by_key = {}
  for p_rel, p_abs in used_paths_rel.items():
    if p_rel not in path_to_key_temp:
      print("unknown sub-module '" + used_paths_rel[p_rel] +
            "'. Check your input or update the compiler script.")
      sys.exit(1)
    smod, temp = path_to_key_temp[p_rel]
    if smod not in selected_by_key:
      selected_by_key[smod] = (temp, p_abs)

  sorted_submodules_files = []
  for smod in ORDERED_KEYS:
    if smod in selected_by_key:
      selection[smod] = selected_by_key[smod][0]
      if smod != "C0":
        sorted_submodules_files.append(selected_by_key[smod][1])

  submodules_files.submodules = sorted_submodules_files
  return submodules_files, selection


def get_grouped_combos(options):
  try:
    from chemmodkit.input import make_submodulefiles_from_yaml
    submodules_files = make_submodulefiles_from_yaml(options.yaml_file_path,
                                                     options.submodules_dir)
  except ImportError:
    print(
        "ERROR: Could not find chemmodkit.input.make_submodulefiles_from_yaml."
    )
    sys.exit(1)

  submodules_files, selection = normalize_and_check_submodule_paths(
      submodules_files, options.submodules_dir, options.yaml_file_path)
  used_paths = [submodules_files.core] + submodules_files.submodules

  midgen = MID(ORDERED_KEYS, BINARY_KEYS, version=VERSION)
  id_str = midgen.combo_to_id(selection)
  print("Generated MID:", id_str)

  grouped_combos = defaultdict(dict)
  cnum = max_carbon(selection.keys())
  grouped_combos[cnum]["modules"] = [selection]
  grouped_combos[cnum]["mid"] = [id_str]
  temp_str = ""
  if is_ht(used_paths, options.submodules_dir):
    temp_str = "_HT"
    grouped_combos[cnum]["temperature"] = ["HT"]
  elif is_ltht(used_paths, options.submodules_dir):
    temp_str = "_LT-HT"
    grouped_combos[cnum]["temperature"] = ["LT-HT"]
  else:
    grouped_combos[cnum]["temperature"] = [""]

  grouped_combos[cnum]["output_chunks"] = [
      sanitize_filename(list(selection.keys())) + temp_str
  ]

  grouped_combos[cnum]["output_dir"] = options.output_dir

  return grouped_combos
