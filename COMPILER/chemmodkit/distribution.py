"""Validated documentation and inventory for ``--generate-all`` output."""

import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path, PurePosixPath
from urllib.parse import quote

import yaml

from .generation_timestamp import normalize_generated_file_bytes


TEMPLATE_FIELDS = (
    "MODEL_NAME",
    "CONTACT_LINE",
    "DEBUG_WARNING",
    "FULL_MODEL",
    "FILE_LAYOUT",
    "QUICK_ACCESS_TABLE",
    "DETAILED_TABLES",
)
MID_RE = re.compile(r"model ID \(MID\):\s*([A-Za-z0-9]+)", re.IGNORECASE)
COUNT_RE = re.compile(
    r"Mechanism contains\s+(\d+)\s+species\s+and\s+(\d+)\s+reactions",
    re.IGNORECASE)
ARTIFACT_TIMESTAMP_TYPES = {
    "cantera_reactions": ("Kinetics",),
    "cantera_yaml": ("Kinetics", "Thermodynamic"),
    "chemkin_reactions": ("Kinetics",),
    "thermochemistry": ("Thermodynamic",),
    "transport": ("Transport",),
}


def source_identity(repo_root):
  """Return the Git source identity and whether the source tree is dirty."""
  unavailable = {
      "source_commit": None,
      "source_tree": None,
      "source_dirty": True,
  }
  git = shutil.which("git")
  if git is None:
    return unavailable
  top_level = subprocess.run(
      [git, "-C", str(repo_root), "rev-parse", "--show-toplevel"],
      check=False,
      capture_output=True,
      text=True)
  commit = subprocess.run(
      [git, "-C", str(repo_root), "rev-parse", "--verify", "HEAD^{commit}"],
      check=False,
      capture_output=True,
      text=True)
  tree = subprocess.run(
      [git, "-C", str(repo_root), "rev-parse", "--verify", "HEAD^{tree}"],
      check=False,
      capture_output=True,
      text=True)
  status = subprocess.run([
      git, "-C",
      str(repo_root), "status", "--porcelain=v1", "--untracked-files=all"
  ],
                          check=False,
                          capture_output=True,
                          text=True)
  if (top_level.returncode != 0
      or Path(top_level.stdout.strip()).resolve() != Path(repo_root).resolve()
      or commit.returncode != 0 or tree.returncode != 0
      or status.returncode != 0):
    return unavailable
  return {
      "source_commit": commit.stdout.strip(),
      "source_tree": tree.stdout.strip(),
      "source_dirty": bool(status.stdout),
  }


def require_empty_output_root(output_dir):
  """Require a dedicated output root before a full generation begins."""
  entries = sorted(name for name in os.listdir(output_dir)
                   if name != ".gitignore")
  if entries:
    raise ValueError(
        "--generate-all requires an empty output directory except for "
        "'.gitignore'. Found: " + ", ".join(entries))


def validate_cantera_success(stdout):
  if "Validating mechanism..." not in stdout or not re.search(
      r"^PASSED\s*$", stdout, re.MULTILINE):
    raise ValueError("Cantera output does not report successful validation")
  if len(COUNT_RE.findall(stdout)) != 1:
    raise ValueError(
        "expected exactly one Cantera species/reaction parse summary")


def relative_artifact_path(path, output_root):
  root = Path(output_root).resolve()
  target = Path(path).resolve()
  if target != root and root not in target.parents:
    raise ValueError("generated artifact is outside output directory: " +
                     str(path))
  relative = target.relative_to(root)
  pure = PurePosixPath(relative.as_posix())
  if pure.is_absolute() or ".." in pure.parts:
    raise ValueError("invalid generated relative path: " + str(pure))
  if not target.is_file() or target.stat().st_size == 0:
    raise ValueError("generated artifact is missing or empty: " + str(path))
  return pure.as_posix()


def _sha256(data):
  return hashlib.sha256(data).hexdigest()


def _normalized_sha256(data, expected_filetypes, expected_model_name):
  normalized = normalize_generated_file_bytes(
      data, expected_filetypes, expected_model_name)
  return _sha256(normalized)


