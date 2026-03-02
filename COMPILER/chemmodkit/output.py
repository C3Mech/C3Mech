import datetime
import os
import re
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

pruned_comment = "! AUTOMATIC PRUNING ! "

from . import input as inp
from . import reaction as rxn

_REACTION_KEYWORD_ALIASES = {
    "LOW": "LOW",
    "LOWMX": "LOWMX",
    "LOWSP": "LOWSP",
    "HIGH": "HIGH",
    "HIGHMX": "HIGHMX",
    "HIGHSP": "HIGHSP",
    "TROE": "TROE",
    "TROEMX": "TROEMX",
    "TROESP": "TROESP",
    "SRI": "SRI",
    "PLOG": "PLOG",
    "CHEB": "CHEB",
    "TCHEB": "TCHEB",
    "PCHEB": "PCHEB",
    "DUP": "DUPLICATE",
    "DUPLICATE": "DUPLICATE",
}


@dataclass(frozen=True)
class ReactionMatchSignature:
  """Subset-check key used for HT vs LT-HT reaction matching.

  Note: "multiple PLOG/CHEB/..." means repeated lines with the same keyword,
  not a plural keyword token.
  """

  canonical: str
  explicit_dependence: tuple
  tb_efficiencies: tuple
  keywords: tuple


@dataclass(frozen=True)
class ParentReactionTrace:
  line_no: int
  is_comment: bool
  reaction_type: str
  reaction_definition: str
  raw_line: str


@dataclass(frozen=True)
class RestrictiveMatchWarning:
  ht_base: str
  parent_base: str
  ht_reaction: str
  parent_reaction: str
  parent_line: int


@dataclass(frozen=True)
class UnmatchedReactionDetail:
  key: tuple
  ht_base: str
  parent_base: str
  ht_reaction: str
  ht_trace: ParentReactionTrace
  parent_traces: tuple
  reason: str


def write_species_list(species_list, species_pruned, filename):
  # write spc str
  commentstr = '\n!+++++++++++++++++++++ '
  speciesallstr = '\n!\\SPECIES_MODULE: ALL '
  speciesendstr = '\n!\\END_SPECIES_MODULE: ALL '
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
  for spc in species_list:
    if spc in species_pruned:
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


def detect_cantera_mode(submodules_filenames):
  """
  Prefer 'LT-HT' entry; fall back to 'HT' if needed.
  Returns True if the core_path basename contains 'cantera', else False.
  """
  for temp in ("LT-HT", "HT"):
    if temp in submodules_filenames and "C0" in submodules_filenames[temp]:
      core_path = submodules_filenames[temp]["C0"]
      return "cantera" in os.path.basename(core_path).lower()
  return False


def get_subtitel_with_directory(prev_cnum, cnum, directory):
  label = " [" + directory + "/](" + directory + "/) "
  if prev_cnum + 1 != cnum:
    label += f"(Number of carbon atoms: {prev_cnum+1}–{cnum})" if cnum <= 7 else "(Number of carbon atoms: 8+)"
  else:
    label += f"(Number of carbon atoms: {cnum})" if cnum <= 7 else f"(Number of carbon atoms: 8+)"
  return label


def generate_readme(grouped_selections, columns, counters):
  # Print one table per carbon group (sorted by increasing C count)
  readme = list()
  readme.append("# Precompiled models ")
  readme.append("")
  readme.append(
      "This directory provides precompiled chemical kinetic sub-models of C3MechV4.0.1, "
      +
      "tailored to specific fuel compositions and conditions, and the full " +
      "version of C3MechV4.0.1. The sub-models were compiled from the sub-modules "
      +
      "in the directory [`SUBMODULES/`](../SUBMODULES/). The reactions in the "
      + "sub-modules are grouped " +
      "based on the number of carbon atoms in the species (C0, C1-C2, C3-C4, C5, "
      +
      "C6, C7, C8+, C5CY, C6CY), with aromatic species being managed separately. "
      +
      "Here, 'CY' refers to non-aromatic, cyclic fuel components. Additionally, sub-modules "
      +
      "for dimethyl carbonate and ethylene carbonate (DMC+EC), nitrogen-containing "
      +
      "species (N), and polycyclic aromatic hydrocarbons (PAH) are available. The tables "
      +
      "below list all precompiled sub-models, where in this subdirectory \"N\" refers to the "
      + "combined N- and N-C sub-modules " +
      "if a sub-model contains carbon atoms.\n " +
      "\nMany sub-models are available as smaller high-temperature (HT) versions, which "
      +
      "are suitable for simulations of unstretched premixed and counterflow flames, "
      +
      "high-temperature flow reactors, and shock tubes. Low-temperature (LT) chemistry "
      +
      "is, for example, required to simulate jet-stirred reactors, flow reactors under "
      +
      "lower-temperature conditions, and rapid compression machine (RCM) experiments. "
      +
      "The columns NS(HT/LT-HT) and NR(HT/LT-HT) in the tables below refer to the number "
      + "of species and reactions in the respective sub-models.\n " +
      "\nEach HT and LT-HT version is assigned a unique model ID (MID(HT/LT-HT)) that encodes "
      +
      "the specific sub-module combination; if a single model is used across all temperatures, "
      +
      "the counts (NS and NR) and MIDs are the same. If you need a combination not listed here, "
      +
      "see [`COMPILER/`](../COMPILER/) directory for an easy-to-use script to create "
      + "custom sub-models.")
  readme.append("")
  readme.append("## Notes and recommendations ")
  readme.append(
      "- **Selecting a sub-model:** Selecting a sub-model with only the necessary sub-modules facilitates and speeds up kinetic simulations. "
  )
  readme.append(
      "- **User responsibility:** The user must select an _appropriate_ sub-model for a simulation case. "
  )
  readme.append("")
  readme.append("For questions or suggestions, please open an issue or ")
  readme.append("[contact us](mailto:r.langer@itv.rwth-aachen.de). ")
  readme.append("")
  readme.append("## Available precompiled models ")
  readme.append("")
  readme.append(
      "You can download individual files in your web browser or clone all files. "
      + "For each sub-model, there are CHEMKIN (.CKI, .THERM, and .TRAN) " +
      "and Cantera (.yaml) files. The .CKI files are provided as CHEMKIN-PRO/"
      + "OpenSMOKE++-compatible versions " +
      "as well as Cantera/FlameMaster-compatible versions " +
      "(filename contains the string 'Cantera'). " +
      "Once you found a suitable sub-model, you can use its MID to " +
      "find the corresponding files. It is recommended to refer to a " +
      " model's MID when using a sub-model of C3MechV4.0.1. " + "")

  prev_cnum = -1
  for cnum, group_combos in grouped_selections.items():

    # Print table per group to stdout (optional)
    label = get_subtitel_with_directory(
        prev_cnum, cnum, os.path.basename(group_combos["output_dir"]))
    print_markdown_table(readme,
                         group_combos,
                         columns,
                         title=label,
                         counters=counters)
    prev_cnum = cnum

  return readme


