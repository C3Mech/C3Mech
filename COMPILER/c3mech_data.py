import os
import re
from itertools import combinations
from collections import defaultdict
import string

VERSION = "4.0"
DMC_EC_FEW = True

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
    "NUIG_N": set(["C0"]),
    "NUIG_C-N": set(["C0", "C1-C2", "NUIG_N"]),
    "PAH_BLOCK": set(["C0", "C1-C2", "C3-C4", "C5cy", "C6cy"]),  # , "C5"
}


def init_identifier_max(dependencies):
  return tuple(dependencies.keys())


# If a key was binary (or ternary), keep its base fixed forever.
ORDERED_KEYS = init_identifier_max(DEPENDENCIES)
BINARY_KEYS = {'LLNL_BLOCK_DMC_EC', 'C1-C2', 'PAH_BLOCK', 'C0', 'NUIG_N'}

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
    #('NUIG_C-N', ''), # handled separately
    ('NUIG_N', 'N'),
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
  base_moduldes_NUIG_HTLT = [
      os.path.join("NUIG", "LT-HT", "NUIG_" + "C0" + "_LT-HT_Cantera.MECH")
  ] + [
      os.path.join("NUIG", "LT-HT", "NUIG_" + b + "_LT-HT.MECH")
      for b in get_base_modules()
  ]
  base_moduldes_NUIG_HT = base_moduldes_NUIG_HTLT[:2] + [
      os.path.join("NUIG", "HT", "NUIG_" + b + "_HT.MECH")
      for b in get_base_modules()[1:]
  ]
  LLNL_base_modules_HT = [os.path.join("LLNL", "LLNL_BLOCK_HT.CKI")]
  LLNL_base_modules_HTLT = [os.path.join("LLNL", "LLNL_BLOCK.CKI")]

  #optional_modules_HT = [
  #    os.path.join("NUIG", "HT", "NUIG_" + "N" + "_HT.MECH")
  #]

  #optional_modules_HTLT = [
  #    os.path.join("NUIG", "LT-HT", "NUIG_" + "N" + "_LT-HT.MECH")
  #]
  optional_modules = [
      os.path.join("NUIG", "LT-HT", "NUIG_N_LT-HT.MECH"),
      os.path.join("ITV_POLIMI", "PAH_BLOCK.CKI"),
      os.path.join("LLNL", "LLNL_BLOCK_DMC_EC.CKI")
  ]

  required_extension_HT = [
      os.path.join("NUIG", "HT", "NUIG_" + "C-N" + "_HT.MECH")
  ]
  required_extension_HTLT = [
      os.path.join("NUIG", "LT-HT", "NUIG_" + "C-N" + "_LT-HT.MECH")
  ]

  modules_ht = base_moduldes_NUIG_HT + LLNL_base_modules_HT + optional_modules + required_extension_HT  # + optional_modules_HT
  modules_htlt = base_moduldes_NUIG_HTLT + LLNL_base_modules_HTLT + optional_modules + required_extension_HTLT  #  + optional_modules_HTLT

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
      ('NUIG_N' in s),
      ('NUIG_C-N' in s),
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
    aux = smod + "." if (smod == "LLNL_BLOCK") else smod
    if smod == "LLNL_BLOCK" and label == "HT":
      aux = "LLNL_BLOCK_HT"
    # First pass: look for 'smod_' and 'NUIG'
    for mod in modules_list:
      if smod + "_" in mod and "NUIG" in mod:
        if matched_mod is not None:
          raise Exception(f"second match '{smod}' in {label}")
        matched_mod = mod

    # Second pass: look for auxiliary name anywhere
    if matched_mod is None:
      for mod in modules_list:
        if aux in mod:
          #print(mod)
          if matched_mod is not None:
            raise Exception(f"second match '{smod}' in {label}")
          matched_mod = mod

    if matched_mod is None:
      print(f"no match for {label}")

    return matched_mod

  submodules_ht = {}
  submodules_htlt = {}

  for smod in submodules:
    #print(f"matching '{smod}'")

    ht_match = find_match(smod, modules_ht, "HT")
    if ht_match:  # Only add if found
      submodules_ht[smod] = ht_match

    htlt_match = find_match(smod, modules_htlt, "HTLT")
    if htlt_match:  # Only add if found
      submodules_htlt[smod] = htlt_match

    #print("")

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

    valid_combos = []

    # Try all possible subsets
    for i in range(1, len(keys) + 1):
      for combo in combinations(keys, i):
        s = set(combo)
        if all(dependencies[k].issubset(s) for k in s):
          valid_combos.append(sorted(s))

    return valid_combos

  combinations_list = generate_valid_combinations(DEPENDENCIES)
  combinations_final = []
  for combo in combinations_list:
    #print(combo)
    has_carbon = False
    if (set(get_base_modules()) & set(combo)
        or set(["LLNL_BLOCK", "LLNL_BLOCK_DMC_EC", "PAH_BLOCK"]) & set(combo)):
      has_carbon = True

    if (has_carbon and "NUIG_N" in combo) and not "NUIG_C-N" in combo:
      continue
    if DMC_EC_FEW and ((
        (max_carbon(combo) > 2 or "NUIG_N" in combo) and max_carbon(combo) < 8)
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
  # quit()
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
    if self.version != "4.0":
      raise ValueError(
          "MID is currently assumed to only be used for C3MechV4.0")

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
      quit()
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
  selection = midgen.id_to_combo(options.mid)

  print("MID '" + options.mid + "' decoded as:")
  for key, temp in selection.items():
    print(f"{key:<20} {temp}")
  if 'C0' not in selection:
    print(
        "Required sub-module 'C0' is missing. Please double check the provided MID '"
        + options.mid + "'")
    quit()

  if "NUIG_C-N" in selection:
    if not "NUIG_N" in selection:
      print("#warning: using NUIG_C-N sub-module without NUIG_N")
    if max_carbon(selection.keys()) == 0:
      print(
          "#warning: using NUIG_C-N sub-module without carbon containing sub-module"
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
    quit(f"#error: duplicate file paths detected in yaml input")


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
  return path_to_key_temp


def check_HT_and_LT_HT_combi(used_paths_rel, path_to_key_temp, options):
  seen_keys = {}
  for p in used_paths_rel:
    if p not in path_to_key_temp:
      quit("unknown sub-module '" + used_paths_rel[p] +
           "'. Check your input or update the compiler script.")
    smod = path_to_key_temp[p][0]
    if smod in seen_keys:
      print("#error: HT and LT-HT version of the sub-module '" + smod +
            "' must not not be combined.")
      print("        Conflicting files:")
      print("        '" + used_paths_rel[p] + "'")
      print("        '" + seen_keys[path_to_key_temp[p][0]] + "'")
      print("check your YAML input file '" + options.yaml_file_path + "'")
      quit()
    seen_keys[path_to_key_temp[p][0]] = used_paths_rel[p]


def normalize_and_check_submodule_paths(submodules_files, submodules_dir):
  submodules_dir_copy = os.path.normcase(
      os.path.abspath(os.path.normpath(submodules_dir)))
  submodules_filenames = get_submodule_filenames(submodules_dir_copy)

  submodules_files.core = os.path.normcase(
      os.path.abspath(os.path.normpath(submodules_files.core)))
  for i in range(len(submodules_files.submodules)):
    submodules_files.submodules[i] = os.path.normcase(
        os.path.abspath(os.path.normpath(submodules_files.submodules[i])))

  used_paths = [submodules_files.core] + submodules_files.submodules
  check_duplicate(used_paths)

  path_to_key_temp = construct_path_to_key_temp(submodules_filenames,
                                                submodules_dir_copy)
  used_paths_rel = get_relative_submodule_paths(used_paths,
                                                submodules_dir_copy)
  check_HT_and_LT_HT_combi(used_paths_rel, path_to_key_temp, options)

  selection = {}
  sorted_submodules_files = []
  for smod in ORDERED_KEYS:
    for temp in submodules_filenames:
      p_abs = submodules_filenames[temp][smod]
      p_rel = list(
          get_relative_submodule_paths([p_abs], submodules_dir_copy).keys())[0]
      if p_rel in used_paths_rel and smod not in selection:
        selection[smod] = temp
        if smod != "C0":
          sorted_submodules_files.append(used_paths_rel[p_rel])

  submodules_files.submodules = sorted_submodules_files
  return submodules_files


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

  submodules_files = normalize_and_check_submodule_paths(
      options.submodules_dir)
  used_paths = [submodules_files.core] + submodules_files.submodules

  midgen = MID(ORDERED_KEYS, BINARY_KEYS, version=VERSION)
  id_str = midgen.combo_to_id(selection)
  print("Generated MID:", id_str)

  grouped_combos = defaultdict(dict)
  cnum = max_carbon(selection.keys())
  grouped_combos[cnum]["modules"] = [selection]
  grouped_combos[cnum]["mid"] = [id_str]
  temp_str = ""
  if is_ht(used_paths, submodules_dir_copy):
    temp_str = "_HT"
    grouped_combos[cnum]["temperature"] = ["HT"]
  elif is_ltht(used_paths, submodules_dir_copy):
    temp_str = "_LT-HT"
    grouped_combos[cnum]["temperature"] = ["LT-HT"]
  else:
    grouped_combos[cnum]["temperature"] = [""]

  grouped_combos[cnum]["output_chunks"] = [
      sanitize_filename(list(selection.keys())) + temp_str
  ]

  grouped_combos[cnum]["output_dir"] = options.output_dir

  return grouped_combos
