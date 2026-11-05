import datetime
import os
import re
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

if __package__ and "." in __package__:
  from .. import c3mech_data
else:
  import c3mech_data

pruned_comment = "! AUTOMATIC PRUNING ! "

from . import input as inp
from . import reaction as rxn
from . import __version__ as compiler_version
from . import distribution
from .errors import ExternalToolError
from .generation_timestamp import format_generation_timestamp_line

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


def _validate_ck2yaml_result(tool_dependent_submodel_key, returncode, stdout,
                             stderr):
  if returncode != 0:
    details = stderr.strip() or stdout.strip()
    suffix = ": " + details if details else ""
    raise ExternalToolError(
        "ck2yaml failed for " + str(tool_dependent_submodel_key) +
        " with exit status " + str(returncode) + suffix)
  try:
    distribution.validate_cantera_success(stdout)
  except ValueError as exc:
    raise ExternalToolError(
        "ck2yaml validation failed for " +
        str(tool_dependent_submodel_key) + ": " + str(exc)) from exc


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


class SpeciesDictionary(dict):
  """Species lookup that retains collider-only output classification."""

  def __init__(self, *args, collider_only=(), **kwargs):
    super().__init__(*args, **kwargs)
    self.collider_only = tuple(collider_only)

  def copy(self):
    return SpeciesDictionary(self, collider_only=self.collider_only)


def write_species_list(species_list, species_pruned, filename):
  # write spc str
  commentstr = '\n!+++++++++++++++++++++ '
  speciesallstr = '\n!\\SPECIES_MODULE: ALL '
  speciesendstr = '\n!\\END_SPECIES_MODULE: ALL '
  allspcstr = '\n'
  count = 0
  spcsperline = 3
  collider_only = set(getattr(species_list, "collider_only", ()))
  regular_species = [
      spc for spc in species_list
      if spc not in species_pruned and spc not in collider_only
  ]
  collider_species = [
      spc for spc in species_list
      if spc not in species_pruned and spc in collider_only
  ]

  for spc in regular_species:
    count += 1
    allspcstr += spc
    allspcstr += ' ' * (30 - len(spc))
    if count % spcsperline == 0:
      allspcstr += '\n'

  if collider_species:
    if not allspcstr.endswith('\n'):
      allspcstr += '\n'
    allspcstr += '! BEGIN COLLIDER-ONLY SPECIES\n'
    count = 0
  for spc in collider_species:
    if spc in species_pruned:
      continue
    count += 1
    allspcstr += spc
    allspcstr += ' ' * (30 - len(spc))
    if count % spcsperline == 0:
      allspcstr += '\n'
  if collider_species:
    if not allspcstr.endswith('\n'):
      allspcstr += '\n'
    allspcstr += '! END COLLIDER-ONLY SPECIES\n'

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


def _is_ic_kinetics_filename(filename):
  """Return whether a kinetics filename identifies the legacy IC variant."""
  return os.path.basename(filename).lower().endswith("_ic.cki")


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


def insert_header(lines, header_filename, header_text=None):
  if header_text is None:
    with open(header_filename, 'r', encoding="utf-8") as header_file:
      header_text = header_file.read()
  normalized_header_text = header_text.replace("\r\n", "\n").replace(
      "\r", "\n")
  for line_number, line in enumerate(
      normalized_header_text.split("\n"), start=1):
    invalid = next(
        (character for character in line
         if not character.isascii() or not character.isprintable()), None)
    if invalid is not None:
      raise c3mech_data.UserInputError(
          "CHEMKIN-format header contains unsupported character " +
          repr(invalid) + " on line " + str(line_number))
  ascii_header_text = ascii_tab_space(normalized_header_text)
  lines.extend(ascii_header_text.splitlines(keepends=True))
  lines.append("\n")
  lines.append("\n")


def insert_time(lines, filetype, name, datetime):
  lines.append(format_generation_timestamp_line(filetype, name, datetime))