def print_markdown_table(readme,
                         all_combos,
                         columns,
                         title=None,
                         counters=None):
  YES = "✓"
  NO = " "
  columns_aux = columns.copy()
  if counters != None:
    columns_aux += [("NS(HT/LT-HT)", "NS(HT/LT-HT)"),
                    ("NR(HT/LT-HT)", "NR(HT/LT-HT)"),
                    ("MID(HT/LT-HT)", "MID(HT/LT-HT)")]

  # print("len(counters)", len(counters))
  # for mid in counters:
  #   print(mid)
  # print("len(combos)", len(combos))
  # print(combos)
  # for idx, data_dict in enumerate(all_combos['modules']):
  # for cnum, data_dict in combos:
  #     print(data_dict)
  #     mid = data_dict["mid"][cnum]
  #     selection = data_dict["modules"][cnum]
  # combos = [comb for comb in combos['modules']]

  # Carbon-group directory name, e.g. "C0", "C1-C2", ...
  group_dir = os.path.basename(all_combos["output_dir"])

  unique = {}
  for idx, selection in enumerate(all_combos["modules"]):
    modules_keys = tuple(sorted(set(list(selection.keys()))))
    if modules_keys not in unique:
      unique[modules_keys] = {}

    # Derive combination directory name from output_chunks and temperature
    name_with_temp = all_combos["output_chunks"][idx]
    temp = all_combos["temperature"][idx]
    if temp in ("HT", "LT-HT"):
      combo_dir = name_with_temp.rsplit("_", 1)[0]
    else:
      combo_dir = name_with_temp

    # Store combo_dir once per modules_keys; verify consistency
    if "combo_dir" not in unique[modules_keys]:
      unique[modules_keys]["combo_dir"] = combo_dir
    elif unique[modules_keys]["combo_dir"] != combo_dir:
      raise Exception("Inconsistent combo_dir for " + str(modules_keys))

    if all_combos["temperature"][idx] == "HT":
      if "HT" in unique[modules_keys] and unique[modules_keys][
          "HT"] != all_combos["mid"][idx]:
        raise Exception("HT with unexpected MID '" + all_combos["mid"][idx] +
                        "' for " + str(modules_keys))

      mid = all_combos["mid"][idx]
      if modules_keys != tuple(sorted(set(list(counters[mid][0].keys())))):
        raise Exception("Inconsistent selection for " + str(modules_keys))

      unique[modules_keys]["HT"] = {}
      unique[modules_keys]["HT"]["MID"] = mid
      unique[modules_keys]["HT"]["NS"] = counters[mid][1]
      unique[modules_keys]["HT"]["NR"] = counters[mid][2]
    elif all_combos["temperature"][idx] == "LT-HT":
      if "LT-HT" in unique[modules_keys] and unique[modules_keys][
          "LT-HT"] != all_combos["mid"][idx]:
        raise Exception("LT-HT with unexpected MID '" +
                        all_combos["mid"][idx] + "' for " + str(modules_keys))

      mid = all_combos["mid"][idx]
      if modules_keys != tuple(sorted(set(list(counters[mid][0].keys())))):
        raise Exception("Inconsistent selection for " + str(modules_keys))
      unique[modules_keys]["LT-HT"] = {}
      unique[modules_keys]["LT-HT"]["MID"] = mid
      unique[modules_keys]["LT-HT"]["NS"] = counters[mid][1]
      unique[modules_keys]["LT-HT"]["NR"] = counters[mid][2]
    else:
      raise Exception("Unexpected temperature field '" +
                      all_combos["temperature"][idx] + "'")

  # --- Sort section ---
  if counters is not None:
    # Extract HT counts and build sortable tuples
    sort_tuples = []
    for module_key in unique:
      # sort by number of species in the HT version
      sort_tuples.append((unique[module_key]["HT"]["NS"], module_key))
    # Sort by HT count ascending
    sort_tuples.sort()
    # Reorder combos and counters accordingly
    sorted_combos = [i for _, i in sort_tuples]
    sorted_ns = [
        str(unique[i]["HT"]["NS"]) + "/" + str(unique[i]["LT-HT"]["NS"])
        for _, i in sort_tuples
    ]
    sorted_nr = [
        str(unique[i]["HT"]["NR"]) + "/" + str(unique[i]["LT-HT"]["NR"])
        for _, i in sort_tuples
    ]

    # Turn MID(HT/LT-HT) into a link to the combination directory
    sorted_mid = []
    for _, key in sort_tuples:
      mid_ht = str(unique[key]["HT"]["MID"])
      mid_lt = str(unique[key]["LT-HT"]["MID"])
      combo_dir = unique[key]["combo_dir"]
      # new layout: C-group/combo_dir/ (Chemkin/ and Cantera/ below)
      target_rel = f"{group_dir}/{combo_dir}/"
      link_text = f"{mid_ht}/{mid_lt}"
      link_md = f"[{link_text}]({target_rel})"
      sorted_mid.append(link_md)
  else:
    sorted_combos = [modules_keys for modules_keys in unique]
    sorted_ns = []
    sorted_nr = []
    sorted_mid = []

  # --- Compute column widths, including cell content lengths ---
  col_widths = [max(len(colname), 1) for _, colname in columns_aux]
  if counters is not None and sorted_combos:
    # NS column
    idx_ns = len(columns_aux) - 3
    col_widths[idx_ns] = max(
        col_widths[idx_ns],
        max(len(s) for s in sorted_ns) if sorted_ns else 1,
    )
    # NR column
    idx_nr = len(columns_aux) - 2
    col_widths[idx_nr] = max(
        col_widths[idx_nr],
        max(len(s) for s in sorted_nr) if sorted_nr else 1,
    )
    # MID column
    idx_mid = len(columns_aux) - 1
    col_widths[idx_mid] = max(
        col_widths[idx_mid],
        max(len(s) for s in sorted_mid) if sorted_mid else 1,
    )

  header = "| " + " | ".join(
      f"{colname:<{w}}"
      for (_, colname), w in zip(columns_aux, col_widths)) + " |"

  sep = "|" + "|".join(f":{'-'*max(1,w)}:" for w in col_widths) + "|"

  rows = []
  count = 0
  for combo in sorted_combos:
    s = set(combo)
    n_col_check = (YES if "UOG_N" in s else NO)

    row_cells = []
    for i, (key, _) in enumerate(columns_aux):
      if counters is not None and i == len(columns_aux) - 3:
        tmp = sorted_ns[count]
        row_cells.append(f"{tmp:^{col_widths[i]}}")  # center align
      elif counters is not None and i == len(columns_aux) - 2:
        tmp = sorted_nr[count]
        row_cells.append(f"{tmp:^{col_widths[i]}}")  # center align
      elif counters is not None and i == len(columns_aux) - 1:
        tmp = sorted_mid[count]
        # LEFT align the MID link so '[' lines up
        row_cells.append(f"{tmp:<{col_widths[i]}}")
      else:
        if key == "UOG_N":
          cell = n_col_check
        else:
          cell = YES if key in s else NO
        row_cells.append(f"{cell:^{col_widths[i]}}")  # center align

    row_str = "| " + " | ".join(row_cells) + " |"
    rows.append(row_str)
    count += 1

  if title:
    readme.append(f"\n### {title}\n")

  readme.append(header)
  readme.append(sep)
  readme.append('\n'.join(rows))

  # rows = []
  # count = 0
  # for combo in combos:
  #   s = set(combo)
  #   n_col_check = (YES if "UOG_N" in s else NO)

  #   row_cells = []
  #   for i, (key, _) in enumerate(columns_aux):
  #     if counters != None and i == len(columns_aux) - 2:
  #       tmp = counters["NS"][count]
  #       row_cells.append(f"{tmp:^{col_widths[i]}}")  # center align
  #     elif counters != None and i == len(columns_aux) - 1:
  #       tmp = counters["NR"][count]
  #       row_cells.append(f"{tmp:^{col_widths[i]}}")  # center align
  #     else:
  #       if key == "UOG_N":
  #         cell = n_col_check
  #       else:
  #         cell = YES if key in s else NO
  #       row_cells.append(f"{cell:^{col_widths[i]}}")  # center align

  #   row_str = "| " + " | ".join(row_cells) + " |"
  #   rows.append(row_str)
  #   count += 1

  # if title:
  #   readme.append(f"\n### {title}\n")

  # readme.append(header)
  # readme.append(sep)
  # readme.append('\n'.join(rows))


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


def insert_header(lines, header_filename):
  with open(header_filename, 'r') as f:
    for line in f:
      lines.append(line)
    lines.append("\n")
    lines.append("\n")


def insert_time(lines, filetype, name, datetime):
  lines.append('! ' + filetype + ' data for ' + name +
               ', generated on {0:%d/%m/%Y %H:%M:%S}.\n'.format(datetime) +
               '\n')