def _mid_from_text(text, path):
  matches = MID_RE.findall(text)
  unique = {match.upper() for match in matches}
  if len(unique) != 1:
    raise ValueError("expected one unique MID in '" + str(path) + "'")
  return unique.pop()


def _artifact(path, output_root, expected_mid, expected_model_name,
              expected_filetypes):
  relative = relative_artifact_path(path, output_root)
  data = Path(path).read_bytes()
  header = data.decode("utf-8")[:32768]
  if expected_model_name not in header:
    raise ValueError("model-name mismatch for '" + relative + "'")
  actual_mid = _mid_from_text(header, path)
  if actual_mid != expected_mid.upper():
    raise ValueError("MID mismatch for '" + relative + "': expected " +
                     expected_mid + ", found " + actual_mid)
  return {
      "path": relative,
      "sha256": _sha256(data),
      "normalized_sha256": _normalized_sha256(
          data, expected_filetypes, expected_model_name),
  }


def _combo_directory(data, index):
  chunk = data["output_chunks"][index]
  temperature = data["temperature"][index]
  if temperature in ("HT", "LT-HT"):
    return chunk.rsplit("_", 1)[0]
  return chunk


def _expected_paths(options, data, index, shared_temperature):
  mid = data["mid"][index].upper()
  chunk = _combo_directory(data, index)
  temperature = "" if shared_temperature else "_" + data["temperature"][index]
  stem = options.model_name + "_" + mid + "_" + chunk + temperature
  combination_dir = os.path.join(data["output_dir"], chunk)
  chemkin_dir = os.path.join(combination_dir, "Chemkin")
  cantera_dir = os.path.join(combination_dir, "Cantera")
  paths = {
      "chemkin_reactions": os.path.join(chemkin_dir, stem + ".CKI"),
      "thermochemistry": os.path.join(chemkin_dir, stem + ".THERM"),
      "transport": os.path.join(chemkin_dir, stem + ".TRAN"),
      "cantera_reactions": os.path.join(cantera_dir,
                                         stem + "_Cantera.CKI"),
  }
  if options.process_cantera:
    paths["cantera_yaml"] = os.path.join(cantera_dir,
                                          stem + "_Cantera.yaml")
  return combination_dir, paths


def build_inventory(options, grouped_selections, included_keys,
                    submodule_labels, counters, compiler_version):
  """Build and validate the generated model inventory.

  ``options.c3mech_configuration`` must contain the selected configuration.
  Its digest is recorded in ``c3mech_configuration_sha256``. A missing
  configuration raises ``ValueError``.
  """
  configuration = getattr(options, "c3mech_configuration", None)
  if configuration is None:
    raise ValueError(
        "C3Mech configuration is required to build the model inventory")
  records = []
  mids_to_selections = {}
  for carbon_number in sorted(grouped_selections):
    data = grouped_selections[carbon_number]
    pairs = {}
    for index, selection in enumerate(data["modules"]):
      keys = tuple(sorted(selection))
      pairs.setdefault(keys, []).append(index)

    for keys in sorted(pairs):
      indices = pairs[keys]
      temperatures = {data["temperature"][i] for i in indices}
      if temperatures != {"HT", "LT-HT"} or len(indices) != 2:
        raise ValueError("expected one HT and one LT-HT model for " + str(keys))
      mids = {data["mid"][i].upper() for i in indices}
      shared_temperature = len(mids) == 1
      for index in sorted(indices,
                          key=lambda i: data["temperature"][i]):
        mid = data["mid"][index].upper()
        selection_key = tuple(sorted(data["modules"][index]))
        previous = mids_to_selections.setdefault(mid, selection_key)
        if previous != selection_key:
          raise ValueError("MID '" + mid +
                           "' identifies different submodule selections")
        if mid not in counters:
          raise ValueError("missing generated counts for MID '" + mid + "'")
        counter_selection, species_count, reaction_count = counters[mid]
        if tuple(sorted(counter_selection)) != selection_key:
          raise ValueError("generated count selection mismatch for MID '" +
                           mid + "'")

        combination_dir, paths = _expected_paths(options, data, index,
                                                   shared_temperature)
        artifacts = {
            name: _artifact(path, options.output_dir, mid, options.model_name,
                            ARTIFACT_TIMESTAMP_TYPES[name])
            for name, path in sorted(paths.items())
        }
        directory = Path(combination_dir).resolve().relative_to(
            Path(options.output_dir).resolve()).as_posix()
        records.append({
            "carbon_group": os.path.basename(data["output_dir"]),
            "directory": directory,
            "modules": list(selection_key),
            "temperature_range": data["temperature"][index],
            "mid": mid,
            "chemkin_species_count": species_count,
            "chemkin_reaction_count": reaction_count,
            "artifacts": artifacts,
        })

  records.sort(key=lambda item: (item["carbon_group"], item["modules"],
                                 item["temperature_range"]))
  source = source_identity(Path(__file__).resolve().parents[2])
  return {
      "schema_version": 5,
      "model_name": options.model_name,
      "model_version": options.version,
      "c3mech_configuration_sha256": configuration.sha256,
      "compiler_version": compiler_version,
      "source_commit": source["source_commit"],
      "source_tree": source["source_tree"],
      "source_dirty": source["source_dirty"],
      "pruning_enabled": options.prune,
      "maximum_carbon_count": options.max_c,
      "cantera_yaml_generated": options.process_cantera,
      "included_submodules": [{
          "key": key,
          "label": submodule_labels[key]
      } for key in included_keys],
      "models": records,
  }