def insert_submodule_list(lines, submodules_files, mid):
  lines.append('! The following sub-modules were considered in this file:\n')
  lines.append('! - ' + os.path.basename(submodules_files.core) + '\n')
  for file_path in submodules_files.submodules:
    lines.append('! - ' + os.path.basename(file_path) + '\n')
  lines.append("\n")
  lines.append('! model ID (MID): ' + mid)
  lines.append("\n")


def insert_boiler_plate(filetype, name, submodules_files, datetime, mid,
                        header_filename, header_text=None):
  lines = []
  insert_header(lines, header_filename, header_text=header_text)
  insert_time(lines, filetype, name, datetime)
  insert_submodule_list(lines, submodules_files, mid)
  return lines


def ascii_tab_space(s: str) -> str:
  """Replace tabs and reject unsupported CHEMKIN-format output characters."""
  non_ascii = next((ch for ch in s if not ch.isascii()), None)
  if non_ascii is not None:
    raise c3mech_data.UserInputError(
        "CHEMKIN-format output contains a non-ASCII character: " +
        repr(non_ascii))
  nonprinting = next(
      (ch for ch in s
       if ch not in '\r\n\t' and not 32 <= ord(ch) <= 126), None)
  if nonprinting is not None:
    raise c3mech_data.UserInputError(
        "CHEMKIN-format output contains a nonprinting ASCII character: " +
        repr(nonprinting))
  return ''.join(
      ch if ch in '\r\n' or 32 <= ord(ch) <= 126 else ' '
      for ch in s)


def _is_ht_submodule_file(path):
  base = os.path.basename(path).upper()
  return base == "LLNL_BLOCK_HT.CKI" or ("_HT." in base
                                         and "_LT-HT." not in base)


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

  # Handle Windows/Linux separators and folder case variants (e.g. ht, HT).
  candidate = re.sub(r"([/\\\\])HT([/\\\\])",
                     r"\1LT-HT\2",
                     ht_path,
                     count=1,
                     flags=re.IGNORECASE)
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
      lines,
      os.path.basename(file_path),
      species_dict,
      reactions,
      reactions_check,
      print_summary=False)
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
        rr = rxn.ChemicalReaction(candidate_upper, candidate_upper,
                                  species_dict)
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
    if (trace.reaction_definition == rr.reaction_definition
        and trace.reaction_type == rr.reaction_type):
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
      return (
          "matching parent reaction exists (same stoichiometry and "
          "third-body/keyword data), but it was already used by another HT "
          "reaction (HT has an extra duplicate, often from mixed REV/ '=' forms)"
      )

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
    return (
        "same arrow form exists in parent, but third-body terms or keyword "
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


def _collect_unmatched_ht_reactions(ht_reactions, parent_reactions,
                                    ht_basename, parent_base, ht_trace_index,
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
      parent_reaction_index[_reaction_equivalence_key(rr)].append(
          (canonical, i, rr))
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
        for canonical_parent, i, rr_parent in parent_relaxed.get(
            relaxed_key, []):
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
                       if (not t.is_comment and t.reaction_definition ==
                           rr_parent.reaction_definition)), -1)))
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
  for ht_path, parent_path in sorted(
      ht_parent_map.items(), key=lambda item: os.path.basename(item[0])):
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
                        datetime, reactions, reactions_pruned_ids,
                        header_text=None, reorder=True):
  species_section_str = write_species_list(species_list, species_pruned, '')
  new_lines = insert_boiler_plate("Kinetics", model_name, submodules_files,
                                  datetime, mid, header_filename,
                                  header_text=header_text)
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

  ordered_reactions = [rr for group in reactions.values() for rr in group]
  if not reorder:
    ordered_reactions.sort(key=lambda rr: rr.source_order)
  for rr in ordered_reactions:
    for p_line in rr.get_orignal_CHEMKIN_text():
      if id(rr) in reactions_pruned_ids and p_line != "":
        new_lines.append(pruned_comment + p_line)
      else:
        new_lines.append(p_line)

  new_lines.append("\nEND\n\n")

  print("writing '" + output_filename + "'")
  with open(output_filename, 'w', encoding="utf-8") as file:
    file.writelines(ascii_tab_space(line) for line in new_lines)
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
  ordered_species = inp.make_species_list('', submodules_files.get_files())

  collider_only = [species.upper()
                   for species in ordered_species.collider_only]
  species_dict = SpeciesDictionary(
      ((species.upper(), 0) for species in ordered_species),
      collider_only=collider_only)
  for s in species_dict:
    species_dict[s] = 0
  return species_dict