def insert_submodule_list(lines, submodules_files, mid):
  lines.append('! The following sub-modules were considered in this file:\n')
  lines.append('! - ' + os.path.basename(submodules_files.core) + '\n')
  for file_path in submodules_files.submodules:
    lines.append('! - ' + os.path.basename(file_path) + '\n')
  lines.append("\n")
  lines.append('! model ID (MID): ' + mid)
  lines.append("\n")


def insert_boiler_plate(filetype, name, submodules_files, datetime, mid,
                        header_filename):
  lines = []
  insert_header(lines, header_filename)
  insert_time(lines, filetype, name, datetime)
  insert_submodule_list(lines, submodules_files, mid)
  return lines


def ascii_space(s: str) -> str:
  """Return s with every non-ASCII char replaced by a space."""
  return ''.join(ch if ord(ch) < 128 else ' ' for ch in s)


def _is_ht_submodule_file(path):
  base = os.path.basename(path).upper()
  return base == "LLNL_BLOCK_HT.CKI" or ("_HT." in base and
                                         "_LT-HT." not in base)


def _infer_ltht_parent_path(ht_path):
  ht_base = os.path.basename(ht_path)
  upper = ht_base.upper()
  if upper == "LLNL_BLOCK_HT.CKI":
    parent_base = "LLNL_BLOCK.CKI"
  else:
    parent_base = re.sub(r"_HT(\.[^.]+)$",
                         r"_LT-HT\1",
                         ht_base,
                         flags=re.IGNORECASE)
    if parent_base == ht_base:
      return None

  candidate = ht_path.replace(os.sep + "HT" + os.sep,
                              os.sep + "LT-HT" + os.sep, 1)
  candidate = os.path.join(os.path.dirname(candidate), parent_base)
  return os.path.normcase(os.path.normpath(candidate))


def _resolve_ht_parent_map(submodules_files):
  ht_parent_map = {}
  for file_path in [submodules_files.core] + list(submodules_files.submodules):
    if not _is_ht_submodule_file(file_path):
      continue
    parent_path = _infer_ltht_parent_path(file_path)
    if parent_path is None:
      raise Exception("Could not derive LT-HT parent for HT sub-module '" +
                      file_path + "'")
    if not os.path.isfile(parent_path):
      raise Exception("#error: expected LT-HT parent sub-module '" +
                      parent_path + "' for HT sub-module '" + file_path +
                      "' but it was not found")
    ht_parent_map[os.path.normcase(os.path.normpath(file_path))] = parent_path
  return ht_parent_map


def _build_parent_species_list(species_list, submodules_files, ht_parent_map):
  if not ht_parent_map:
    return species_list.copy(), species_list.copy()

  core_key = os.path.normcase(os.path.normpath(submodules_files.core))
  core_parent = ht_parent_map.get(core_key, submodules_files.core)
  submodules_parent = [
      ht_parent_map.get(os.path.normcase(os.path.normpath(path)), path)
      for path in submodules_files.submodules
  ]
  parent_files = inp.SubModulesFiles(core_parent, submodules_parent)
  parent_species = make_clean_species_list(parent_files)

  extended_species = species_list.copy()
  for sp in parent_species:
    if sp not in extended_species:
      extended_species[sp] = 0
  return parent_species, extended_species


def _parse_reactions_from_submodule(file_path, species_list):
  species_dict = {s: 0 for s in species_list}
  with open(file_path, 'r') as file:
    lines = file.readlines()
  reactions, reactions_check = {}, {}
  n_reactions, _, reactions, reactions_check, species_dict = inp.count_reactions(
      lines, os.path.basename(file_path), species_dict, reactions,
      reactions_check, print_summary=False)
  species_used = sum(1 for _, used in species_dict.items() if used != 0)
  return reactions, species_used, n_reactions


def _extract_reaction_keywords(rr):
  """Collect recognized keyword families for metadata matching.

  REV is intentionally ignored here:
  - REV/0 .../ is canonicalized to the same irreversible semantics as '=>'
  - REV/nonzero is already represented by an additional reverse reaction during
    parsing, so matching can rely on reaction instances instead of keyword text
  """
  keywords = set()
  for line in rr.get_orignal_CHEMKIN_text():
    clean = line.split('!', 1)[0].strip().upper()
    if not clean or '=' in clean:
      continue
    head = clean.split('/', 1)[0].strip()
    if not head:
      continue
    token = head.split()[0]
    if token == "REV":
      continue
    if token in _REACTION_KEYWORD_ALIASES:
      keywords.add(_REACTION_KEYWORD_ALIASES[token])
  return tuple(sorted(keywords))


def _reaction_match_signature(rr):
  canonical = rr.canonical_representation()[0]
  explicit_dependence = tuple(sorted(rr.explicit_dependence))
  tb_efficiencies = tuple(
      sorted((sp, round(val, 12)) for sp, val in rr.tb_efficiencies.items()))
  keywords = _extract_reaction_keywords(rr)
  return ReactionMatchSignature(canonical=canonical,
                                explicit_dependence=explicit_dependence,
                                tb_efficiencies=tb_efficiencies,
                                keywords=keywords)


def _reaction_equivalence_key(rr):
  # Canonical stoichiometry key independent of reaction direction/reversibility.
  return rr.canonical_representation()[1]


def _reaction_metadata_signature(rr):
  explicit_dependence = tuple(sorted(rr.explicit_dependence))
  tb_efficiencies = tuple(
      sorted((sp, round(val, 12)) for sp, val in rr.tb_efficiencies.items()))
  keywords = _extract_reaction_keywords(rr)
  return (explicit_dependence, tb_efficiencies, keywords)

def _force_irreversible_separator(text):
  if '<=>' in text:
    return text.replace('<=>', '=>', 1)
  if '=>' in text:
    return text
  if '=' in text:
    return text.replace('=', '=>', 1)
  return text


def _force_irreversible_separator_in_line(line):
  has_newline = line.endswith('\n')
  body = line[:-1] if has_newline else line
  if '!' in body:
    lhs, comment = body.split('!', 1)
    body = _force_irreversible_separator(lhs) + '!' + comment
  else:
    body = _force_irreversible_separator(body)
  return body + ('\n' if has_newline else '')


def _apply_irreversible_fixes(reactions, reaction_ids):
  for _, rr_list in reactions.items():
    for rr in rr_list:
      if id(rr) not in reaction_ids:
        continue
      rr.make_irreversible()
      rr.reaction_definition = _force_irreversible_separator(
          rr.reaction_definition)
      rr.reaction_string = _force_irreversible_separator(rr.reaction_string)
      rr.reaction_string_orig = _force_irreversible_separator_in_line(
          rr.reaction_string_orig)


def _build_reaction_trace_index(file_path, species_list):
  species_dict = {s: 0 for s in species_list}
  trace_index = defaultdict(list)
  with open(file_path, 'r') as file:
    for line_no, raw_line in enumerate(file, start=1):
      stripped = raw_line.strip()
      if not stripped:
        continue

      is_comment = stripped.startswith("!")
      if is_comment:
        candidate = stripped.lstrip("!").strip()
      else:
        candidate = stripped.split('!', 1)[0].strip()
      if "=" not in candidate:
        continue

      candidate_upper = candidate.upper()
      try:
        rr = rxn.ChemicalReaction(candidate_upper, candidate_upper, species_dict)
      except Exception:
        continue

      trace_index[_reaction_equivalence_key(rr)].append(
          ParentReactionTrace(line_no=line_no,
                              is_comment=is_comment,
                              reaction_type=rr.reaction_type,
                              reaction_definition=rr.reaction_definition,
                              raw_line=raw_line.rstrip('\n')))
  return trace_index