def _load_quick_access(path, included_keys, known_keys=None):
  with open(path, "r", encoding="utf-8") as stream:
    data = yaml.safe_load(stream)
  if not isinstance(data, dict) or set(data) != {"quick_access"}:
    raise ValueError("quick-access file must contain only 'quick_access'")
  entries = data["quick_access"]
  if not isinstance(entries, list) or not entries:
    raise ValueError("quick_access must be a nonempty list")
  labels = set()
  selections = set()
  result = []
  allowed_fields = {"label", "modules", "note"}
  for entry in entries:
    if not isinstance(entry, dict) or not {"label", "modules"} <= set(entry):
      raise ValueError("each quick-access entry requires label and modules")
    unknown = set(entry) - allowed_fields
    if unknown:
      raise ValueError("unknown quick-access fields: " +
                       ", ".join(sorted(unknown)))
    label = entry["label"]
    modules = tuple(sorted(entry["modules"]))
    if not isinstance(label, str) or not label.strip():
      raise ValueError("quick-access label must be nonempty text")
    if len(modules) != len(set(modules)):
      raise ValueError("duplicate module in quick-access entry '" + label + "'")
    note = entry.get("note", "")
    if not isinstance(note, str):
      raise ValueError("quick-access note must be text for '" + label + "'")
    missing_modules = set(modules) - set(included_keys)
    if missing_modules:
      if known_keys is not None:
        unknown_modules = missing_modules - set(known_keys)
        if unknown_modules:
          raise ValueError(
              "quick-access entry '" + label + "' contains unknown "
              "submodules: " + ", ".join(sorted(unknown_modules)))
        continue
      raise ValueError(
          "quick-access entry '" + label + "' requires submodules not "
          "included in this model collection: " +
          ", ".join(sorted(missing_modules)))
    if label in labels or modules in selections:
      raise ValueError("duplicate quick-access label or selection")
    labels.add(label)
    selections.add(modules)
    result.append({
        "label": label,
        "modules": modules,
        "note": note,
    })
  return result


def _paired_models(inventory):
  paired = {}
  for model in inventory["models"]:
    key = tuple(model["modules"])
    temperature = model["temperature_range"]
    if temperature in paired.setdefault(key, {}):
      raise ValueError("duplicate generated model for " + str((key, temperature)))
    paired[key][temperature] = model
  for key, temperatures in paired.items():
    if set(temperatures) != {"HT", "LT-HT"}:
      raise ValueError("incomplete temperature pair for " + str(key))
    if temperatures["HT"]["directory"] != temperatures["LT-HT"]["directory"]:
      raise ValueError("temperature pair uses different directories")
  return paired


