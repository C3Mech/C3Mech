#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import re
import shutil
from pathlib import Path

if __package__:
  from . import c3mech_data as c3mech
  from . import c3mech_header
  from .chemmodkit import __version__
  from .chemmodkit import distribution
  from .chemmodkit.errors import ExternalToolError
else:
  import c3mech_data as c3mech
  import c3mech_header
  from chemmodkit import __version__
  from chemmodkit import distribution
  from chemmodkit.errors import ExternalToolError

DIR = os.path.dirname(os.path.abspath(__file__))
YAML = "submodules.yaml"
OUTPUT = "output"
default_yaml_file_path = os.path.join(DIR, YAML)
_MODEL_NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]*")


def _format_options(options):
  configuration_path = getattr(
      getattr(options, "c3mech_configuration", None), "source_path", None)
  return ("Options(\n"
          f"  generate_all={getattr(options, 'generate_all', None)},\n"
          f"  max_c={getattr(options, 'max_c', None)},\n"
          f"  prune={getattr(options, 'prune', None)},\n"
          f"  reorder={getattr(options, 'reorder', True)},\n"
          "  process_cantera=" +
          str(getattr(options, "process_cantera", None)) + ",\n"
          f"  model_name='{getattr(options, 'model_name', None)}',\n"
          "  yaml_file_path='" +
          str(getattr(options, "yaml_file_path", None)) + "',\n"
          "  submodules_dir='" +
          str(getattr(options, "submodules_dir", None)) + "',\n"
          f"  mid='{getattr(options, 'mid', None)}',\n"
          f"  mid_cantera={getattr(options, 'mid_cantera', None)},\n"
          f"  thermfile='{getattr(options, 'thermfile', None)}',\n"
          f"  transfile='{getattr(options, 'transfile', None)}',\n"
          f"  header='{getattr(options, 'header', None)}',\n"
          f"  version='{getattr(options, 'version', None)}',\n"
          f"  output_dir='{getattr(options, 'output_dir', None)}',\n"
          "  selected_submodules=" +
          str(getattr(options, "selected_submodules", None)) + ",\n"
          f"  c3mech_configuration_path={configuration_path!r},\n"
          "  header_text_supplied=" +
          str(getattr(options, "header_text", None) is not None) + ",\n"
          "  require_ht_subset_no_change=" +
          str(getattr(options, "require_ht_subset_no_change", None)) + "\n"
          ")")


class Options:

  def __init__(self, generate_all, max_c, prune, process_cantera, max_threads,
               model_name, yaml_file_path, submodules_dir, mid, mid_cantera,
               thermfile, transfile, header, version, output_dir,
               require_ht_subset_no_change, selected_submodules=None,
               c3mech_configuration=None, header_text=None, reorder=True):
    self.generate_all = generate_all
    self.max_c = max_c
    self.reorder = reorder
    self.prune = prune
    self.process_cantera = process_cantera
    self.max_threads = max_threads
    self.model_name = model_name
    self.yaml_file_path = yaml_file_path
    self.submodules_dir = submodules_dir
    self.mid = mid
    self.mid_cantera = mid_cantera
    self.thermfile = thermfile
    self.transfile = transfile
    self.header = header
    self.version = version
    self.output_dir = output_dir
    self.require_ht_subset_no_change = require_ht_subset_no_change
    self.selected_submodules = selected_submodules
    self.c3mech_configuration = c3mech_configuration
    self.header_text = header_text

  def __repr__(self):
    return _format_options(self)