def _consume_ht_trace(rr, ht_trace_index, used_trace_ids):
  eq_key = _reaction_equivalence_key(rr)
  traces = ht_trace_index.get(eq_key, [])
  for i, trace in enumerate(traces):
    if i in used_trace_ids[eq_key]:
      continue
    if trace.is_comment:
      continue
    if (trace.reaction_definition == rr.reaction_definition and
        trace.reaction_type == rr.reaction_type):
      used_trace_ids[eq_key].add(i)
      return trace
  for i, trace in enumerate(traces):
    if i in used_trace_ids[eq_key]:
      continue
    if not trace.is_comment:
      used_trace_ids[eq_key].add(i)
      return trace
  return ParentReactionTrace(line_no=-1,
                             is_comment=False,
                             reaction_type=rr.reaction_type,
                             reaction_definition=rr.reaction_definition,
                             raw_line=rr.reaction_string_orig.rstrip('\n'))


def _classify_unmatched_reason(rr, canonical, parent_signatures, parent_used,
                               parent_reaction_index):
  def _has_unused(candidates):
    for canonical_parent, i, _ in candidates:
      if not parent_used[canonical_parent][i]:
        return True
    return False

  eq_key = _reaction_equivalence_key(rr)
  meta_key = _reaction_metadata_signature(rr)
  canonical_candidates = parent_signatures.get(canonical, [])
  if len(canonical_candidates) == 0:
    relaxed_candidates = parent_reaction_index.get((eq_key, meta_key), [])
    if relaxed_candidates:
      if _has_unused(relaxed_candidates):
        return ("same stoichiometric reaction exists in parent with matching "
                "third-body/keyword data, but arrow form differs "
                "(direction/reversibility mismatch, e.g. A+B=C+D vs C+D=A+B)")
      return ("matching parent reaction exists (same stoichiometry and "
              "third-body/keyword data), but it was already used by another HT "
              "reaction (HT has an extra duplicate, often from mixed REV/ '=' forms)")

    eq_candidates = parent_reaction_index.get(eq_key, [])
    if eq_candidates:
      return ("same stoichiometric reaction exists in parent, but third-body "
              "terms or keyword blocks differ (e.g. LOW/HIGH/TROE/SRI/"
              "PLOG/CHEB/DUPLICATE)")
    return "no active parent reaction with equivalent stoichiometry was found"

  has_unused_same_canonical = False
  has_unused_same_signature = False
  for i, candidate_signature in enumerate(canonical_candidates):
    if parent_used[canonical][i]:
      continue
    has_unused_same_canonical = True
    if candidate_signature == _reaction_match_signature(rr):
      has_unused_same_signature = True
      break

  if has_unused_same_signature:
    return "internal matching inconsistency (unexpected unmatched state)"
  if has_unused_same_canonical:
    return ("same arrow form exists in parent, but third-body terms or keyword "
            "blocks differ (e.g. LOW/HIGH/TROE/SRI/PLOG/CHEB/DUPLICATE)")
  if (eq_key, meta_key) in parent_reaction_index:
    return ("matching parent reaction exists (same stoichiometry and "
            "third-body/keyword data), but it was already used by another HT "
            "duplicate (HT has an extra duplicate)")
  if eq_key in parent_reaction_index:
    return ("same stoichiometric reaction exists in parent, but third-body "
            "terms or keyword blocks differ (e.g. LOW/HIGH/TROE/SRI/"
            "PLOG/CHEB/DUPLICATE)")
  return "no active parent reaction with equivalent stoichiometry was found"


def _collect_unmatched_ht_reactions(ht_reactions, parent_reactions, ht_basename,
                                    parent_base, ht_trace_index,
                                    parent_trace_index):
  parent_signatures = {}
  parent_used = {}
  parent_relaxed = defaultdict(list)
  parent_reversible = defaultdict(list)
  parent_reaction_index = defaultdict(list)
  for canonical, rr_list in parent_reactions.items():
    signatures = [_reaction_match_signature(rr) for rr in rr_list]
    parent_signatures[canonical] = signatures
    parent_used[canonical] = [False] * len(signatures)
    for i, rr in enumerate(rr_list):
      relaxed_key = (_reaction_equivalence_key(rr),
                     _reaction_metadata_signature(rr))
      parent_reaction_index[_reaction_equivalence_key(rr)].append((canonical, i,
                                                                   rr))
      parent_reaction_index[relaxed_key].append((canonical, i, rr))
      if rr.reaction_type == "irreversible":
        parent_relaxed[relaxed_key].append((canonical, i, rr))
      elif rr.reaction_type == "reversible":
        parent_reversible[relaxed_key].append((canonical, i, rr))

  unmatched = []
  restrictive_warnings = []
  restrictive_keys = set()
  used_ht_trace_ids = defaultdict(set)
  local_count = defaultdict(int)
  for canonical, rr_list in ht_reactions.items():
    for rr in rr_list:
      local_idx = local_count[canonical]
      local_count[canonical] += 1
      ht_trace = _consume_ht_trace(rr, ht_trace_index, used_ht_trace_ids)
      target_signature = _reaction_match_signature(rr)

      matched = False
      for i, candidate_signature in enumerate(
          parent_signatures.get(canonical, [])):
        if parent_used[canonical][i]:
          continue
        if target_signature == candidate_signature:
          parent_used[canonical][i] = True
          matched = True
          break

      # Parent reversible already contains both directions and is therefore a
      # valid superset for an HT irreversible reaction with the same metadata.
      if not matched and rr.reaction_type == "irreversible":
        relaxed_key = (_reaction_equivalence_key(rr),
                       _reaction_metadata_signature(rr))
        for canonical_parent, i, _ in parent_reversible.get(relaxed_key, []):
          if parent_used[canonical_parent][i]:
            continue
          parent_used[canonical_parent][i] = True
          matched = True
          break

      # If HT is reversible but parent only has irreversible variant with the
      # same stoichiometry/metadata, keep it and report that parent is stricter.
      if not matched and rr.reaction_type == "reversible":
        relaxed_key = (_reaction_equivalence_key(rr),
                       _reaction_metadata_signature(rr))
        for canonical_parent, i, rr_parent in parent_relaxed.get(relaxed_key,
                                                                 []):
          if parent_used[canonical_parent][i]:
            continue
          parent_used[canonical_parent][i] = True
          matched = True
          restrictive_keys.add((ht_basename, canonical, local_idx))
          restrictive_warnings.append(
              RestrictiveMatchWarning(
                  ht_base=ht_basename,
                  parent_base=parent_base,
                  ht_reaction=rr.reaction_definition,
                  parent_reaction=rr_parent.reaction_definition,
                  parent_line=next(
                      (t.line_no for t in parent_trace_index.get(
                          _reaction_equivalence_key(rr_parent), [])
                       if (not t.is_comment and
                           t.reaction_definition == rr_parent.reaction_definition)),
                      -1)))
          break

      if not matched:
        eq_key = _reaction_equivalence_key(rr)
        traces = tuple(parent_trace_index.get(eq_key, []))
        reason = _classify_unmatched_reason(rr, canonical, parent_signatures,
                                            parent_used, parent_reaction_index)
        unmatched.append(
            UnmatchedReactionDetail(key=(ht_basename, canonical, local_idx),
                                    ht_base=ht_basename,
                                    parent_base=parent_base,
                                    ht_reaction=rr.reaction_definition,
                                    ht_trace=ht_trace,
                                    parent_traces=traces,
                                    reason=reason))
  return unmatched, restrictive_warnings, restrictive_keys


