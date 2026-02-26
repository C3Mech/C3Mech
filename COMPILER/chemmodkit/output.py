import datetime
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

pruned_comment = "! AUTOMATIC PRUNING ! "

from . import input as inp
from . import reaction as rxn


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


def print_kinetics_file(species_list, species_pruned, header_filename,
                        submodules_files, model_name, mid, output_filename,
                        datetime, reactions, reactions_pruned):
  species_section_str = write_species_list(species_list, species_pruned, '')
  new_lines = insert_boiler_plate("Kinetics", model_name, submodules_files,
                                  datetime, mid, header_filename)
  n_species = len(species_list)
  # no pruned species (my be empty)
  n_species -= len(species_pruned)
  new_lines.append("! number of species: " + str(n_species) + "\n")
  n_reactions = len(reactions)
  n_reactions -= len(reactions_pruned)
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
        if r in reactions_pruned and p_line != "":
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


def prune_model(reactions, prune):
  never_consumed = set()
  never_produced = set()
  count = 1
  consumed, produced, species2reaction = rxn.get_cons_prod_counter(
      reactions, 1)
  removed_reaction = set()
  active_species = set([s for s in species2reaction])
  if prune:
    print("start pruning...")
  while prune:
    print("round " + str(count) + " with " + str(len(active_species)) +
          " species")
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
  print("\nprocess input...")
  reactions = process_submodules(species_list, submodules_files)

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

  never_consumed, never_produced, removed_reaction = prune_model(
      reactions, options.prune)
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

  if len(removed_reaction):
    print("\n")
    print(len(removed_reaction), "pruned reactions:")
    for r in removed_reaction:
      for rr in reactions[r]:
        print(f"{rr.reaction_definition}")
    print("\n")

  print("\ngenerate output...")
  species_pruned = never_consumed.union(never_produced)
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
                                               reactions, removed_reaction)

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