def _build_tool_independent_submodel_key(tool_dependent_submodel_key):
  """Return a tool-independent filename key for one submodel.

  The key contains normalized submodule filenames. The mid encodes the
  submodule selection. Hence, both can identify a submodel. The tools are
  CHEMKIN-PRO and Cantera.
  """
  return tuple(sorted(
      c3mech_data.normalize_submodule_filename_for_tool_independent_key(name)
      for name in tool_dependent_submodel_key))


def _register_mid(mid_by_tool_independent_submodel_key,
                  tool_dependent_submodel_key, mid):
  """Map a tool-independent submodel key to its mid."""
  tool_independent_submodel_key = _build_tool_independent_submodel_key(
      tool_dependent_submodel_key)
  if tool_independent_submodel_key in mid_by_tool_independent_submodel_key:
    registered_mid = mid_by_tool_independent_submodel_key[
        tool_independent_submodel_key]
    if registered_mid != mid:
      raise RuntimeError(
          "MID mismatch for tool-independent submodel key " +
          str(tool_independent_submodel_key) + ": '" + registered_mid +
          "' != '" + mid + "'")
    print("Reusing MID ='" + mid + "'")
    return
  for registered_key, registered_mid in (
      mid_by_tool_independent_submodel_key.items()):
    if registered_mid == mid:
      raise RuntimeError(
          "MID '" + mid + "' identifies different tool-independent " +
          "submodel keys: " + str(registered_key) + " and " +
          str(tool_independent_submodel_key))
  mid_by_tool_independent_submodel_key[
      tool_independent_submodel_key] = mid
  print("new MID ='" + mid + "'")


def clean_therm(therm_output, species_list, species_pruned, header_filename,
                submodules_files, model_name, mid, species_output, datetime,
                header_text=None):
  print("writing '" + therm_output + "'")
  with open(therm_output, 'w', encoding="utf-8") as thermfile:

    thermfile.writelines(
        ascii_tab_space(line) for line in insert_boiler_plate(
            "Thermodynamic", model_name, submodules_files, datetime, mid,
            header_filename, header_text=header_text))

    thermfile.write(ascii_tab_space('THERMO ALL\n'))
    thermfile.write(ascii_tab_space('300.   1000.   5000.\n'))

    for s in species_list:
      addition = ""
      if s in species_pruned:
        addition = pruned_comment

      thermfile.write(ascii_tab_space(addition + species_output[s][0]))
      thermfile.write(ascii_tab_space(addition + species_output[s][1]))
      thermfile.write(ascii_tab_space(addition + species_output[s][2]))
      thermfile.write(ascii_tab_space(addition + species_output[s][3]))

    thermfile.write(ascii_tab_space('\nEND\n\n'))