def _prepare_ht_subset_pruning(species_list, submodules_files):
  ht_parent_map = _resolve_ht_parent_map(submodules_files)
  if not ht_parent_map:
    return set(), set(), [], [], species_list.copy(), species_list.copy()

  parent_species, extended_species = _build_parent_species_list(
      species_list, submodules_files, ht_parent_map)
  n_extra = len(extended_species) - len(species_list)
  if n_extra > 0:
    print("LT-HT parent species extension adds", n_extra, "species")

  unmatched_keys = set()
  restrictive_keys = set()
  unmatched_details = []
  restrictive_warnings = []
  for ht_path, parent_path in sorted(ht_parent_map.items(),
                                     key=lambda item: os.path.basename(item[0])):
    ht_base = os.path.basename(ht_path)
    parent_base = os.path.basename(parent_path)
    print("HT subset check: '" + ht_base + "' against parent '" + parent_base +
          "'")

    parent_reactions, parent_species_used, parent_reaction_count = _parse_reactions_from_submodule(
        parent_path, extended_species)
    ht_reactions, ht_species_used, ht_reaction_count = _parse_reactions_from_submodule(
        ht_path, extended_species)
    print("  parent (LT-HT) summary:")
    print("    species referenced by reactions:", parent_species_used)
    print("    reactions parsed:", parent_reaction_count)
    print("  HT summary:")
    print("    species referenced by reactions:", ht_species_used)
    print("    reactions parsed:", ht_reaction_count)
    ht_trace_index = _build_reaction_trace_index(ht_path, extended_species)
    parent_trace_index = _build_reaction_trace_index(parent_path,
                                                     extended_species)
    unmatched, restrictive_i, restrictive_i_keys = _collect_unmatched_ht_reactions(
        ht_reactions, parent_reactions, ht_base, parent_base, ht_trace_index,
        parent_trace_index)
    restrictive_warnings.extend(restrictive_i)
    restrictive_keys.update(restrictive_i_keys)
    for detail in unmatched:
      unmatched_keys.add(detail.key)
      unmatched_details.append(detail)
  return unmatched_keys, restrictive_keys, unmatched_details, restrictive_warnings, parent_species, extended_species


def _reaction_instance_key_map(reactions):
  # Map each reaction occurrence to id(rr). We use id(rr) to target one
  # specific ChemicalReaction object even when canonical strings are duplicated.
  seen = defaultdict(int)
  mapping = {}
  for canonical, rr_list in reactions.items():
    for rr in rr_list:
      source = rr.get_submodule_file()
      local_idx = seen[(source, canonical)]
      seen[(source, canonical)] += 1
      key = (source, canonical, local_idx)
      if key in mapping:
        raise Exception("Duplicate reaction-instance key '" + str(key) + "'")
      mapping[key] = id(rr)
  return mapping


def _resolve_prepruned_reaction_ids(reactions, unmatched_keys):
  # Convert unmatched (file, canonical, local occurrence) keys into id(rr)
  # so downstream pruning/comments affect exactly those reaction instances.
  if not unmatched_keys:
    return set()
  key_to_id = _reaction_instance_key_map(reactions)
  resolved = set()
  missing = []
  for key in sorted(unmatched_keys):
    if key not in key_to_id:
      missing.append(key)
    else:
      resolved.add(key_to_id[key])
  if missing:
    raise Exception("#error: internal mismatch while mapping HT subset-pruned "
                    "reactions to compiled reactions. Missing keys: " +
                    ", ".join(str(k) for k in missing))
  return resolved


def _collect_reaction_species(rr):
  species = set()
  for _, sp in rr.reactants:
    species.add(sp)
  for _, sp in rr.products:
    species.add(sp)
  species.update(rr.explicit_dependence)
  species.update(rr.tb_efficiencies.keys())
  return species


def _species_only_in_removed_reactions(reactions, removed_reaction_ids):
  if not removed_reaction_ids:
    return set()
  removed_species = set()
  active_species = set()
  for _, rr_list in reactions.items():
    for rr in rr_list:
      species = _collect_reaction_species(rr)
      if id(rr) in removed_reaction_ids:
        removed_species.update(species)
      else:
        active_species.update(species)
  return removed_species - active_species


def _reaction_consumed_species(rr):
  consumed = [sp for _, sp in rr.reactants]
  if rr.reaction_type == 'reversible':
    consumed += [sp for _, sp in rr.products]
  return consumed


def _reaction_produced_species(rr):
  produced = [sp for _, sp in rr.products]
  if rr.reaction_type == 'reversible':
    produced += [sp for _, sp in rr.reactants]
  return produced


def _reaction_by_id(reactions):
  by_id = {}
  for _, rr_list in reactions.items():
    for rr in rr_list:
      by_id[id(rr)] = rr
  return by_id


def _count_reaction_instances(reactions):
  return sum(len(rr_list) for rr_list in reactions.values())


def _count_active_canonical_reactions(reactions, reactions_pruned_ids):
  # Count canonical reactions that still have at least one active instance.
  count = 0
  for _, rr_list in reactions.items():
    if any(id(rr) not in reactions_pruned_ids for rr in rr_list):
      count += 1
  return count


def print_kinetics_file(species_list, species_pruned, header_filename,
                        submodules_files, model_name, mid, output_filename,
                        datetime, reactions, reactions_pruned_ids):
  species_section_str = write_species_list(species_list, species_pruned, '')
  new_lines = insert_boiler_plate("Kinetics", model_name, submodules_files,
                                  datetime, mid, header_filename)
  n_species = len(species_list)
  # no pruned species (my be empty)
  n_species -= len(species_pruned)
  new_lines.append("! number of species: " + str(n_species) + "\n")
  n_reactions = _count_active_canonical_reactions(reactions,
                                                  reactions_pruned_ids)
  new_lines.append("! number of reactions: " + str(n_reactions) + "\n")
  new_lines.append("\n")

  insert_reaction_count = len(new_lines)

  new_lines = insert_species_list(species_section_str, submodules_files.core,
                                  new_lines)

  new_lines.append("REACTIONS\n")

  #this does not account for pruning
  # new_lines.insert(
  #    insert_reaction_count + 1, "! number of reactions: " +
  #    str(cantera_count) + " (number of reactions given by cantera)\n\n")

  for r in reactions:
    for rr in reactions[r]:
      #print("\n\n\n")
      #print(rr.pretty() + ":")
      for p_line in rr.get_orignal_CHEMKIN_text():
        if id(rr) in reactions_pruned_ids and p_line != "":
          new_lines.append(pruned_comment + p_line)
        else:
          new_lines.append(p_line)

  new_lines.append("\nEND\n\n")

  print("writing '" + output_filename + "'")
  with open(output_filename, 'w', encoding="utf-8") as file:
    file.writelines(ascii_space(line) for line in new_lines)
  return n_species, n_reactions


