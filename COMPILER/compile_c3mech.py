#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import shutil

import c3mech_data as c3mech
from chemmodkit import __version__

DIR = os.path.dirname(os.path.abspath(__file__))
HEADER = "C3MechV4.0.1_header.txt"
YAML = "submodules.yaml"
OUTPUT = "output"
default_yaml_file_path = os.path.join(DIR, YAML)


class Options:

  def __init__(self, generate_all, max_c, prune, process_cantera, max_threads,
               model_name, yaml_file_path, submodules_dir, mid, mid_cantera,
               thermfile, transfile, header, output_dir,
               require_ht_subset_no_change):
    self.generate_all = generate_all
    self.max_c = max_c
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
    self.output_dir = output_dir
    self.require_ht_subset_no_change = require_ht_subset_no_change

  def __repr__(self):
    return ("Options(\n"
            f"  generate_all={self.generate_all},\n"
            f"  max_c={self.max_c},\n"
            f"  prune={self.prune},\n"
            f"  process_cantera={self.process_cantera},\n"
            f"  model_name='{self.model_name}',\n"
            f"  yaml_file_path='{self.yaml_file_path}',\n"
            f"  submodules_dir='{self.submodules_dir}',\n"
            f"  mid='{self.mid}',\n"
            f"  mid_cantera='{self.mid_cantera}',\n"
            f"  thermfile='{self.thermfile}',\n"
            f"  transfile='{self.transfile}',\n"
            f"  header='{self.header}',\n"
            f"  output_dir='{self.output_dir}',\n"
            f"  require_ht_subset_no_change={self.require_ht_subset_no_change}\n"
            ")")


def parse_args():
  parser = argparse.ArgumentParser(
      description="chemmodkit: Modular chemical kinetic model builder")
  parser.add_argument('--generate-all',
                      action='store_true',
                      help='Generate all model combinations (default: False)')
  parser.add_argument('--max-c',
                      type=int,
                      default=100,
                      help='Maximum carbon count for models (default: 100)')
  parser.add_argument(
      '--max-threads',
      type=int,
      default=8,
      help='Maximum number of threads for Cantera execution (default: 8)')
  parser.add_argument('--prune',
                      dest='prune',
                      action='store_true',
                      help='Enable pruning of the model (default: True)')
  parser.add_argument('--no-prune',
                      dest='prune',
                      action='store_false',
                      help='Disable pruning of the model')
  parser.set_defaults(prune=True)

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
  default_model_name = 'C3MechV' + c3mech.VERSION
  parser.add_argument('--model-name',
                      type=str,
                      default=default_model_name,
                      help="Model name to use in output files (default: " +
                      default_model_name + ")")
  parser.add_argument(
      '--mid',
      type=str,
      default="",
      help="model ID (MID) that is used to generate a sub-model")
  parser.add_argument(
      '--mid-cantera',
      dest='mid_cantera',
      action='store_true',
      help=
      "Cantera-compatible sub-modules are used (default: True, only relevant when decoding an MID)"
  )
  parser.add_argument(
      '--no-mid-cantera',
      dest='mid_cantera',
      action='store_false',
      help=
      "Cantera-compatible sub-modules are not used (only relevant when decoding an MID)"
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

  default_header_input = os.path.join(DIR, HEADER)
  parser.add_argument('--header',
                      type=str,
                      default=default_header_input,
                      help="header file (default: " + default_header_input +
                      ")")

  parser.set_defaults(process_cantera=True)
  parser.set_defaults(mid_cantera=True)

  parser.add_argument('--version',
                      action='version',
                      version=f'%(prog)s {__version__}')

  args = parser.parse_args()

  if args.max_threads < 1:
    raise ValueError("--max-threads must be >= 1")
  if args.max_c < 0:
    raise ValueError("--max-c must be >= 0")

  # Determine whether a YAML file will be used for this run
  needs_yaml = (args.mid == "" and not args.generate_all)

  paths = []
  if needs_yaml:
    paths.append(("yaml_file_path", True))
  paths += [("submodules_dir", False), ("thermfile", True),
            ("transfile", True), ("header", True), ("output_dir", False)]

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
              "Please create it first; this script does not create output root directories."
          )
        raise FileNotFoundError(f"Directory does not exist: {path}")

  if args.process_cantera and shutil.which("ck2yaml") is None:
    print(
        "\n\n\n\n#warning: ck2yaml is not installed or not found in your PATH. Setting the \"process-cantera\" option to False.\n\n\n\n"
    )
    args.process_cantera = False

  return Options(generate_all=args.generate_all,
                 max_c=args.max_c,
                 prune=args.prune,
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
                 output_dir=args.output_dir,
                 require_ht_subset_no_change=args.require_ht_subset_no_change)


def main():
  try:
    options = parse_args()
  except (FileNotFoundError, ValueError) as exc:
    print("#error:", exc)
    sys.exit(1)
  # debug
  print(f"[chemmodkit] Running with options: {options}")
  if options.mid == "" and options.generate_all:
    submodules_filenames, grouped_combos = c3mech.generate_submodels(options)
  else:
    if options.mid != "":
      if options.generate_all:
        print("#warning: MID overrides \"--generate-all\"")
        options.generate_all = False
      if default_yaml_file_path != options.yaml_file_path:
        print("#warning: MID '" + options.mid +
              "' overrides yaml input from '" + options.yaml_file_path + "'")
      grouped_combos = c3mech.get_grouped_combos_mid(options)
    else:
      grouped_combos = c3mech.get_grouped_combos(options)

    submodules_filenames = c3mech.get_submodule_filenames(
        options.submodules_dir)

  try:
    from chemmodkit.output import run
  except ImportError as exc:
    if getattr(exc, "name",
               None) in ("chemmodkit", "chemmodkit.output"):
      print("ERROR: Could not import chemmodkit.output.run.")
      print("Original error:", exc)
      sys.exit(1)
    raise

  run(options, submodules_filenames, grouped_combos, c3mech.columns)


if __name__ == "__main__":
  main()