def _markdown_table(headers, rows):
  widths = [len(header) for header in headers]
  for row in rows:
    widths = [max(width, len(str(cell)))
              for width, cell in zip(widths, row)]
  header = "| " + " | ".join(
      value.ljust(width) for value, width in zip(headers, widths)) + " |"
  separator = "|" + "|".join(":" + "-" * width + ":"
                               for width in widths) + "|"
  body = ["| " + " | ".join(
      str(value).ljust(width) for value, width in zip(row, widths)) + " |"
          for row in rows]
  return "\n".join([header, separator] + body)


def _pair_values(pair):
  ht = pair["HT"]
  ltht = pair["LT-HT"]
  return (
      str(ht["chemkin_species_count"]) + "/" +
      str(ltht["chemkin_species_count"]),
      str(ht["chemkin_reaction_count"]) + "/" +
      str(ltht["chemkin_reaction_count"]),
      "`" + ht["directory"] + "/`",
      "[" + ht["mid"] + "/" + ltht["mid"] + "](" +
      ht["directory"] + "/)",
  )


def _quick_access_table(entries, paired, columns, max_c, carbon_map):
  rows = []
  notes = []
  headers = (["Use case", "Directory", "MID(HT/LT-HT)"] +
             [label for _, label in columns] +
             ["CHEMKIN NS(HT/LT-HT)", "CHEMKIN NR(HT/LT-HT)"])
  for entry in entries:
    maximum = max([carbon_map.get(key, -1) for key in entry["modules"]] + [0])
    if max_c is not None and maximum > max_c:
      continue
    if entry["modules"] not in paired:
      raise ValueError("eligible quick-access selection was not generated: " +
                       entry["label"])
    pair = paired[entry["modules"]]
    ns, nr, directory, linked_mid = _pair_values(pair)
    row = [entry["label"], directory, linked_mid]
    selected = set(entry["modules"])
    row.extend("✓" if key in selected else "" for key, _ in columns)
    row.extend([ns, nr])
    rows.append(row)
    if entry["note"]:
      notes.append("- **" + entry["label"] + ":** " + entry["note"])
  if not rows:
    return "No configured quick-access selection is available for this carbon limit."
  rendered = _markdown_table(headers, rows)
  if notes:
    rendered += "\n\n" + "\n".join(notes)
  return rendered


def _detailed_tables(paired, columns):
  by_group = {}
  for selection, pair in paired.items():
    group = pair["HT"]["carbon_group"]
    by_group.setdefault(group, []).append((selection, pair))
  sections = []
  headers = ([label for _, label in columns] + ["Directory"] +
             ["CHEMKIN NS(HT/LT-HT)", "CHEMKIN NR(HT/LT-HT)",
              "MID(HT/LT-HT)"])
  for group in sorted(by_group, key=lambda value: (value == "C8+", value)):
    rows = []
    pairs = sorted(by_group[group],
                   key=lambda item: item[1]["HT"]["chemkin_species_count"])
    for selection, pair in pairs:
      ns, nr, directory, linked_mid = _pair_values(pair)
      selected = set(selection)
      row = ["✓" if key in selected else "" for key, _ in columns]
      row.extend([directory, ns, nr, linked_mid])
      rows.append(row)
    sections.append("### [" + group + "/](" + group + "/)\n\n" +
                    _markdown_table(headers, rows))
  return "\n\n".join(sections)


def _debug_warning(inventory, carbon_map):
  maximum_supported = max(carbon_map.values(), default=0)
  maximum_generated = inventory["maximum_carbon_count"]
  if maximum_generated is None or maximum_generated >= maximum_supported:
    return ""
  return (
      "> **Warning:** This is incomplete debug output generated with "
      "`--max-c " + str(maximum_generated) + "`. It must not be distributed "
      "as a complete set of " + inventory["model_name"] + " sub-models.")