def process_submodules(species_list, submodules_files):

  species_dict = {s: 0 for s in species_list}
  for s in species_dict:
    if "+" in s:
      raise Exception("species name '" + s + "' contains a +")

    match = re.match(r'^[\w\-\(\),\#]+$', s)
    if not match:
      raise Exception("species name '" + s +
                      "' does not match the species pattern")

  print("processing: '" + os.path.basename(submodules_files.core) + "'")

  processed_files = set([os.path.basename(submodules_files.core)])
  with open(submodules_files.core, 'r') as file:
    lines = file.readlines()
  normalized_reactions, normalized_reactions_check = {}, {}
  n_reaction, cantera_count, normalized_reactions, normalized_reactions_check, species_dict = inp.count_reactions(
      lines, os.path.basename(submodules_files.core), species_dict,
      normalized_reactions, normalized_reactions_check)

  #base_names = sorted([os.path.basename(file_path) for file_path in submodules_files.submodules])
  aux_path = {
      os.path.basename(file_path): file_path
      for file_path in submodules_files.submodules
  }
  for base_name in aux_path:
    if base_name in processed_files:
      raise Exception("duplicate filename '" + base_name +
                      "' in sub-modules files")
    processed_files.add(base_name)
    file_path = aux_path[base_name]
    print("processing: '" + base_name + "'")
    with open(file_path, 'r') as file:
      lines = file.readlines()
      n_reaction_i, cantera_count_i, normalized_reactions, normalized_reactions_check, species_dict = inp.count_reactions(
          lines, base_name, species_dict, normalized_reactions,
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

  print("compiled model contains " + str(len(species_list)) + " species and " +
        str(cantera_count) + " (cantera count) / " +
        str(len(normalized_reactions)) + " (normal count) reactions")

  return normalized_reactions


def prune_model(reactions, prune, initial_removed_reaction_ids=None):
  if initial_removed_reaction_ids is None:
    initial_removed_reaction_ids = set()

  never_consumed = set()
  never_produced = set()
  removed_reaction_ids = set(initial_removed_reaction_ids)

  species2reaction = defaultdict(set)
  consumed = {}
  produced = {}
  reaction_by_id = _reaction_by_id(reactions)
  for _, rr_list in reactions.items():
    for rr in rr_list:
      rr_id = id(rr)
      if rr_id in removed_reaction_ids:
        continue
      consumed_species = _reaction_consumed_species(rr)
      produced_species = _reaction_produced_species(rr)
      for s in consumed_species:
        consumed[s] = consumed.get(s, 0) + 1
        species2reaction[s].add(rr_id)
      for s in produced_species:
        produced[s] = produced.get(s, 0) + 1
        species2reaction[s].add(rr_id)

  active_species = set(species2reaction.keys())
  count = 1
  if prune:
    print("start pruning...")
  while prune:
    print("round " + str(count) + " with " + str(len(active_species)) +
          " species")
    new_never_consumed = set()
    new_never_produced = set()

    for s in active_species:
      if s not in consumed and s in produced and s not in never_consumed:
        new_never_consumed.add(s)
      if s not in produced and s in consumed and s not in never_produced:
        new_never_produced.add(s)

    remove_species = new_never_consumed.union(new_never_produced)
    active_species = set()
    for s in remove_species:
      for rr_id in species2reaction.get(s, set()):
        if rr_id in removed_reaction_ids:
          continue
        removed_reaction_ids.add(rr_id)
        rr = reaction_by_id[rr_id]

        for s_remove in _reaction_consumed_species(rr):
          if s_remove not in consumed:
            continue
          consumed[s_remove] -= 1
          if abs(consumed[s_remove]) < 1.0e-5:
            del consumed[s_remove]
            if s_remove not in remove_species:
              active_species.add(s_remove)

        for s_remove in _reaction_produced_species(rr):
          if s_remove not in produced:
            continue
          produced[s_remove] -= 1
          if abs(produced[s_remove]) < 1.0e-5:
            del produced[s_remove]
            if s_remove not in remove_species:
              active_species.add(s_remove)

    never_consumed = never_consumed.union(new_never_consumed)
    never_produced = never_produced.union(new_never_produced)

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

  return never_consumed, never_produced, removed_reaction_ids


def make_clean_species_list(submodules_files):
  species_list = inp.make_species_list('', submodules_files.get_files())

  species_dict = {k.upper(): 0 for k in species_list}
  for s in species_dict:
    species_dict[s] = 0
  return species_dict


def get_identifier_model(identifier):
  # removes the Tool-dependence of the identifier
  return tuple([name.replace("_Cantera", "") for name in identifier] + ['mid'])


def clean_therm(therm_output, species_list, species_pruned, header_filename,
                submodules_files, model_name, mid, species_output, datetime):
  print("writing '" + therm_output + "'")
  with open(therm_output, 'w') as thermfile:

    thermfile.writelines(
        ascii_space(line) for line in insert_boiler_plate(
            "Thermodynamic", model_name, submodules_files, datetime, mid,
            header_filename))

    thermfile.write(ascii_space('THERMO ALL\n'))
    thermfile.write(ascii_space('300.   1000.   5000.\n'))

    for s in species_list:
      addition = ""
      if s in species_pruned:
        addition = pruned_comment

      thermfile.write(ascii_space(addition + species_output[s][0]))
      thermfile.write(ascii_space(addition + species_output[s][1]))
      thermfile.write(ascii_space(addition + species_output[s][2]))
      thermfile.write(ascii_space(addition + species_output[s][3]))

    thermfile.write(ascii_space('\nEND\n\n'))


def clean_tran(tran_file, tran_output, species_list, species_pruned,
               header_filename, submodules_files, model_name, mid, datetime):
  tran = open(tran_file, 'r', encoding="utf-8")
  tranlines = tran.readlines()
  tran.close()

  species_dict = {s.upper(): 0 for s in species_list}
  print("writing '" + tran_output + "'")
  with open(tran_output, 'w') as tranfile:
    tranfile.writelines(
        ascii_space(line) for line in insert_boiler_plate(
            "Transport", model_name, submodules_files, datetime, mid,
            header_filename))

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
              ascii_space(
                  '{0:18}    {1}    {2:8.2f}    {3:6.2f}    {4:6.2f}    {5:6.2f}    {6:6.2f}    {7}\n'
                  .format(tran_component[0], tran_component[1],
                          float(tran_component[2]), float(tran_component[3]),
                          float(tran_component[4]), float(tran_component[5]),
                          float(tran_component[6]),
                          ' '.join(tran_component[7:]))))
        else:
          addition = ""
          if sp_name in species_pruned:
            addition = pruned_comment
          tranfile.write(
              ascii_space(
                  addition +
                  '{0:18}    {1}    {2:8.2f}    {3:6.2f}    {4:6.2f}    {5:6.2f}    {6:6.2f}\n'
                  .format(tran_component[0], tran_component[1],
                          float(tran_component[2]), float(tran_component[3]),
                          float(tran_component[4]), float(tran_component[5]),
                          float(tran_component[6]))))
        #tranfile.write('{0}\n'.format(tranlines[line].rstrip()))

    for s, v in species_dict.items():
      if v == 0:
        print('{0} : transport data not found...'.format(s))