def parse_args():
  current_configuration = c3mech.load_c3mech_configuration(
      c3mech.CURRENT_CONFIGURATION_PATH)
  parser = argparse.ArgumentParser(
      description="chemmodkit: Modular chemical kinetic model builder")
  parser.add_argument('--generate-all',
                      action='store_true',
                      help='Generate all model combinations (default: False)')
  parser.add_argument('--max-c',
                      type=int,
                      default=None,
                      help=('Maximum carbon count for models '
                            '(default: no limit)'))
  parser.add_argument(
      '--max-threads',
      type=int,
      default=8,
      help='Maximum number of threads for Cantera execution (default: 8)')
  parser.add_argument('--prune',
                      dest='prune',
                      action='store_true',
                      help='Enable pruning of the model (default: False)')
  parser.add_argument('--no-prune',
                      dest='prune',
                      action='store_false',
                      help='Disable pruning of the model')
  parser.set_defaults(prune=False)
  parser.add_argument(
      "--reorder", choices=("true", "false"), default="true",
      help="Group reactions by canonical representation (default: true). "
           "Use false to preserve source order and reaction-class markers.")

  parser.add_argument(
      '--process-cantera',
      dest='process_cantera',
      action='store_true',
      help="Process output with Cantera's ck2yaml (default: True)")
  parser.add_argument('--no-process-cantera',
                      dest='process_cantera',
                      action='store_false',
                      help="Do not process output with Cantera's ck2yaml")
  parser.add_argument(
      '--require-ht-subset-no-change',
      action='store_true',
      help=("Fail immediately if HT-vs-LT-HT subset checks would alter output "
            "(e.g., removed reactions or irreversible rewrites)."))
  parser.add_argument(
      '--mid',
      type=str,
      default="",
      help="model ID (MID) that is used to generate a sub-model")
  parser.add_argument(
      '--mid-ic', '--mid-cantera',
      dest='mid_cantera',
      action='store_true',
      help=
      "Use independent-collider (IC) submodules (default: True, only relevant when decoding an MID)"
  )
  parser.add_argument(
      '--no-mid-ic', '--no-mid-cantera',
      dest='mid_cantera',
      action='store_false',
      help=
      "Use LOWMX/LOWSP linear-mixture-rule submodules (only relevant when decoding an MID)"
  )
  parser.add_argument(
      '--yaml-file-path',
      type=str,
      default=default_yaml_file_path,
      help="YAML input file specifying the sub-modules (default: " +
      default_yaml_file_path + ")")
  # assumes the sub-modules directory can be found relative to this file
  default_submodules_dir = c3mech.get_submodules_dir(DIR)
  parser.add_argument('--submodules-dir',
                      type=str,
                      default=default_submodules_dir,
                      help="directory for the sub-modules (default: " +
                      default_submodules_dir + ")")

  # assumes that output should be relative to this file
  default_output_dir = os.path.join(DIR, OUTPUT)
  parser.add_argument('--output-dir',
                      type=str,
                      default=default_output_dir,
                      help="directory for the output (default: " +
                      default_output_dir + ")")

  default_therm_input = os.path.join(default_submodules_dir,
                                     "SOURCE-C3Mech.THERM")
  parser.add_argument('--thermfile',
                      type=str,
                      default=default_therm_input,
                      help="thermochemistry data file (default: " +
                      default_therm_input + ")")

  default_trans_input = os.path.join(default_submodules_dir,
                                     "SOURCE-C3Mech.TRAN")
  parser.add_argument('--transfile',
                      type=str,
                      default=default_trans_input,
                      help="transport data file (default: " +
                      default_trans_input + ")")
  default_model_version = current_configuration.model.version
  parser.add_argument('--model-version',
                      type=str,
                      default=default_model_version,
                      help="model version (default: " + default_model_version +
                      ")")
  parser.add_argument('--header',
                      type=str,
                      default=None,
                      help=("custom header file (default: render the current "
                            "C3Mech configuration)"))

  default_model_name = current_configuration.model.name
  parser.add_argument('--model-name',
                      type=str,
                      default=default_model_name,
                      help="Model name to use in output files (default: " +
                      default_model_name + ")")
  parser.set_defaults(process_cantera=True)
  parser.set_defaults(mid_cantera=True)

  parser.add_argument('--version',
                      action='version',
                      version=f'%(prog)s {__version__}')

  args = parser.parse_args()

  if args.mid and args.generate_all:
    raise c3mech.UserInputError(
        "--mid cannot be combined with --generate-all")

  raw_model_version = args.model_version.strip()
  normalized_model_version = raw_model_version[1:] if raw_model_version.lower(
  ).startswith("v") else raw_model_version
  if normalized_model_version == "":
    raise c3mech.UserInputError(
        "invalid --model-version: empty after normalization")
  if normalized_model_version != raw_model_version:
    print("#warning: normalizing model version '" + raw_model_version +
          "' to '" + normalized_model_version + "'")
  args.model_version = normalized_model_version

  # Validate version semantics early so invalid versions do not fail later
  # with unrelated file-path errors.
  c3mech.MID(c3mech.ORDERED_KEYS, c3mech.BINARY_KEYS, args.model_version)

  therm_was_explicitly_set = any(
      (arg == "--thermfile" or arg.startswith("--thermfile="))
      for arg in sys.argv[1:])
  trans_was_explicitly_set = any(
      (arg == "--transfile" or arg.startswith("--transfile="))
      for arg in sys.argv[1:])

  if not os.path.isabs(args.submodules_dir):
    args.submodules_dir = os.path.abspath(args.submodules_dir)
  args.submodules_dir = os.path.normpath(args.submodules_dir)

  # Relative THERM/TRAN paths are always interpreted relative to the selected
  # sub-modules directory to avoid inconsistent file mixes.
  if therm_was_explicitly_set:
    if not os.path.isabs(args.thermfile):
      args.thermfile = os.path.join(args.submodules_dir, args.thermfile)
  else:
    args.thermfile = os.path.join(args.submodules_dir, "SOURCE-C3Mech.THERM")
  if trans_was_explicitly_set:
    if not os.path.isabs(args.transfile):
      args.transfile = os.path.join(args.submodules_dir, args.transfile)
  else:
    args.transfile = os.path.join(args.submodules_dir, "SOURCE-C3Mech.TRAN")

  therm_dir = os.path.normpath(os.path.dirname(os.path.abspath(args.thermfile)))
  trans_dir = os.path.normpath(os.path.dirname(os.path.abspath(args.transfile)))
  if therm_dir != args.submodules_dir:
    print("#warning: --thermfile directory differs from --submodules-dir")
  if trans_dir != args.submodules_dir:
    print("#warning: --transfile directory differs from --submodules-dir")

  if args.model_version != default_model_version:
    if args.model_name == default_model_name:
      new_default = 'C3MechV' + args.model_version 
      print("#warning: overriding default model name '" + default_model_name + "' by " + new_default)
      args.model_name = new_default

  if args.max_threads < 1:
    raise c3mech.UserInputError("--max-threads must be >= 1")
  if args.max_c is not None and args.max_c < 0:
    raise c3mech.UserInputError("--max-c must be >= 0")

  # Determine whether a YAML file will be used for this run
  needs_yaml = (args.mid == "" and not args.generate_all)

  paths = []
  if needs_yaml:
    paths.append(("yaml_file_path", True))
  paths += [("submodules_dir", False), ("thermfile", True),
            ("transfile", True), ("output_dir", False)]
  if args.header is not None:
    paths.append(("header", True))

  for attr, is_file in paths:
    path = getattr(args, attr)
    if not os.path.isabs(path):
      path = os.path.abspath(path)
      setattr(args, attr, path)
    if is_file:
      if not os.path.isfile(path):
        raise FileNotFoundError(f"File does not exist: {path}")
    else:
      if not os.path.isdir(path):
        if attr == "output_dir":
          raise FileNotFoundError(
              f"Output directory does not exist: {path}. "
              "Please create it first. This script does not create output root directories."
          )
        raise FileNotFoundError(f"Directory does not exist: {path}")

  if args.process_cantera and shutil.which("ck2yaml") is None:
    raise c3mech.UserInputError(
        "Cantera processing was requested but ck2yaml was not found in PATH. "
        "install ck2yaml or use --no-process-cantera")

  options = Options(generate_all=args.generate_all,
                 max_c=args.max_c,
                 prune=args.prune,
                 reorder=args.reorder == "true",
                 process_cantera=args.process_cantera,
                 max_threads=args.max_threads,
                 model_name=args.model_name,
                 yaml_file_path=args.yaml_file_path,
                 submodules_dir=args.submodules_dir,
                 mid=args.mid,
                 mid_cantera=args.mid_cantera,
                 thermfile=args.thermfile,
                 transfile=args.transfile,
                 header=args.header,
                 version=args.model_version,
                 output_dir=args.output_dir,
                 require_ht_subset_no_change=args.require_ht_subset_no_change,
                 selected_submodules=None,
                 c3mech_configuration=current_configuration)
  return options