def _full_model_section(inventory, paired, included_keys, carbon_map):
  full_selection = tuple(sorted(included_keys))
  maximum = max([carbon_map.get(key, -1) for key in full_selection] + [0])
  maximum_generated = inventory["maximum_carbon_count"]
  if maximum_generated is not None and maximum > maximum_generated:
    return ""
  if full_selection not in paired:
    raise ValueError("the full model is missing")
  full_model = paired[full_selection]["LT-HT"]
  directory = full_model["directory"] + "/"
  linked_directory = "[`" + directory + "`](" + directory + ")"
  return ("The full " + inventory["model_name"] +
          " model corresponds to the directory " + linked_directory +
          " with MID `" + full_model["mid"] + "`.")


def _file_layout(cantera_enabled, model_name):
  text = (
      "Every sub-model directory has the same layout:\n\n"
      "- `Chemkin/` contains a complete CHEMKIN-format chemical kinetic "
      "model:\n"
      "  - `" + model_name + "_*.CKI` contains species declarations and "
      "reactions.\n"
      "  - `" + model_name + "_*.THERM` contains thermochemistry data.\n"
      "  - `" + model_name + "_*.TRAN` contains transport data.\n"
      "- `Cantera/` contains the Cantera/FlameMaster-compatible `" +
      model_name + "_*_Cantera.CKI` file.")
  if cantera_enabled:
    text += ("\n  - `" + model_name +
             "_*_Cantera.yaml` is the validated Cantera YAML file.")
  else:
    text += "\n\nCantera YAML files were not generated."
  return text


def _render_template(path, values):
  with open(path, "r", encoding="utf-8") as stream:
    text = stream.read()
  found = re.findall(r"\{\{([A-Z0-9_]+)\}\}", text)
  if sorted(found) != sorted(TEMPLATE_FIELDS):
    raise ValueError(
        "model-catalog template fields must occur exactly once: " +
        ", ".join(TEMPLATE_FIELDS))
  if set(values) != set(TEMPLATE_FIELDS):
    raise ValueError(
        "model-catalog renderer fields do not match template fields")
  for field in TEMPLATE_FIELDS:
    text = text.replace("{{" + field + "}}", values[field])
  unresolved = re.findall(r"\{\{[^{}]+\}\}", text)
  if unresolved:
    raise ValueError("unresolved model-catalog template fields: " +
                     ", ".join(unresolved))
  text = re.sub(r"\n{3,}", "\n\n", text)
  return text.rstrip() + "\n"


def _validate_markdown_links(catalog, output_root):
  root = Path(output_root).resolve()
  for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", catalog):
    if re.match(r"^(?:https?|mailto):", target, re.IGNORECASE):
      continue
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
      raise ValueError("model catalog contains an unsupported link: " + target)
    pure = PurePosixPath(target)
    if pure.is_absolute():
      raise ValueError("model catalog contains an absolute local link: " +
                       target)
    if ".." in pure.parts:
      raise ValueError("model catalog contains a parent-directory link: " +
                       target)
    resolved = (root / Path(*pure.parts)).resolve()
    if resolved != root and root not in resolved.parents:
      raise ValueError("model-catalog link target is outside output directory: "
                       + target)
    if not resolved.exists():
      raise ValueError("model-catalog link target does not exist: " + target)


def _markdown_link_label(text):
  escaped = html.escape(text, quote=False)
  escaped = re.sub(r"([\\\[\]*_`~])", r"\\\1", escaped)
  protected_spaces = {"\N{NO-BREAK SPACE}", "\N{FIGURE SPACE}",
                      "\N{NARROW NO-BREAK SPACE}"}
  return "".join(
      character if character in protected_spaces
      else "\N{NO-BREAK SPACE}"
      if unicodedata.category(character) == "Zs" else character
      for character in escaped)


def _markdown_destination(url):
  return quote(url, safe=":/@!$&'*+,;=-._~%")


def _mailto_destination(email):
  return quote(email, safe="@.!$&'*+-/=_~")


def _contact_line(configuration):
  if configuration is None:
    raise ValueError(
        "C3Mech configuration is required to render the model catalog")
  authors = {author.identifier: author for author in configuration.authors}
  contacts = []
  for identifier in configuration.contact_author_ids:
    author = authors[identifier]
    contacts.append(
        "[" + _markdown_link_label(author.name) + "](mailto:" +
        _mailto_destination(author.email) + ")")
  repository_url = _markdown_destination(
      configuration.project.source_repository_url)
  return ("For questions or suggestions, visit the [source repository](" +
          repository_url + ") or contact " + " or ".join(contacts) + ".")