def compile_model(options,
                  submodules_files,
                  output,
                  datetime,
                  output_chunk,
                  output_chunk_kin,
                  generated_combinations,
                  identifier,
                  mid,
                  write_therm_trans=True):
  species_list = make_clean_species_list(submodules_files)
  subset_unmatched_keys, restrictive_fix_keys, subset_unmatched_details, restrictive_match_warnings, parent_species_list, _ = _prepare_ht_subset_pruning(
      species_list, submodules_files)
  species_missing_in_parent = set(species_list.keys()) - set(
      parent_species_list.keys())
  if options.require_ht_subset_no_change:
    has_subset_effect = bool(subset_unmatched_keys or restrictive_fix_keys or
                             species_missing_in_parent)
    if has_subset_effect:
      print(
          "#error: HT-vs-LT-HT subset checks found differences while "
          "'--require-ht-subset-no-change' is enabled.")
      print("        This run is aborted to guarantee that subset logic has no "
            "effect on the generated output.")
      if len(subset_unmatched_keys):
        print("        unmatched HT reactions that would be commented out:",
              len(subset_unmatched_keys))
      if len(restrictive_fix_keys):
        print("        reversible HT reactions that would be rewritten to "
              "irreversible:", len(restrictive_fix_keys))
      if len(species_missing_in_parent):
        print("        species present in HT selection but missing in LT-HT "
              "parent:", len(species_missing_in_parent))
      raise Exception(
          "#error: aborting due to HT-vs-LT-HT subset differences "
          "(strict no-change mode)")
  if len(species_missing_in_parent):
    print("\n")
    print(
        len(species_missing_in_parent),
        "species are present in the selected model but absent in the LT-HT parent species list:"
    )
    for s in sorted(species_missing_in_parent):
      print(s)

  print("\nprocess input...")
  reactions = process_submodules(species_list, submodules_files)
  subset_removed_reaction_ids = _resolve_prepruned_reaction_ids(
      reactions, subset_unmatched_keys)
  restrictive_fix_ids = _resolve_prepruned_reaction_ids(
      reactions, restrictive_fix_keys)
  _apply_irreversible_fixes(reactions, restrictive_fix_ids)
  subset_removed_species = _species_only_in_removed_reactions(
      reactions, subset_removed_reaction_ids)
  subset_removed_species_missing_parent = subset_removed_species & species_missing_in_parent
  subset_removed_species_present_in_parent = subset_removed_species - species_missing_in_parent
  unresolved_parent_mismatch = species_missing_in_parent - subset_removed_species
  if unresolved_parent_mismatch:
    raise Exception("#error: species missing in LT-HT parent were not removed "
                    "by HT subset pruning: " +
                    ", ".join(sorted(unresolved_parent_mismatch)))

  species_compo_dict, species_nasa_output = inp.process_therm(
      options.thermfile, species_list)

  i = 0
  for r in reactions:
    for rr in reactions[r]:
      rr.check_elem_conservation(species_compo_dict)
      rr.set_idx(i)
      i += 1

  ### reaction_trie = build_trie(reactions, species_compo_dict)

  # profiler = cProfile.Profile()
  # profiler.enable()
  ### unburned_mixture = {"H2": 1, "HE": 1, "AR": 1, "O2": 1, "N2": 1}
  ### build_network(unburned_mixture, reaction_trie, species_compo_dict, reactions)
  # profiler.disable()
  # profiler.dump_stats('profile_output.prof')

  # p = pstats.Stats('profile_output.prof')
  # p.sort_stats('cumtime').print_stats(20)  # Top 20 functions by cumulative time

  # quit()

  if len(restrictive_match_warnings):
    print("\n")
    print(
        len(restrictive_match_warnings),
        "HT reactions are reversible in HT but irreversible in the LT-HT parent:"
    )
    print("Generated HT output rewrites these reactions to '=>'.")
    for w in restrictive_match_warnings:
      line_info = "" if w.parent_line < 0 else f" (line {w.parent_line})"
      print("[" + w.ht_base + " -> " + w.parent_base + "] HT: " +
            w.ht_reaction)
      print("    parent" + line_info + ": " + w.parent_reaction)

  if len(subset_unmatched_details):
    print("\n")
    print(
        len(subset_unmatched_details),
        "HT reactions could not be matched to the LT-HT parent under subset rules and will be commented out:"
    )
    for detail in subset_unmatched_details:
      ht_loc = "" if detail.ht_trace.line_no < 0 else f" (line {detail.ht_trace.line_no})"
      print("[" + detail.ht_base + " -> " + detail.parent_base +
            "] HT reaction" + ht_loc + ": " + detail.ht_reaction)
      print("    reason: " + detail.reason)
      if not detail.parent_traces:
        print("    parent trace revealed: none")
      else:
        print("    parent trace revealed:")
        for trace in detail.parent_traces:
          print(f"    line {trace.line_no}: {trace.raw_line}")

  if len(subset_removed_species_missing_parent):
    print("\n")
    print(
        len(subset_removed_species_missing_parent),
        "species are absent in the LT-HT parent and appear only in removed HT reactions:"
    )
    for s in sorted(subset_removed_species_missing_parent):
      print(s)

  if len(subset_removed_species_present_in_parent):
    print("\n")
    print(
        len(subset_removed_species_present_in_parent),
        "species appear in the LT-HT parent but become inactive in this HT build after removed-reaction filtering:"
    )
    for s in sorted(subset_removed_species_present_in_parent):
      print(s)

  never_consumed, never_produced, removed_reaction_ids = prune_model(
      reactions,
      options.prune,
      initial_removed_reaction_ids=subset_removed_reaction_ids)
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

  reaction_by_id = _reaction_by_id(reactions)
  removed_by_pruning = removed_reaction_ids - subset_removed_reaction_ids
  if len(removed_by_pruning):
    print("\n")
    print(len(removed_by_pruning), "additional pruned reactions:")
    for rr_id in removed_by_pruning:
      print(f"{reaction_by_id[rr_id].reaction_definition}")
    print("\n")

  print("\ngenerate output...")
  species_pruned = never_consumed.union(never_produced).union(
      subset_removed_species)
  if output_chunk != "":
    output_chunk = "_" + output_chunk

  def get_mid(generated_combinations, identifier):
    identifier_model = get_identifier_model(identifier)
    if identifier_model in generated_combinations:
      reusing = generated_combinations[identifier_model]["mid"]
      print("Reusing MID ='" + reusing + "'")
      return reusing
    generated_combinations[identifier_model] = {}
    print("new MID ='" + mid + "'")
    generated_combinations[identifier_model]["mid"] = mid
    return mid

  SID = get_mid(generated_combinations, identifier)
  USID = "_" + SID

  kin_file = options.model_name + USID + output_chunk + output_chunk_kin + ".CKI"
  output_filename_kin = os.path.join(options.output_dir, output, kin_file)
  ns_printed, nr_printed = print_kinetics_file(species_list, species_pruned,
                                               options.header,
                                               submodules_files,
                                               options.model_name, mid,
                                               output_filename_kin, datetime,
                                               reactions, removed_reaction_ids)

  therm_file = options.model_name + USID + output_chunk + ".THERM"
  output_filename_therm = os.path.join(options.output_dir, output, therm_file)

  trans_filename = options.model_name + USID + output_chunk + ".TRAN"
  output_filename_trans = os.path.join(options.output_dir, output,
                                       trans_filename)

  if write_therm_trans:
    clean_therm(output_filename_therm, species_list, species_pruned,
                options.header, submodules_files, options.model_name, mid,
                species_nasa_output, datetime)

    clean_tran(options.transfile, output_filename_trans, species_list,
               species_pruned, options.header, submodules_files,
               options.model_name, mid, datetime)
  else:
    # We deliberately do not write separate THERM/TRAN here.
    # The caller is responsible for pointing to canonical files.
    output_filename_therm = None
    output_filename_trans = None

  generated_combinations[identifier] = {}
  generated_combinations[identifier]["kin"] = output_filename_kin
  generated_combinations[identifier]["therm"] = output_filename_therm
  generated_combinations[identifier]["trans"] = output_filename_trans
  generated_combinations[identifier]["dir"] = os.path.join(
      options.output_dir, output)
  generated_combinations[identifier]["ns"] = ns_printed
  generated_combinations[identifier]["nr"] = nr_printed

  return ns_printed, nr_printed, generated_combinations


def process_ck2yaml(identifier, generated_combinations):

  output_filename_kin = generated_combinations[identifier]["kin"]
  output_filename_therm = generated_combinations[identifier]["therm"]
  output_filename_trans = generated_combinations[identifier]["trans"]
  output_filename_dir = generated_combinations[identifier]["dir"]
  if "cantera" in str(output_filename_kin).lower():
    cmd = [
        "ck2yaml", f"--input={output_filename_kin}",
        f"--thermo={output_filename_therm}",
        f"--transport={output_filename_trans}"
    ]
    result = subprocess.run(cmd,
                            cwd=output_filename_dir,
                            capture_output=True,
                            text=True)
    return identifier, result.returncode, result.stdout, result.stderr
  else:
    return identifier, 0, "", ""  # Not processed


def _generate_identifer(submodules_filenames, selection, cantera):
  c0 = 'C0'
  identifier_list = []
  for smod, temp in selection.items():
    if smod.upper() == c0:
      continue
    path = submodules_filenames[temp][smod]
    if smod == 'C1-C2':
      if cantera:
        # ensure we point to the Cantera-compatible file
        cand = path.replace("UOG_C1-C2_LT-HT.MECH",
                            "UOG_C1-C2_LT-HT_Cantera.MECH")
        if os.path.isfile(cand):
          path = cand
      else:
        # ensure we point to the non-Cantera file
        cand = path.replace("UOG_C1-C2_LT-HT_Cantera.MECH",
                            "UOG_C1-C2_LT-HT.MECH")
        if os.path.isfile(cand):
          path = cand
    identifier_list.append(path)

  core_filename = submodules_filenames[selection[c0]][c0]
  if not cantera:
    # switch core to non-Cantera variant (as before, but more robust)
    cand_core = core_filename.replace("UOG_C0_LT-HT_Cantera.MECH",
                                      "UOG_C0_LT-HT.MECH")
    if os.path.isfile(cand_core):
      core_filename = cand_core
    else:
      print("#error: expected non-Cantera C0 core not found: " + cand_core)
      sys.exit(1)

  identifier_list.append(core_filename)
  return tuple(sorted(identifier_list)), core_filename