def _prepare_header(options):
  header_path = getattr(options, "header", None)
  header_text = getattr(options, "header_text", None)
  if not hasattr(options, "header_text"):
    options.header_text = None
  if header_path is not None and header_text is not None:
    raise c3mech.UserInputError(
        "header and header_text cannot both be supplied")
  _require_model_name(getattr(options, "model_name", None))
  if header_text is not None and not isinstance(header_text, str):
    raise c3mech.UserInputError("header_text must be a string")
  if header_path is not None:
    try:
      header_text_to_validate = Path(header_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
      raise c3mech.UserInputError(
          "could not read header file " + str(header_path) + ": " +
          str(error)) from error
    header_text_to_validate = _require_ascii_header(
        header_text_to_validate, "header file " + str(header_path))
    if not header_text_to_validate.strip():
      raise c3mech.UserInputError(
          "header file must not be empty: " + str(header_path))
    options.header_text = header_text_to_validate
    options.header = None
  elif header_text is not None:
    options.header_text = _require_ascii_header(header_text, "header_text")
    if not header_text.strip():
      raise c3mech.UserInputError("header_text must not be empty")
  if header_path is not None or header_text is not None:
    if getattr(options, "c3mech_configuration", None) is None:
      try:
        options.c3mech_configuration = c3mech.load_c3mech_configuration(
            c3mech.CURRENT_CONFIGURATION_PATH)
      except c3mech.C3MechConfigurationError as error:
        raise c3mech.UserInputError(str(error)) from error
    return

  configuration = getattr(options, "c3mech_configuration", None)
  if configuration is None:
    raise c3mech.UserInputError(
        "a header file, header text, or C3Mech configuration is required")
  try:
    if (options.model_name == configuration.model.name and
        options.version == configuration.model.version):
      options.header_text = c3mech_header.render_c3mech_header(configuration)
    else:
      options.header_text = c3mech_header.render_minimal_c3mech_header(
          options.model_name, options.version)
  except c3mech_header.C3MechHeaderError as error:
    raise c3mech.UserInputError(str(error)) from error


def _require_printable_ascii_value(value, source):
  """Require one nonempty value containing only printable ASCII characters."""
  if not isinstance(value, str):
    raise c3mech.UserInputError(source + " must be a string")
  if not value:
    raise c3mech.UserInputError(source + " must not be empty")
  invalid = next(
      (character for character in value
       if not character.isascii() or not character.isprintable()), None)
  if invalid is not None:
    raise c3mech.UserInputError(
        source + " contains unsupported character " + repr(invalid))


def _require_model_name(model_name):
  """Require one model name that is safe as a filename prefix."""
  _require_printable_ascii_value(model_name, "model_name")
  if _MODEL_NAME_PATTERN.fullmatch(model_name) is None:
    raise c3mech.UserInputError(
        "model_name must begin with an ASCII letter or digit and contain "
        "only ASCII letters, digits, periods, underscores, plus signs, or "
        "hyphens")


def _require_ascii_header(header_text, source):
  """Require printable ASCII header text with CR or LF line endings."""
  normalized_header_text = header_text.replace("\r\n", "\n").replace(
      "\r", "\n")
  for line_number, line in enumerate(
      normalized_header_text.split("\n"), start=1):
    invalid = next(
        (character for character in line
         if not character.isascii() or not character.isprintable()), None)
    if invalid is not None:
      raise c3mech.UserInputError(
          source + " contains unsupported character " + repr(invalid) +
          " on line " + str(line_number))
  return normalized_header_text


def run_compiler(options):
  """Compile a YAML or MID selection, or every permitted selection."""
  if options.mid and options.generate_all:
    raise c3mech.UserInputError(
        "mid cannot be combined with generate_all")
  if options.selected_submodules is not None and not options.generate_all:
    raise c3mech.UserInputError(
        "selected_submodules requires generate_all")
  if options.max_threads < 1:
    raise c3mech.UserInputError("max_threads must be at least 1")
  if options.max_c is not None and options.max_c < 0:
    raise c3mech.UserInputError("max_c must be at least 0")
  _prepare_header(options)
  if options.process_cantera and shutil.which("ck2yaml") is None:
    raise c3mech.UserInputError(
        "Cantera processing was requested but ck2yaml was not found in PATH. "
        "install ck2yaml or disable Cantera processing")
  if options.generate_all:
    try:
      distribution.require_empty_output_root(options.output_dir)
    except ValueError as exc:
      raise c3mech.UserInputError(str(exc)) from exc
  # debug
  print("[chemmodkit] Running with options: " + _format_options(options))
  if options.mid == "" and options.generate_all:
    submodules_filenames, grouped_combos = c3mech.generate_submodels(options)
  else:
    if options.mid != "":
      if default_yaml_file_path != options.yaml_file_path:
        print("#warning: MID '" + options.mid +
              "' overrides yaml input from '" + options.yaml_file_path + "'")
      grouped_combos = c3mech.get_grouped_combos_mid(options)
    else:
      grouped_combos = c3mech.get_grouped_combos(options)

    submodules_filenames = c3mech.get_submodule_filenames(
        options.submodules_dir)

  if __package__:
    from .chemmodkit.output import run
  else:
    from chemmodkit.output import run

  included_keys = options.selected_submodules
  if included_keys is None:
    included_keys = tuple(
        key for key in c3mech.MID(c3mech.ORDERED_KEYS, c3mech.BINARY_KEYS,
                   version=options.version)._keys
        if key in c3mech.get_repository_submodules())
  run(options, submodules_filenames, grouped_combos, c3mech.columns,
      c3mech.carbon_map, included_keys, c3mech.submodule_labels)


def main():
  try:
    options = parse_args()
  except (FileNotFoundError, c3mech.UserInputError) as exc:
    print("#error:", exc)
    sys.exit(1)
  try:
    run_compiler(options)
  except (c3mech.UserInputError, ExternalToolError) as exc:
    print("#error:", exc)
    sys.exit(1)


if __name__ == "__main__":
  main()