def render_model_catalog(options, inventory, columns, carbon_map, known_keys,
                         template_path, quick_access_path, configuration):
  """Render the model catalog using the selected C3Mech configuration.

  ``configuration.sha256`` must equal the inventory field
  ``c3mech_configuration_sha256``. A missing configuration, a missing digest
  field, or a digest mismatch raises ``ValueError``.
  """
  if configuration is None:
    raise ValueError(
        "C3Mech configuration is required to render the model catalog")
  if "c3mech_configuration_sha256" not in inventory:
    raise ValueError(
        "model inventory is missing c3mech_configuration_sha256")
  if (inventory.get("c3mech_configuration_sha256") !=
      configuration.sha256):
    raise ValueError(
        "model inventory c3mech_configuration_sha256 differs from the "
        "selected C3Mech configuration")
  paired = _paired_models(inventory)
  included_keys = [item["key"] for item in inventory["included_submodules"]]
  selected_columns = [column for column in columns
                      if column[0] in included_keys]
  quick_entries = _load_quick_access(
      quick_access_path, included_keys,
      known_keys=known_keys)
  values = {
      "MODEL_NAME": inventory["model_name"],
      "CONTACT_LINE": _contact_line(configuration),
      "DEBUG_WARNING": _debug_warning(inventory, carbon_map),
      "FULL_MODEL": _full_model_section(inventory, paired, included_keys,
                                         carbon_map),
      "FILE_LAYOUT": _file_layout(inventory["cantera_yaml_generated"],
                                   inventory["model_name"]),
      "QUICK_ACCESS_TABLE": _quick_access_table(
          quick_entries, paired, selected_columns,
          inventory["maximum_carbon_count"],
          carbon_map),
      "DETAILED_TABLES": _detailed_tables(paired, selected_columns),
  }
  catalog = _render_template(template_path, values)
  _validate_markdown_links(catalog, options.output_dir)
  manifest = json.dumps(inventory, indent=2, sort_keys=False) + "\n"
  return catalog, manifest


def publish_model_catalog(output_dir, catalog, manifest):
  """Publish both model documents, with the catalog as completion marker."""
  root = Path(output_dir)
  manifest_fd = None
  catalog_fd = None
  manifest_tmp = None
  catalog_tmp = None
  try:
    manifest_fd, manifest_tmp = tempfile.mkstemp(prefix=".MODEL_MANIFEST.",
                                                  dir=root, text=True)
    catalog_fd, catalog_tmp = tempfile.mkstemp(prefix=".MODEL_CATALOG.",
                                                dir=root, text=True)
    with os.fdopen(manifest_fd, "w", encoding="utf-8",
                   newline="\n") as stream:
      manifest_fd = None
      stream.write(manifest)
      stream.flush()
      os.fsync(stream.fileno())
    with os.fdopen(catalog_fd, "w", encoding="utf-8",
                   newline="\n") as stream:
      catalog_fd = None
      stream.write(catalog)
      stream.flush()
      os.fsync(stream.fileno())
    os.chmod(manifest_tmp, 0o644)
    os.chmod(catalog_tmp, 0o644)
    manifest_path = root / "MODEL_MANIFEST.json"
    catalog_path = root / "MODEL_CATALOG.md"
    os.replace(manifest_tmp, manifest_path)
    manifest_tmp = None
    os.replace(catalog_tmp, catalog_path)
    catalog_tmp = None
  except BaseException:
    if manifest_fd is not None:
      os.close(manifest_fd)
    if catalog_fd is not None:
      os.close(catalog_fd)
    if manifest_tmp is not None:
      Path(manifest_tmp).unlink(missing_ok=True)
    if catalog_tmp is not None:
      Path(catalog_tmp).unlink(missing_ok=True)
    (root / "MODEL_MANIFEST.json").unlink(missing_ok=True)
    (root / "MODEL_CATALOG.md").unlink(missing_ok=True)
    raise