def one_carbon_number(options,
                      submodules_filenames,
                      datetime,
                      cnum,
                      data_dict,
                      generated_combinations,
                      counters=None,
                      cantera=True,
                      canonical_files=None):
  for selection_count, selection in enumerate(data_dict["modules"]):
    identifier, core_filename = _generate_identifer(submodules_filenames,
                                                    selection, cantera)

    submodules_list = []
    for smod, temp in selection.items():
      if smod.upper() == "C0":
        continue
      path = submodules_filenames[temp][smod]
      if smod == "C1-C2":
        if cantera:
          cand = path.replace("UOG_C1-C2_LT-HT.MECH",
                              "UOG_C1-C2_LT-HT_Cantera.MECH")
          if os.path.isfile(cand):
            path = cand
        else:
          cand = path.replace("UOG_C1-C2_LT-HT_Cantera.MECH",
                              "UOG_C1-C2_LT-HT.MECH")
          if os.path.isfile(cand):
            path = cand
      submodules_list.append(path)

    submodules_files = inp.SubModulesFiles(core_filename, submodules_list)
    submodules_files.insert_model_path(options.submodules_dir)

    # --- Directory layout: carbon group / combo_dir / tool ---
    # Examples:
    #   PRECOMPILED/C8+/C0-C8+_DMC+EC_N/Chemkin/
    #   PRECOMPILED/C8+/C0-C8+_DMC+EC_N/Cantera/
    carbon_dir = data_dict["output_dir"]  # absolute, e.g. PRECOMPILED/C8+
    tool_dir = "Cantera" if cantera else "Chemkin"

    name_with_temp = data_dict["output_chunks"][selection_count]
    temp_flag = data_dict["temperature"][selection_count]  # "HT", "LT-HT", or ""

    # Strip trailing "_HT" / "_LT-HT" for the directory name
    if temp_flag in ("HT", "LT-HT"):
      combo_dir = name_with_temp.rsplit("_", 1)[0]
    else:
      combo_dir = name_with_temp

    target_dir = os.path.join(carbon_dir, combo_dir, tool_dir)
    os.makedirs(target_dir, exist_ok=True)

    out_chuck = ""
    if cantera:
      out_chuck = "_Cantera"

    mid = data_dict["mid"][selection_count]

    if identifier not in generated_combinations:
      # In --generate-all:
      #   - Chemkin (cantera=False): write THERM/TRAN (canonical copies)
      #   - Cantera (cantera=True): do NOT write THERM/TRAN here; reuse Chemkin's
      write_therm_trans = True
      if options.generate_all and cantera:
        write_therm_trans = False

      ns_printed, nr_printed, generated_combinations = compile_model(
          options,
          submodules_files,
          output=target_dir,
          datetime=datetime,
          output_chunk=name_with_temp,
          output_chunk_kin=out_chuck,
          generated_combinations=generated_combinations,
          identifier=identifier,
          mid=mid,
          write_therm_trans=write_therm_trans)

      # Track canonical THERM/TRAN by MID (where they are actually written)
      if canonical_files is not None:
        therm_path = generated_combinations[identifier]["therm"]
        trans_path = generated_combinations[identifier]["trans"]
        if therm_path is not None and trans_path is not None:
          canonical_files[mid] = {
              "therm": therm_path,
              "trans": trans_path,
          }

      # For Cantera in --generate-all, point to canonical Chemkin THERM/TRAN
      if options.generate_all and cantera and canonical_files is not None:
        if mid not in canonical_files:
          raise Exception("Canonical THERM/TRAN missing for MID '" + mid +
                          "' when generating Cantera files")
        generated_combinations[identifier]["therm"] = canonical_files[mid][
            "therm"]
        generated_combinations[identifier]["trans"] = canonical_files[mid][
            "trans"]

      if counters is not None:
        if mid in counters:
          if counters[mid][1] != ns_printed or counters[mid][2] != nr_printed:
            raise Exception("duplicate MID '" + mid + "' for " +
                            str((selection, ns_printed, nr_printed)) +
                            " (new) and " + str(counters[mid]))
        counters[mid] = (selection, ns_printed, nr_printed)
    else:
      mid = data_dict["mid"][selection_count]
      if counters is not None and mid not in counters:
        raise Exception("duplicate identifier " + str(identifier) +
                        " must have counter but '" + mid + "' was not found")
      # if a sub-module combination was used before
      # this is because there is no distinction between
      # HT and LT-HT for this combination
      aux = ["kin", "therm", "trans"]
      for f in aux:
        fname = generated_combinations[identifier][f]
        if fname is None:
          continue
        if not cantera and "cantera" in fname.lower():
          raise Exception(
              "fname " + fname +
              "contains cantera, but cantera is FALSE. There is a bug.")
        dir_name = os.path.dirname(fname)
        base_name = os.path.basename(fname)
        new_base = base_name.replace('_LT-HT', '').replace('_HT', '')
        new_fname = os.path.join(dir_name, new_base)
        if new_fname != fname:
          print(
              f"Renaming {os.path.basename(fname)} -> {os.path.basename(new_fname)}"
          )
          generated_combinations[identifier][f] = new_fname
          os.rename(fname, new_fname)

      # After renaming, refresh canonical THERM/TRAN for this MID
      if canonical_files is not None:
        therm_path = generated_combinations[identifier]["therm"]
        trans_path = generated_combinations[identifier]["trans"]
        if therm_path is not None and trans_path is not None:
          canonical_files[mid] = {
              "therm": therm_path,
              "trans": trans_path,
          }

  return generated_combinations


def run(options, submodules_filenames, grouped_selections, columns):

  print("read input...")
  DATETIME = datetime.datetime.now()

  if options.generate_all:
    generated_combinations = {}
    submodules_filename = options.yaml_file_path

    counters = {}
    # MID -> {"therm": path, "trans": path}
    canonical_files = {}

    # Run Chemkin first (cantera=False), then Cantera (cantera=True)
    cantera_opts = [False, True]
    for cantera in cantera_opts:
      for cnum, data_dict in grouped_selections.items():
        generated_combinations = one_carbon_number(
            options,
            submodules_filenames,
            DATETIME,
            cnum,
            data_dict,
            generated_combinations,
            counters=counters,
            cantera=cantera,
            canonical_files=canonical_files)

    readme = generate_readme(grouped_selections, columns, counters)
    readme_file = os.path.join(options.output_dir, "README.md")
    print("writing:", readme_file)
    with open(readme_file, "w") as f:
      f.write('\n'.join(readme))

    tasks = []
    with ThreadPoolExecutor(max_workers=options.max_threads) as executor:
      for identifier in generated_combinations:
        if "mid" in identifier:
          continue
        if options.process_cantera and "cantera" in str(
            generated_combinations[identifier]["kin"]).lower():
          tasks.append(
              executor.submit(process_ck2yaml, identifier,
                              generated_combinations))

      for future in as_completed(tasks):
        identifier, returncode, stdout, stderr = future.result()
        print(f"\n=== {identifier} ===")
        print(stdout)
        print(stderr)
        if returncode != 0:
          print(f"Error running ck2yaml for {identifier}:")
          print(stderr)
          sys.exit(1)
        else:
          print("processing with cantera was successful!")
  else:

    generated_combinations_single = {}
    canonical_files_single = {}
    cantera_mode = detect_cantera_mode(submodules_filenames)
    for cnum, data_dict in grouped_selections.items():
      generated_combinations_single = one_carbon_number(
          options,
          submodules_filenames,
          DATETIME,
          cnum,
          data_dict,
          generated_combinations_single,
          cantera=cantera_mode,
          canonical_files=canonical_files_single)

    for identifier in generated_combinations_single:
      if "mid" in identifier:
        continue
      # --- Process with ck2yaml if requested ---
      if options.process_cantera and "cantera" in str(
          generated_combinations_single[identifier]["kin"]).lower():
        result = process_ck2yaml(identifier, generated_combinations_single)

        _, returncode, stdout, stderr = result
        print(stdout)
        print(stderr)

        if returncode != 0:
          print(f"Error running ck2yaml for {identifier}:")
          print(stderr)
          sys.exit(1)
        else:
          print("processing with cantera was successful!")