def clean_tran(tran_file, tran_output, species_list, species_pruned,
               header_filename, submodules_files, model_name, mid, datetime,
               header_text=None):
  tran = open(tran_file, 'r', encoding="utf-8")
  tranlines = tran.readlines()
  tran.close()

  species_dict = {s.upper(): 0 for s in species_list}
  print("writing '" + tran_output + "'")
  with open(tran_output, 'w', encoding="utf-8") as tranfile:
    tranfile.writelines(
        ascii_tab_space(line) for line in insert_boiler_plate(
            "Transport", model_name, submodules_files, datetime, mid,
            header_filename, header_text=header_text))

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
              ascii_tab_space(
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
              ascii_tab_space(
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
                  tool_dependent_submodel_key,
                  mid,
                  write_therm_trans=True):
  species_list = make_clean_species_list(submodules_files)
  subset_unmatched_keys, restrictive_fix_keys, subset_unmatched_details, restrictive_match_warnings, parent_species_list, _ = _prepare_ht_subset_pruning(
      species_list, submodules_files)
  species_missing_in_parent = set(species_list.keys()) - set(
      parent_species_list.keys())
  if options.require_ht_subset_no_change:
    has_subset_effect = bool(subset_unmatched_keys or restrictive_fix_keys
                             or species_missing_in_parent)
    if has_subset_effect:
      print("#error: HT-vs-LT-HT subset checks found differences while "
            "'--require-ht-subset-no-change' is enabled.")
      print(
          "        This run is aborted to guarantee that subset logic has no "
          "effect on the generated output.")
      if len(subset_unmatched_keys):
        print("        unmatched HT reactions that would be commented out:",
              len(subset_unmatched_keys))
      if len(restrictive_fix_keys):
        print(
            "        reversible HT reactions that would be rewritten to "
            "irreversible:", len(restrictive_fix_keys))
      if len(species_missing_in_parent):
        print(
            "        species present in HT selection but missing in LT-HT "
            "parent:", len(species_missing_in_parent))
      raise Exception("#error: aborting due to HT-vs-LT-HT subset differences "
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

  mid_with_leading_underscore = "_" + mid

  kin_file = (options.model_name + mid_with_leading_underscore + output_chunk +
              output_chunk_kin + ".CKI")
  output_filename_kin = os.path.join(options.output_dir, output, kin_file)
  ns_printed, nr_printed = print_kinetics_file(species_list, species_pruned,
                                               options.header,
                                               submodules_files,
                                               options.model_name, mid,
                                               output_filename_kin, datetime,
                                               reactions, removed_reaction_ids,
                                               header_text=options.header_text,
                                               reorder=getattr(options, "reorder", True))

  therm_file = (options.model_name + mid_with_leading_underscore +
                output_chunk + ".THERM")
  property_output = os.path.dirname(output) if output_chunk_kin == "_IC" else output
  output_filename_therm = os.path.join(options.output_dir, property_output, therm_file)

  trans_filename = (options.model_name + mid_with_leading_underscore +
                    output_chunk + ".TRAN")
  output_filename_trans = os.path.join(options.output_dir, property_output,
                                       trans_filename)

  if write_therm_trans:
    clean_therm(output_filename_therm, species_list, species_pruned,
                options.header, submodules_files, options.model_name, mid,
                species_nasa_output, datetime,
                header_text=options.header_text)

    clean_tran(options.transfile, output_filename_trans, species_list,
               species_pruned, options.header, submodules_files,
               options.model_name, mid, datetime,
               header_text=options.header_text)
  else:
    # We deliberately do not write separate THERM/TRAN here.
    # The caller is responsible for pointing to canonical files.
    output_filename_therm = None
    output_filename_trans = None

  generated_combinations[tool_dependent_submodel_key] = {}
  generated_combinations[tool_dependent_submodel_key][
      "kin"] = output_filename_kin
  generated_combinations[tool_dependent_submodel_key][
      "therm"] = output_filename_therm
  generated_combinations[tool_dependent_submodel_key][
      "trans"] = output_filename_trans
  generated_combinations[tool_dependent_submodel_key]["dir"] = os.path.join(
      options.output_dir, output)
  generated_combinations[tool_dependent_submodel_key]["ns"] = ns_printed
  generated_combinations[tool_dependent_submodel_key]["nr"] = nr_printed
  generated_combinations[tool_dependent_submodel_key]["mid"] = mid

  return ns_printed, nr_printed, generated_combinations


def process_ck2yaml(tool_dependent_submodel_key, generated_combinations):

  output_filename_kin = generated_combinations[
      tool_dependent_submodel_key]["kin"]
  output_filename_therm = generated_combinations[
      tool_dependent_submodel_key]["therm"]
  output_filename_trans = generated_combinations[
      tool_dependent_submodel_key]["trans"]
  output_filename_dir = generated_combinations[
      tool_dependent_submodel_key]["dir"]
  if not _is_ic_kinetics_filename(output_filename_kin):
    output_yaml = os.path.splitext(output_filename_kin)[0] + ".yaml"
    converter = os.path.join(os.path.dirname(__file__), "lmrr.py")
    cmd = [
        sys.executable, converter, f"--input={output_filename_kin}",
        f"--thermo={output_filename_therm}",
        f"--transport={output_filename_trans}", f"--output={output_yaml}"
    ]
    result = subprocess.run(cmd,
                            cwd=output_filename_dir,
                            capture_output=True,
                            text=True)
    return (tool_dependent_submodel_key, output_filename_kin,
            result.returncode, result.stdout, result.stderr)
  else:
    return (tool_dependent_submodel_key, output_filename_kin, 0, "", "")


def _require_tool_compatible_submodule_filename(path, cantera):
  """Return the requested LOWMX/LOWSP or independent-collider (IC)
  submodule filename and fail if the submodule file is unavailable.
  """
  candidate = c3mech_data.select_tool_compatible_submodule_filename(
      path, cantera)
  if not os.path.isfile(candidate):
    tool = "IC" if cantera else "LOWMX/LOWSP"
    raise FileNotFoundError("required " + tool +
                            " submodule file not found: '" + candidate +
                            "'")
  return candidate


def _build_tool_dependent_submodel_key(submodules_filenames, selection,
                                       cantera):
  """Return the key and submodule filenames for a tool-dependent variant
  of a submodel.
  """
  c0 = 'C0'
  selected_non_core_submodule_filenames = []
  for smod, temp in selection.items():
    if smod.upper() == c0:
      continue
    path = submodules_filenames[temp][smod]
    path = _require_tool_compatible_submodule_filename(path, cantera)
    selected_non_core_submodule_filenames.append(path)

  core_filename = submodules_filenames[selection[c0]][c0]
  core_filename = _require_tool_compatible_submodule_filename(
      core_filename, cantera)

  selected_submodule_filenames = (
      [core_filename] + selected_non_core_submodule_filenames)
  return (tuple(sorted(selected_submodule_filenames)), core_filename,
          selected_non_core_submodule_filenames)


def one_carbon_number(options,
                      submodules_filenames,
                      datetime,
                      cnum,
                      data_dict,
                      generated_combinations,
                      mid_by_tool_independent_submodel_key,
                      counters=None,
                      cantera=True,
                      canonical_files=None):
  for selection_count, selection in enumerate(data_dict["modules"]):
    (tool_dependent_submodel_key, core_filename,
     selected_non_core_submodule_filenames) = (
        _build_tool_dependent_submodel_key(submodules_filenames, selection,
                                           cantera))

    submodules_files = inp.SubModulesFiles(
        core_filename, selected_non_core_submodule_filenames)
    submodules_files.insert_model_path(options.submodules_dir)

    # Historical cantera=True selects IC source files. File format and
    # collider formulation are independent; native Cantera YAML uses LMRR.
    carbon_dir = data_dict["output_dir"]
    tool_dir = "LEGACY" if cantera else ""

    name_with_temp = data_dict["output_chunks"][selection_count]
    temp_flag = data_dict["temperature"][
        selection_count]  # "HT", "LT-HT", or ""

    # Strip trailing "_HT" / "_LT-HT" for the directory name
    if temp_flag in ("HT", "LT-HT"):
      combo_dir = name_with_temp.rsplit("_", 1)[0]
    else:
      combo_dir = name_with_temp

    target_dir = os.path.join(carbon_dir, combo_dir, tool_dir)
    os.makedirs(target_dir, exist_ok=True)

    out_chunk = ""
    if cantera:
      out_chunk = "_IC"

    mid = data_dict["mid"][selection_count]
    _register_mid(mid_by_tool_independent_submodel_key,
                  tool_dependent_submodel_key, mid)

    if tool_dependent_submodel_key not in generated_combinations:
      # In --generate-all:
      #   - LMRR (cantera=False): write canonical THERM/TRAN.
      #   - IC (cantera=True): reuse those property files.
      write_therm_trans = True
      if options.generate_all and cantera:
        write_therm_trans = False

      ns_printed, nr_printed, generated_combinations = compile_model(
          options,
          submodules_files,
          output=target_dir,
          datetime=datetime,
          output_chunk=name_with_temp,
          output_chunk_kin=out_chunk,
          generated_combinations=generated_combinations,
          tool_dependent_submodel_key=tool_dependent_submodel_key,
          mid=mid,
          write_therm_trans=write_therm_trans)

      # Track canonical THERM/TRAN by MID (where they are actually written)
      if canonical_files is not None:
        therm_path = generated_combinations[tool_dependent_submodel_key][
            "therm"]
        trans_path = generated_combinations[tool_dependent_submodel_key][
            "trans"]
        if therm_path is not None and trans_path is not None:
          canonical_files[mid] = {
              "therm": therm_path,
              "trans": trans_path,
          }

      # For legacy IC in --generate-all, reuse the parent property files.
      if options.generate_all and cantera and canonical_files is not None:
        if mid not in canonical_files:
          raise Exception("Canonical THERM/TRAN missing for MID '" + mid +
                          "' when generating legacy IC files")
        generated_combinations[tool_dependent_submodel_key][
            "therm"] = canonical_files[mid]["therm"]
        generated_combinations[tool_dependent_submodel_key][
            "trans"] = canonical_files[mid]["trans"]

      if counters is not None:
        if mid in counters:
          if counters[mid][1] != ns_printed or counters[mid][2] != nr_printed:
            raise Exception("duplicate MID '" + mid + "' for " +
                            str((selection, ns_printed, nr_printed)) +
                            " (new) and " + str(counters[mid]))
        counters[mid] = (selection, ns_printed, nr_printed)
    else:
      if counters is not None and mid not in counters:
        raise Exception("duplicate tool-dependent submodel key " +
                        str(tool_dependent_submodel_key) +
                        " must have counter but '" + mid + "' was not found")
      # if a sub-module combination was used before
      # this is because there is no distinction between
      # HT and LT-HT for this combination
      aux = ["kin", "therm", "trans"]
      for f in aux:
        fname = generated_combinations[tool_dependent_submodel_key][f]
        if fname is None:
          continue
        if (not cantera and
            _is_ic_kinetics_filename(fname)):
          raise Exception(
              "LMRR output has an IC " +
              "kinetics filename: '" + fname + "'")
        dir_name = os.path.dirname(fname)
        base_name = os.path.basename(fname)
        new_base = base_name.replace('_LT-HT', '').replace('_HT', '')
        new_fname = os.path.join(dir_name, new_base)
        if new_fname != fname:
          print(
              f"Renaming {os.path.basename(fname)} -> {os.path.basename(new_fname)}"
          )
          generated_combinations[tool_dependent_submodel_key][f] = new_fname
          os.rename(fname, new_fname)

      # After renaming, refresh canonical THERM/TRAN for this MID
      if canonical_files is not None:
        therm_path = generated_combinations[tool_dependent_submodel_key][
            "therm"]
        trans_path = generated_combinations[tool_dependent_submodel_key][
            "trans"]
        if therm_path is not None and trans_path is not None:
          canonical_files[mid] = {
              "therm": therm_path,
              "trans": trans_path,
          }

  return generated_combinations

def _require_selected_species_data(options, submodules_filenames,
                                   grouped_selections):
  """Require thermochemistry and transport records before model generation.

  Read each distinct submodule once per core, including LOWMX/LOWSP
  and independent-collider (IC) submodules for --generate-all. Use only selections
  scheduled for generation, so excluded submodules and the carbon limit do not
  add required species.
  """
  print("Checking thermochemistry and transport availability...", flush=True)
  cantera_modes = ((False, True) if options.generate_all else
                    (c3mech_data.detect_cantera_mode(submodules_filenames),))
  submodules_by_core = {}
  for cantera in cantera_modes:
    for data_dict in grouped_selections.values():
      for selection in data_dict["modules"]:
        _, core, submodules = _build_tool_dependent_submodel_key(
            submodules_filenames, selection, cantera)
        selected = submodules_by_core.setdefault(core, {})
        selected.update(dict.fromkeys(submodules))
  if not submodules_by_core:
    raise c3mech_data.UserInputError("no submodels selected for generation")

  species = set()
  for core, submodules in submodules_by_core.items():
    species.update(name.upper() for name in inp.make_species_list(
        "", [core, *submodules]))
  inp.require_species_data(options.thermfile, options.transfile, species)
  print("Thermochemistry and transport records available for all " +
        str(len(species)) + " required species.", flush=True)


def run(options, submodules_filenames, grouped_selections, columns, carbon_map,
        included_keys, submodule_labels):

  print("read input...")
  _require_selected_species_data(options, submodules_filenames,
                                 grouped_selections)
  DATETIME = datetime.datetime.now()

  if options.generate_all:
    generated_combinations = {}
    mid_by_tool_independent_submodel_key = {}
    submodules_filename = options.yaml_file_path

    counters = {}
    # MID -> {"therm": path, "trans": path}
    canonical_files = {}

    # Compile LMRR first (cantera=False), then legacy IC (cantera=True).
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
            mid_by_tool_independent_submodel_key,
            counters=counters,
            cantera=cantera,
            canonical_files=canonical_files)

    tasks = []
    with ThreadPoolExecutor(max_workers=options.max_threads) as executor:
      for tool_dependent_submodel_key in generated_combinations:
        if options.process_cantera and not _is_ic_kinetics_filename(
            generated_combinations[tool_dependent_submodel_key]["kin"]):
          tasks.append(
              executor.submit(process_ck2yaml, tool_dependent_submodel_key,
                              generated_combinations))

      for future in as_completed(tasks):
        (tool_dependent_submodel_key, _, returncode, stdout,
         stderr) = future.result()
        print(f"\n=== {tool_dependent_submodel_key} ===")
        print(stdout)
        print(stderr)
        _validate_ck2yaml_result(tool_dependent_submodel_key, returncode,
                                 stdout, stderr)
        print("processing with cantera was successful!")

    template_root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "templates", "model_catalog")
    inventory = distribution.build_inventory(
        options, grouped_selections, included_keys, submodule_labels,
        counters, compiler_version)
    catalog, manifest = distribution.render_model_catalog(
        options, inventory, columns, carbon_map, tuple(submodule_labels),
        os.path.join(template_root, "MODEL_CATALOG.md.in"),
        os.path.join(template_root, "quick_access.yaml"),
        options.c3mech_configuration)
    distribution.publish_model_catalog(options.output_dir, catalog, manifest)
    print("writing:", os.path.join(options.output_dir,
                                    "MODEL_MANIFEST.json"))
    print("writing:", os.path.join(options.output_dir, "MODEL_CATALOG.md"))
  else:

    generated_combinations_single = {}
    mid_by_tool_independent_submodel_key_single = {}
    canonical_files_single = {}
    cantera_mode = c3mech_data.detect_cantera_mode(submodules_filenames)
    for cnum, data_dict in grouped_selections.items():
      generated_combinations_single = one_carbon_number(
          options,
          submodules_filenames,
          DATETIME,
          cnum,
          data_dict,
          generated_combinations_single,
          mid_by_tool_independent_submodel_key_single,
          cantera=cantera_mode,
          canonical_files=canonical_files_single)

    for tool_dependent_submodel_key in generated_combinations_single:
      # --- Process with ck2yaml if requested ---
      if options.process_cantera and not _is_ic_kinetics_filename(
          generated_combinations_single[tool_dependent_submodel_key]["kin"]):
        result = process_ck2yaml(tool_dependent_submodel_key,
                                 generated_combinations_single)

        _, _, returncode, stdout, stderr = result
        print(stdout)
        print(stderr)

        _validate_ck2yaml_result(tool_dependent_submodel_key, returncode,
                                 stdout, stderr)
        print("processing with cantera was successful!")
