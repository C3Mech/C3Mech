import os
import re
import sys
from dataclasses import dataclass
import hashlib
from itertools import combinations
from collections import defaultdict
from pathlib import Path
import string
from types import MappingProxyType
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import unicodedata
from urllib.parse import urlparse

CURRENT_CONFIGURATION_PATH = Path(__file__).with_name("c3mech.yaml")

DMC_EC_FEW = True
# Default to LOWMX/LOWSP submodules for native LMRR output.
# The historical CANTERA_MODE flag selects source formulation, not solver support.
CANTERA_MODE = False

TOOL_COMPATIBLE_SUBMODULE_BASENAMES = {
    "C0": {
        "chemkin_pro": "UOG_C0_LT-HT.MECH",
        "cantera": "UOG_C0_LT-HT_IC.MECH",
    },
    "C1-C2": {
        "chemkin_pro": "UOG_C1-C2_LT-HT.MECH",
        "cantera": "UOG_C1-C2_LT-HT_IC.MECH",
    },
    "UOG_N": {
        "chemkin_pro": "UOG_N_LT-HT.MECH",
        "cantera": "UOG_N_LT-HT_IC.MECH",
    },
}

# Directory, relative to SUBMODULES, holding the IC and LOWMX/LOWSP source pair.
# Historical compatibility keys are retained for callers. UOG_N carries the
# ammonia model of Girhe et al. (2026).
TOOL_COMPATIBLE_SUBMODULE_DIRS = {
    "C0": ("UOG", "LT-HT"),
    "C1-C2": ("UOG", "LT-HT"),
    "UOG_N": ("ITV_UOG",),
}


def tool_compatible_submodule_path(key, compatibility):
  """Return an IC or LOWMX/LOWSP source path, relative to SUBMODULES."""
  return os.path.join(*TOOL_COMPATIBLE_SUBMODULE_DIRS[key],
                      TOOL_COMPATIBLE_SUBMODULE_BASENAMES[key][compatibility])


def tool_compatible_submodule_label(key, compatibility):
  """Return the same relative path with forward slashes, for messages."""
  return "/".join(TOOL_COMPATIBLE_SUBMODULE_DIRS[key] +
                  (TOOL_COMPATIBLE_SUBMODULE_BASENAMES[key][compatibility],))


def _recognized_tool_compatible_submodule_basenames(basename):
  normalized_basename = os.path.normcase(basename)
  for submodule_basenames in TOOL_COMPATIBLE_SUBMODULE_BASENAMES.values():
    if normalized_basename in {
        os.path.normcase(value) for value in submodule_basenames.values()
    }:
      return submodule_basenames
  return None


def normalize_submodule_filename_for_tool_independent_key(filename):
  """Return a submodule filename normalized for a tool-independent key.

  For a recognized pair, the IC and LOWMX/LOWSP submodule filenames are
  represented by the unsuffixed filename. The directory is preserved.
  Other filenames remain unchanged. Unknown IC names and obsolete
  ``_Cantera`` source names are rejected.
  """
  directory, basename = os.path.split(filename)
  submodule_basenames = _recognized_tool_compatible_submodule_basenames(
      basename)
  if submodule_basenames is not None:
    return os.path.join(directory, submodule_basenames["chemkin_pro"])
  if "_ic" in basename.casefold() or "_cantera" in basename.casefold():
    raise UserInputError(
        "unknown IC submodule filename: '" + filename + "'")
  return filename


def select_tool_compatible_submodule_filename(filename, cantera):
  """Return the requested filename from a recognized submodule pair.

  The historical cantera argument selects IC when true and LOWMX/LOWSP
  when false. Other filenames remain unchanged. Unknown IC names and
  obsolete ``_Cantera`` source names are rejected. The caller checks files.
  """
  directory, basename = os.path.split(filename)
  submodule_basenames = _recognized_tool_compatible_submodule_basenames(
      basename)
  if submodule_basenames is not None:
    compatibility = "cantera" if cantera else "chemkin_pro"
    return os.path.join(directory, submodule_basenames[compatibility])
  if "_ic" in basename.casefold() or "_cantera" in basename.casefold():
    raise UserInputError(
        "unknown IC submodule filename: '" + filename + "'")
  return filename


def detect_cantera_mode(submodules_filenames):
  """Return whether the C0 source selects IC (historical function name)."""
  for temperature in ("LT-HT", "HT"):
    if (temperature in submodules_filenames and
        "C0" in submodules_filenames[temperature]):
      core_path = submodules_filenames[temperature]["C0"]
      core_basename = os.path.basename(core_path)
      c0_basenames = TOOL_COMPATIBLE_SUBMODULE_BASENAMES["C0"]
      if core_basename.casefold() == c0_basenames["cantera"].casefold():
        return True
      if core_basename.casefold() == c0_basenames["chemkin_pro"].casefold():
        return False
      raise UserInputError(
          "unknown C0 submodule filename: '" + core_path + "'")
  raise UserInputError("C0 submodule filename is unavailable")

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
    "UOG_MTBE": set(["C0", "C1-C2", "C3-C4"]),
    "LLNL_BLOCK_LARGE_METHYL_ESTERS": set(["C0", "C1-C2", "C3-C4", "C5", "C6", "C7", "LLNL_BLOCK"]),
    "OMEs": set(["C0", "C1-C2"]),
}


def init_identifier_max(dependencies):
  return tuple(dependencies.keys())


# If a key was binary (or ternary), keep its base fixed forever.
ORDERED_KEYS = init_identifier_max(DEPENDENCIES)
CODING_KEYS_V4_0 = (
    "C0",
    "C1-C2",
    "C3-C4",
    "C5",
    "C5cy",
    "C6",
    "C6cy",
    "C7",
    "LLNL_BLOCK",
    "LLNL_BLOCK_DMC_EC",
    "UOG_N",
    "UOG_C-N",
    "PAH_BLOCK",
)
# Preserve the full identifier coding table; only these modules ship publicly.
PUBLIC_SUBMODULE_KEYS = CODING_KEYS_V4_0

BINARY_KEYS_V4_0: frozenset = frozenset(
    {"C0", "C1-C2", "LLNL_BLOCK_DMC_EC", "UOG_N", "PAH_BLOCK"})
CODING_KEYS_V4_1_0 = CODING_KEYS_V4_0 + (
    "UOG_MTBE",
    "LLNL_BLOCK_LARGE_METHYL_ESTERS",
    "OMEs",
)
BINARY_KEYS_V4_1_0: frozenset = BINARY_KEYS_V4_0 | frozenset(
    {"UOG_MTBE", "LLNL_BLOCK_LARGE_METHYL_ESTERS", "OMEs"})
# Submodules added after V4.0.1 are encoded above the complete V4.0.1 MID
# space. Keep the V4.0.1 keys and their order unchanged.

BINARY_KEYS: frozenset = BINARY_KEYS_V4_1_0
#BINARY_KEYS = {'LLNL_BLOCK_DMC_EC', 'C1-C2', 'PAH_BLOCK', 'C0', 'UOG_N', 'UOG_MTBE'}

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
CARBON_BLOCK_NAMES = {
    0: "C0",
    2: "C1-C2",
    4: "C3-C4",
    5: "C5",
    6: "C6",
    7: "C7",
    8: "C8+",
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
    ('PAH_BLOCK', 'PAH'),
    ('UOG_MTBE', 'MTBE'),
    ('LLNL_BLOCK_LARGE_METHYL_ESTERS', 'LME'),
    ('OMEs', 'OME'),
]

key_to_display = dict(columns)
submodule_labels = dict(key_to_display)
submodule_labels["UOG_C-N"] = "C-N"
cyclic_keys = ['C5cy', 'C6cy']


class UserInputError(ValueError):
  """Fatal input-validation error caused by user-provided options/files."""
  pass


class C3MechConfigurationError(ValueError):
  """Fatal error locating, reading, or validating a C3Mech configuration."""
  pass


@dataclass(frozen=True)
class C3MechModel:
  """Derived model identity and the configured model header title.

  The name is derived from ``version``. Schema version 5 also derives the
  species dictionary title. Schema versions 3 and 4 retain their configured
  title. ``header_title`` is ``None`` when the header uses the model name
  alone.
  """
  name: str
  version: str
  species_dictionary_title: str
  header_title: Optional[str]


@dataclass(frozen=True)
class C3MechProject:
  """Consortium name and abbreviation, source repository URL, and
  information URL.
  """
  consortium_name: str
  consortium_abbreviation: str
  source_repository_url: str
  information_url: str


@dataclass(frozen=True)
class C3MechAffiliation:
  """One affiliated organization and its ordered address lines."""
  organization: str
  address_lines: Tuple[str, ...]


@dataclass(frozen=True)
class C3MechAuthor:
  """One model author with ordered affiliation references.

  ``email`` is ``None`` when no email address is configured. Contact authors
  are selected separately by ``contact_author_ids``. Every selected contact
  must have an email address.
  """
  identifier: str
  name: str
  affiliation_ids: Tuple[str, ...]
  email: Optional[str]


@dataclass(frozen=True)
class C3MechPublicationAuthor:
  """One publication author with explicit output forms.

  ``given_names`` and ``family_names`` are written to Citation File
  Format output. ``citation_name`` is the exact abbreviated name used in
  chemical kinetic model headers and distribution citation guidance.
  """
  given_names: str
  family_names: str
  citation_name: str


@dataclass(frozen=True)
class C3MechPublication:
  """One publication in the accumulated C3Mech citation catalog.

  ``publication_type`` is ``article`` or ``unpublished``. Published articles
  require complete journal metadata. The corresponding fields are ``None``
  for unpublished work.
  ``cff_title`` is ``None`` when Citation File Format output uses ``title``.
  ``issue`` is ``None`` for journals without an issue number. Exactly one of
  ``article_number`` or the ``start_page``/``end_page`` pair identifies an
  article's location in its volume.
  ``url`` is the publication page written to Citation File Format output.
  """
  identifier: str
  publication_type: str
  authors: Tuple[C3MechPublicationAuthor, ...]
  year: Optional[int]
  title: str
  cff_title: Optional[str]
  journal: Optional[str]
  volume: Optional[str]
  issue: Optional[str]
  article_number: Optional[str]
  start_page: Optional[str]
  end_page: Optional[str]
  doi: Optional[str]
  url: Optional[str]


@dataclass(frozen=True)
class C3MechMajorCitationVersion:
  """Ordered publications and corrigenda for one model family."""
  preferred_publication_id: str
  publication_ids: Tuple[str, ...]
  corrigendum_ids: Tuple[str, ...]


@dataclass(frozen=True)
class C3MechMinorCitationVersion:
  """Ordered update publications for one nonzero minor version."""
  publication_ids: Tuple[str, ...]


@dataclass(frozen=True)
class C3MechCitationCatalog:
  """Accumulated publications and version-specific citation selections.

  Mapping order has no presentation significance. Publication identifier
  lists retain YAML order within each role. The current minor-version
  update precedes model-family publications and their corrigenda.
  """
  cff_title: str
  major_versions: Mapping[str, C3MechMajorCitationVersion]
  minor_versions: Mapping[str, C3MechMinorCitationVersion]
  publications: Mapping[str, C3MechPublication]


@dataclass(frozen=True)
class C3MechCitation:
  """One publication selected for the current model header.

  ``role`` is one value from ``HEADER_CITATION_ROLE_ORDER``.
  """
  identifier: str
  role: str
  publication_type: str
  authors: Tuple[C3MechPublicationAuthor, ...]
  year: Optional[int]
  title: str
  cff_title: Optional[str]
  journal: Optional[str]
  volume: Optional[str]
  issue: Optional[str]
  article_number: Optional[str]
  start_page: Optional[str]
  end_page: Optional[str]
  doi: Optional[str]
  url: Optional[str]


@dataclass(frozen=True)
class C3MechConfiguration:
  """Validated content of exactly one selected YAML file.

  Authors and their affiliation references retain YAML order. The affiliation
  mapping retains YAML insertion order, but consumers must not use that order
  to arrange generated content. ``contact_author_ids`` retains YAML order,
  which controls the order of contacts in generated content. ``citation``
  retains the complete publication catalog. ``header_citations`` contains
  only the model family publications, applicable corrigenda, and publications
  for the selected nonzero minor version.

  For a normal file load, ``source_path`` is the resolved path of the selected
  file. For a captured snapshot, it is the normalized absolute path supplied
  by the caller that protected the file read. ``source_bytes`` contains the
  exact bytes read by the file loader or supplied by that snapshot caller.
  ``sha256`` is
  ``hashlib.sha256(source_bytes).hexdigest()``.
  """
  schema_version: int
  model: C3MechModel
  project: C3MechProject
  affiliations: Mapping[str, C3MechAffiliation]
  authors: Tuple[C3MechAuthor, ...]
  contact_author_ids: Tuple[str, ...]
  citation: C3MechCitationCatalog
  header_citations: Tuple[C3MechCitation, ...]
  source_path: Path
  source_bytes: bytes
  sha256: str


def _construct_unique_mapping(loader, node, deep=False):
  loader.flatten_mapping(node)
  mapping = {}
  for key_node, value_node in node.value:
    key = loader.construct_object(key_node, deep=deep)
    if not isinstance(key, str):
      raise C3MechConfigurationError("YAML mapping keys must be strings")
    if key in mapping:
      raise C3MechConfigurationError("duplicate YAML key: " + key)
    mapping[key] = loader.construct_object(value_node, deep=deep)
  return mapping


_CONFIGURATION_FIELDS = {
    "schema_version",
    "model",
    "project",
    "affiliations",
    "authors",
    "contact_author_ids",
    "citation",
}
_LEGACY_MODEL_FIELDS = {
    "name", "version", "species_dictionary_title", "header_title"
}
_MODEL_FIELDS = {"version", "header_title"}
_PROJECT_FIELDS = {
    "consortium_name",
    "consortium_abbreviation",
    "source_repository_url",
    "information_url",
}
_AFFILIATION_FIELDS = {"organization", "address_lines"}
_AUTHOR_FIELDS = {"id", "name", "affiliation_ids", "email"}
_ARTICLE_CITATION_FIELDS = {
    "authors",
    "year",
    "title",
    "cff_title",
    "journal",
    "volume",
    "article_number",
    "doi",
    "url",
}
_ARTICLE_CITATION_FIELDS_V4 = _ARTICLE_CITATION_FIELDS | {
    "issue", "start_page", "end_page"
}
_UNPUBLISHED_CITATION_FIELDS = {"type", "authors", "title"}
_CITATION_AUTHOR_FIELDS = {"given_names", "family_names", "citation_name"}
_CITATION_CATALOG_FIELDS = {
    "cff_title", "major_versions", "minor_versions", "publications"
}
_MAJOR_CITATION_VERSION_FIELDS = {
    "preferred_publication_id", "publication_ids", "corrigendum_ids"
}
_MINOR_CITATION_VERSION_FIELDS = {"publication_ids"}
_IDENTIFIER_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_DOI_PATTERN = re.compile(r"^10\.[0-9]{4,9}/\S+$")
_MODEL_VERSION_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
_MAJOR_VERSION_PATTERN = re.compile(r"^[0-9]+$")
_MINOR_VERSION_PATTERN = re.compile(r"^[0-9]+\.[1-9][0-9]*$")
HEADER_CITATION_ROLE_ORDER = (
    "minor_version_publication",
    "major_version_publication",
    "corrigendum",
)


def _configuration_mapping(value, name, fields):
  """Require a YAML mapping with exactly the specified fields.

  For example, ``{"name": "C3Mech"}`` is valid when ``fields`` contains only
  ``"name"``. A missing ``name`` field or an additional field is fatal.
  """
  if not isinstance(value, dict):
    raise C3MechConfigurationError(name + " must be a mapping")
  missing = sorted(fields - set(value))
  unknown = sorted(set(value) - fields)
  if missing:
    raise C3MechConfigurationError(
        name + " is missing fields: " + ", ".join(missing))
  if unknown:
    raise C3MechConfigurationError(
        name + " contains unknown fields: " + ", ".join(unknown))
  return value


def _configuration_list(value, name, allow_empty=False):
  """Require a YAML list, which is nonempty unless explicitly permitted.

  For example, ``["first", "second"]`` is valid. A scalar such as ``"first"``
  is not a list.
  """
  if not isinstance(value, list):
    raise C3MechConfigurationError(name + " must be a list")
  if not allow_empty and not value:
    raise C3MechConfigurationError(name + " must not be empty")
  return value


def _configuration_mapping_collection(value, name, allow_empty=False):
  """Require a YAML mapping used as an identifier-addressed collection."""
  if not isinstance(value, dict):
    raise C3MechConfigurationError(name + " must be a mapping")
  if not allow_empty and not value:
    raise C3MechConfigurationError(name + " must not be empty")
  return value


def _configuration_string(value, name):
  """Require one nonempty string without surrounding whitespace.

  Unicode control, format, surrogate, private use, unassigned, line separator,
  and paragraph separator characters are rejected. For example,
  ``"C3MechV4.1.0"`` is valid, while ``" C3MechV4.1.0"`` is not.
  """
  if not isinstance(value, str) or not value.strip():
    raise C3MechConfigurationError(name + " must be a nonempty string")
  if value != value.strip():
    raise C3MechConfigurationError(
        name + " must not have leading or trailing whitespace")
  if any(unicodedata.category(character)[0] == "C" or
         unicodedata.category(character) in {"Zl", "Zp"}
         for character in value):
    raise C3MechConfigurationError(
        name + " contains a nonprinting character")
  return value


def _configuration_identifier(value, name):
  """Require an identifier that starts with a letter from ``a`` through ``z``.

  Remaining characters may be letters from ``a`` through ``z``, digits, or
  underscores. For example, ``"raymond_langer"`` is valid and ``"1raymond"``
  is not.
  """
  value = _configuration_string(value, name)
  if _IDENTIFIER_PATTERN.fullmatch(value) is None:
    raise C3MechConfigurationError(
        name + " must start with a lowercase letter and otherwise use only "
        "lowercase letters, digits, and underscores")
  return value


def _configuration_strings(value, name):
  """Require a nonempty YAML list of strings and return it as a tuple.

  For example, ``["first", "second"]`` becomes ``("first", "second")``.
  Every list item is checked by ``_configuration_string``.
  """
  values = _configuration_list(value, name)
  return tuple(
      _configuration_string(item, name + "[" + str(index) + "]")
      for index, item in enumerate(values))


def _configuration_https_url(value, name):
  """Require an absolute ASCII HTTPS URL.

  Each hostname label may contain only ASCII letters, digits, or hyphens. A
  label cannot be empty, start or end with a hyphen, or exceed 63 characters.
  Credentials, parameters, queries, and fragments are rejected. For example,
  ``"https://github.com/C3Mech/C3Mech"`` is valid.
  """
  value = _configuration_string(value, name)
  if (not value.isascii() or "\\" in value or
      any(character.isspace() or ord(character) == 127
          for character in value) or
      re.search(r"%(?![0-9A-Fa-f]{2})", value)):
    raise C3MechConfigurationError(name + " must be a valid HTTPS URL")
  try:
    parsed = urlparse(value)
    hostname = parsed.hostname
    parsed.port
  except ValueError as error:
    raise C3MechConfigurationError(name + " must be a valid HTTPS URL") \
        from error
  valid_hostname = bool(hostname and all(
      label and len(label) <= 63 and not label.startswith("-") and
      not label.endswith("-") and
      re.fullmatch(r"[A-Za-z0-9-]+", label)
      for label in hostname.split(".")))
  if (parsed.scheme != "https" or not parsed.netloc or parsed.username or
      parsed.password or parsed.params or parsed.query or parsed.fragment or
      parsed.netloc.endswith(":") or not valid_hostname):
    raise C3MechConfigurationError(
        name + " must be an absolute HTTPS URL without credentials, "
        "parameters, query, or fragment")
  return value


def _load_model(data, schema_version):
  fields = _LEGACY_MODEL_FIELDS if schema_version < 5 else _MODEL_FIELDS
  model = _configuration_mapping(data, "model", fields)
  version = _configuration_string(model["version"], "model.version")
  if _MODEL_VERSION_PATTERN.fullmatch(version) is None:
    raise C3MechConfigurationError(
        "model.version must contain three dot-separated integers")
  name = "C3MechV" + version
  species_dictionary_title = name + " species dictionary"
  if schema_version < 5:
    configured_name = _configuration_string(model["name"], "model.name")
    if configured_name != name:
      raise C3MechConfigurationError(
          "model.name must equal C3MechV followed by model.version")
    species_dictionary_title = _configuration_string(
        model["species_dictionary_title"],
        "model.species_dictionary_title")
  header_title = model["header_title"]
  if header_title is not None:
    header_title = _configuration_string(header_title, "model.header_title")
  return C3MechModel(
      name=name,
      version=version,
      species_dictionary_title=species_dictionary_title,
      header_title=header_title)


def _load_project(data):
  project = _configuration_mapping(data, "project", _PROJECT_FIELDS)
  return C3MechProject(
      consortium_name=_configuration_string(
          project["consortium_name"], "project.consortium_name"),
      consortium_abbreviation=_configuration_string(
          project["consortium_abbreviation"],
          "project.consortium_abbreviation"),
      source_repository_url=_configuration_https_url(
          project["source_repository_url"],
          "project.source_repository_url"),
      information_url=_configuration_https_url(
          project["information_url"], "project.information_url"))


def _load_affiliations(data):
  if not isinstance(data, dict):
    raise C3MechConfigurationError("affiliations must be a mapping")
  if not data:
    raise C3MechConfigurationError("affiliations must not be empty")
  affiliations = data
  resolved = {}
  for identifier, raw_affiliation in affiliations.items():
    identifier = _configuration_identifier(
        identifier, "affiliation identifier")
    affiliation = _configuration_mapping(
        raw_affiliation, "affiliations." + identifier, _AFFILIATION_FIELDS)
    resolved[identifier] = C3MechAffiliation(
        organization=_configuration_string(
            affiliation["organization"],
            "affiliations." + identifier + ".organization"),
        address_lines=_configuration_strings(
            affiliation["address_lines"],
            "affiliations." + identifier + ".address_lines"))
  return resolved


def _load_authors(data, affiliations):
  raw_authors = _configuration_list(data, "authors")
  authors = []
  identifiers = set()
  names = set()
  referenced_affiliations = set()
  for index, raw_author in enumerate(raw_authors):
    location = "authors[" + str(index) + "]"
    author = _configuration_mapping(raw_author, location, _AUTHOR_FIELDS)
    identifier = _configuration_identifier(author["id"], location + ".id")
    if identifier in identifiers:
      raise C3MechConfigurationError("duplicate author identifier: " +
                                     identifier)
    identifiers.add(identifier)
    name = _configuration_string(author["name"], location + ".name")
    if name in names:
      raise C3MechConfigurationError("duplicate author name: " + name)
    names.add(name)
    affiliation_ids = _configuration_strings(
        author["affiliation_ids"], location + ".affiliation_ids")
    if len(affiliation_ids) != len(set(affiliation_ids)):
      raise C3MechConfigurationError(
          location + ".affiliation_ids contains duplicates")
    unknown = sorted(set(affiliation_ids) - set(affiliations))
    if unknown:
      raise C3MechConfigurationError(
          location + " references unknown affiliations: " +
          ", ".join(unknown))
    referenced_affiliations.update(affiliation_ids)
    email = author["email"]
    if email is not None:
      email = _configuration_string(email, location + ".email")
      local_part, separator, domain = email.partition("@")
      valid_domain = bool(domain and domain.isascii() and all(
          label and len(label) <= 63 and not label.startswith("-") and
          not label.endswith("-") and
          re.fullmatch(r"[A-Za-z0-9-]+", label)
          for label in domain.split(".")))
      valid_local_part = bool(
          local_part and local_part.isascii() and
          re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+", local_part) and
          not local_part.startswith(".") and not local_part.endswith(".") and
          ".." not in local_part)
      if (separator != "@" or "@" in domain or not local_part or
          not valid_local_part or not valid_domain or
          any(character.isspace() for character in email)):
        raise C3MechConfigurationError(
            location + ".email must be an email address or null")
    authors.append(C3MechAuthor(
        identifier=identifier,
        name=name,
        affiliation_ids=affiliation_ids,
        email=email))
  unreferenced = sorted(set(affiliations) - referenced_affiliations)
  if unreferenced:
    raise C3MechConfigurationError(
        "unreferenced affiliations: " + ", ".join(unreferenced))
  return tuple(authors)


def _load_contacts(data, authors):
  contacts = _configuration_strings(data, "contact_author_ids")
  if len(contacts) != len(set(contacts)):
    raise C3MechConfigurationError(
        "contact_author_ids contains duplicates")
  authors_by_id = {author.identifier: author for author in authors}
  unknown = sorted(set(contacts) - set(authors_by_id))
  if unknown:
    raise C3MechConfigurationError(
        "contact_author_ids contains unknown authors: " + ", ".join(unknown))
  missing_email = [
      identifier for identifier in contacts
      if authors_by_id[identifier].email is None
  ]
  if missing_email:
    raise C3MechConfigurationError(
        "contact authors require email addresses: " +
        ", ".join(missing_email))
  return contacts


def _load_publication_authors(data, location):
  raw_authors = _configuration_list(data, location)
  authors = []
  citation_names = set()
  for index, raw_author in enumerate(raw_authors):
    author_location = location + "[" + str(index) + "]"
    author = _configuration_mapping(
        raw_author, author_location, _CITATION_AUTHOR_FIELDS)
    citation_name = _configuration_string(
        author["citation_name"], author_location + ".citation_name")
    if citation_name in citation_names:
      raise C3MechConfigurationError(
          location + " contains duplicate citation names")
    citation_names.add(citation_name)
    authors.append(C3MechPublicationAuthor(
        given_names=_configuration_string(
            author["given_names"], author_location + ".given_names"),
        family_names=_configuration_string(
            author["family_names"], author_location + ".family_names"),
        citation_name=citation_name))
  return tuple(authors)


def _load_publications(data, schema_version):
  publications = _configuration_mapping_collection(
      data, "citation.publications")
  if not publications:
    raise C3MechConfigurationError("citation.publications must not be empty")
  resolved = {}
  for identifier, raw_publication in publications.items():
    _configuration_identifier(identifier, "citation publication identifier")
    location = "citation.publications." + identifier
    if schema_version == 3:
      publication_type = "article"
      fields = _ARTICLE_CITATION_FIELDS
    else:
      if not isinstance(raw_publication, dict):
        raise C3MechConfigurationError(location + " must be a mapping")
      publication_type = raw_publication.get("type", "article")
      publication_type = _configuration_string(
          publication_type, location + ".type")
      if publication_type == "article":
        fields = set(_ARTICLE_CITATION_FIELDS_V4)
        if "type" in raw_publication:
          fields.add("type")
      elif publication_type == "unpublished":
        fields = _UNPUBLISHED_CITATION_FIELDS
      else:
        raise C3MechConfigurationError(
            location + ".type must be article or unpublished")
    publication = _configuration_mapping(raw_publication, location, fields)
    authors = _load_publication_authors(
        publication["authors"], location + ".authors")
    title = _configuration_string(
        publication["title"], location + ".title")
    if publication_type == "unpublished":
      resolved[identifier] = C3MechPublication(
          identifier=identifier,
          publication_type=publication_type,
          authors=authors,
          year=None,
          title=title,
          cff_title=None,
          journal=None,
          volume=None,
          issue=None,
          article_number=None,
          start_page=None,
          end_page=None,
          doi=None,
          url=None)
      continue
    year = publication["year"]
    if isinstance(year, bool) or not isinstance(year, int) or year < 1:
      raise C3MechConfigurationError(
          location + ".year must be a positive integer")
    doi = _configuration_string(publication["doi"], location + ".doi")
    if _DOI_PATTERN.fullmatch(doi) is None:
      raise C3MechConfigurationError(
          location + ".doi must be a DOI without a URL prefix")
    if schema_version == 3:
      issue = None
      article_number = _configuration_string(
          publication["article_number"], location + ".article_number")
      start_page = None
      end_page = None
    else:
      issue = (None if publication["issue"] is None else
               _configuration_string(
                   publication["issue"], location + ".issue"))
      article_number = (
          None if publication["article_number"] is None else
          _configuration_string(
              publication["article_number"], location + ".article_number"))
      start_page = (
          None if publication["start_page"] is None else
          _configuration_string(
              publication["start_page"], location + ".start_page"))
      end_page = (
          None if publication["end_page"] is None else
          _configuration_string(
              publication["end_page"], location + ".end_page"))
      if (start_page is None) != (end_page is None):
        raise C3MechConfigurationError(
            location + ".start_page and .end_page must both be set or null")
      if (article_number is None) == (start_page is None):
        raise C3MechConfigurationError(
            location + " must define either article_number or a page range")
    resolved[identifier] = C3MechPublication(
        identifier=identifier,
        publication_type=publication_type,
        authors=authors,
        year=year,
        title=title,
        cff_title=(None if publication["cff_title"] is None else
                   _configuration_string(
                       publication["cff_title"], location + ".cff_title")),
        journal=_configuration_string(
            publication["journal"], location + ".journal"),
        volume=_configuration_string(
            publication["volume"], location + ".volume"),
        issue=issue,
        article_number=article_number,
        start_page=start_page,
        end_page=end_page,
        doi=doi,
        url=_configuration_https_url(publication["url"], location + ".url"))
  return resolved


def _publication_ids(value, location, publications):
  identifiers = _configuration_strings(value, location)
  if len(identifiers) != len(set(identifiers)):
    raise C3MechConfigurationError(location + " contains duplicates")
  for identifier in identifiers:
    _configuration_identifier(identifier, location)
  unknown = sorted(set(identifiers) - set(publications))
  if unknown:
    raise C3MechConfigurationError(
        location + " references unknown publications: " + ", ".join(unknown))
  return identifiers


def _load_major_citation_versions(data, publications):
  versions = _configuration_mapping_collection(
      data, "citation.major_versions", allow_empty=True)
  resolved = {}
  for version, raw_version in versions.items():
    location = "citation.major_versions." + version
    if _MAJOR_VERSION_PATTERN.fullmatch(version) is None:
      raise C3MechConfigurationError(
          location + " key must be a numeric major version")
    version_data = _configuration_mapping(
        raw_version, location, _MAJOR_CITATION_VERSION_FIELDS)
    publication_ids = _publication_ids(
        version_data["publication_ids"], location + ".publication_ids",
        publications)
    if not publication_ids:
      raise C3MechConfigurationError(
          location + ".publication_ids must not be empty")
    preferred = _configuration_identifier(
        version_data["preferred_publication_id"],
        location + ".preferred_publication_id")
    if preferred not in publication_ids:
      raise C3MechConfigurationError(
          location + ".preferred_publication_id must occur in publication_ids")
    corrigendum_ids = _publication_ids(
        version_data["corrigendum_ids"], location + ".corrigendum_ids",
        publications)
    if set(publication_ids) & set(corrigendum_ids):
      raise C3MechConfigurationError(
          location + " uses one publication as both publication and "
          "corrigendum")
    resolved[version] = C3MechMajorCitationVersion(
        preferred_publication_id=preferred,
        publication_ids=publication_ids,
        corrigendum_ids=corrigendum_ids)
  return resolved


def _load_minor_citation_versions(data, publications, major_versions):
  versions = _configuration_mapping_collection(
      data, "citation.minor_versions", allow_empty=True)
  resolved = {}
  for version, raw_version in versions.items():
    location = "citation.minor_versions." + version
    if _MINOR_VERSION_PATTERN.fullmatch(version) is None:
      raise C3MechConfigurationError(
          location + " key must be a numeric major.minor version with a "
          "nonzero minor component")
    if version.split(".")[0] not in major_versions:
      raise C3MechConfigurationError(
          location + " has no corresponding major version")
    version_data = _configuration_mapping(
        raw_version, location, _MINOR_CITATION_VERSION_FIELDS)
    publication_ids = _publication_ids(
        version_data["publication_ids"], location + ".publication_ids",
        publications)
    if not publication_ids:
      raise C3MechConfigurationError(
          location + ".publication_ids must not be empty")
    resolved[version] = C3MechMinorCitationVersion(
        publication_ids=publication_ids)
  return resolved


def _selected_citations(model, major_versions, minor_versions, publications):
  major, minor, _ = model.version.split(".")
  if major not in major_versions:
    raise C3MechConfigurationError(
        "citation.major_versions is missing model major version " + major)
  major_selection = major_versions[major]
  minor_role, major_role, corrigendum_role = HEADER_CITATION_ROLE_ORDER
  selections = [
      (major_role, major_selection.publication_ids),
      (corrigendum_role, major_selection.corrigendum_ids),
  ]
  if minor != "0":
    minor_version = major + "." + minor
    if minor_version not in minor_versions:
      raise C3MechConfigurationError(
          "citation.minor_versions is missing model minor version " +
          minor_version)
    selections.insert(0, (
        minor_role,
        minor_versions[minor_version].publication_ids))
  citations = []
  selected_ids = set()
  for role, identifiers in selections:
    for identifier in identifiers:
      if identifier in selected_ids:
        raise C3MechConfigurationError(
            "selected citation publication occurs more than once: " +
            identifier)
      selected_ids.add(identifier)
      publication = publications[identifier]
      citations.append(C3MechCitation(
          identifier=publication.identifier,
          role=role,
          publication_type=publication.publication_type,
          authors=publication.authors,
          year=publication.year,
          title=publication.title,
          cff_title=publication.cff_title,
          journal=publication.journal,
          volume=publication.volume,
          issue=publication.issue,
          article_number=publication.article_number,
          start_page=publication.start_page,
          end_page=publication.end_page,
          doi=publication.doi,
          url=publication.url))
  return tuple(citations)


def _load_citation_catalog(data, model, schema_version):
  citation = _configuration_mapping(
      data, "citation", _CITATION_CATALOG_FIELDS)
  publications = _load_publications(
      citation["publications"], schema_version)
  major_versions = _load_major_citation_versions(
      citation["major_versions"], publications)
  minor_versions = _load_minor_citation_versions(
      citation["minor_versions"], publications, major_versions)
  major_publication_ids = {
      identifier for selection in major_versions.values()
      for identifier in selection.publication_ids
  }
  corrigendum_ids = {
      identifier for selection in major_versions.values()
      for identifier in selection.corrigendum_ids
  }
  minor_publication_ids = {
      identifier for selection in minor_versions.values()
      for identifier in selection.publication_ids
  }
  overlapping_roles = sorted(
      (major_publication_ids & corrigendum_ids) |
      (major_publication_ids & minor_publication_ids) |
      (corrigendum_ids & minor_publication_ids))
  if overlapping_roles:
    raise C3MechConfigurationError(
        "citation publications have more than one role: " +
        ", ".join(overlapping_roles))
  publication_version_groups = {}
  for major, selection in major_versions.items():
    for identifier in selection.publication_ids + selection.corrigendum_ids:
      publication_version_groups.setdefault(identifier, set()).add(major)
  for minor, selection in minor_versions.items():
    for identifier in selection.publication_ids:
      publication_version_groups.setdefault(identifier, set()).add(minor)
  multiple_version_groups = sorted(
      identifier for identifier, versions in publication_version_groups.items()
      if len(versions) > 1)
  if multiple_version_groups:
    raise C3MechConfigurationError(
        "citation publications belong to more than one version group: " +
        ", ".join(multiple_version_groups))
  for major in major_versions:
    minor_numbers = sorted(
        int(version.split(".")[1]) for version in minor_versions
        if version.split(".")[0] == major)
    if minor_numbers:
      expected = list(range(1, minor_numbers[-1] + 1))
      if minor_numbers != expected:
        raise C3MechConfigurationError(
            "citation.minor_versions must contain every version from " +
            major + ".1 through " + major + "." + str(minor_numbers[-1]))
  header_citations = _selected_citations(
      model, major_versions, minor_versions, publications)
  referenced = set()
  for selection in major_versions.values():
    referenced.update(selection.publication_ids)
    referenced.update(selection.corrigendum_ids)
  for selection in minor_versions.values():
    referenced.update(selection.publication_ids)
  unreferenced = sorted(set(publications) - referenced)
  if unreferenced:
    raise C3MechConfigurationError(
        "citation contains unreferenced publications: " +
        ", ".join(unreferenced))
  catalog = C3MechCitationCatalog(
      cff_title=_configuration_string(
          citation["cff_title"], "citation.cff_title"),
      major_versions=MappingProxyType(major_versions),
      minor_versions=MappingProxyType(minor_versions),
      publications=MappingProxyType(publications))
  return catalog, header_citations


def _parse_c3mech_configuration(source_path, source_bytes):
  import yaml  # Keep unrelated c3mech_data interfaces usable without PyYAML.

  try:
    text = source_bytes.decode("utf-8")
  except UnicodeError as error:
    raise C3MechConfigurationError(
        "C3Mech configuration is not UTF-8: " + str(source_path)) from error
  try:
    class ConfigurationLoader(yaml.SafeLoader):
      pass

    ConfigurationLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        _construct_unique_mapping)
    raw = yaml.load(text, Loader=ConfigurationLoader)
  except C3MechConfigurationError as error:
    raise C3MechConfigurationError(
        "invalid C3Mech configuration in " + str(source_path) + ": " +
        str(error)) from error
  except yaml.YAMLError as error:
    raise C3MechConfigurationError(
        "invalid C3Mech YAML in " + str(source_path) + ": " +
        str(error)) from error
  try:
    root = _configuration_mapping(raw, "configuration", _CONFIGURATION_FIELDS)
    schema_version = root["schema_version"]
    if (isinstance(schema_version, bool) or
        not isinstance(schema_version, int) or
        schema_version not in {3, 4, 5}):
      raise C3MechConfigurationError(
          "schema_version must equal integer 3, 4, or 5")
    model = _load_model(root["model"], schema_version)
    affiliations = _load_affiliations(root["affiliations"])
    authors = _load_authors(root["authors"], affiliations)
    citation, header_citations = _load_citation_catalog(
        root["citation"], model, schema_version)
    return C3MechConfiguration(
        schema_version=schema_version,
        model=model,
        project=_load_project(root["project"]),
        affiliations=MappingProxyType(affiliations),
        authors=authors,
        contact_author_ids=_load_contacts(
            root["contact_author_ids"], authors),
        citation=citation,
        header_citations=header_citations,
        source_path=source_path,
        source_bytes=source_bytes,
        sha256=hashlib.sha256(source_bytes).hexdigest())
  except C3MechConfigurationError as error:
    raise C3MechConfigurationError(
        "invalid C3Mech configuration in " + str(source_path) + ": " +
        str(error)) from error


def load_c3mech_configuration(path):
  """Load and validate exactly one explicitly selected C3Mech configuration.

  The loader requires every documented field and rejects unknown fields. It
  does not search for another file, merge configurations, or provide missing
  values. ``header_title`` is the only nullable model field. Author order and
  affiliation-reference order are retained. The citation catalog accumulates
  publications across versions. Generated content selects the current major
  version publications and corrigenda, plus only the current nonzero minor
  version publications. A contact must identify an author with an email
  address.
  Configuration versions use the complete numeric
  ``MAJOR.MINOR.PATCH`` form. Compiler development labels such as ``4.X`` are
  not accepted as model versions.
  """
  if not isinstance(path, (str, os.PathLike)):
    raise C3MechConfigurationError(
        "C3Mech configuration path must be a string or path-like object")
  try:
    path_text = os.fspath(path)
  except TypeError as error:
    raise C3MechConfigurationError(
        "C3Mech configuration path-like object must resolve to text") \
        from error
  if not isinstance(path_text, str):
    raise C3MechConfigurationError(
        "C3Mech configuration path-like object must resolve to text")
  if "\0" in path_text:
    raise C3MechConfigurationError(
        "could not resolve C3Mech configuration path: " + repr(path_text))
  try:
    source_path = Path(path_text).expanduser().resolve()
  except (OSError, RuntimeError, ValueError) as error:
    raise C3MechConfigurationError(
        "could not resolve C3Mech configuration path: " + str(path)) \
        from error
  if not source_path.is_file():
    raise C3MechConfigurationError(
        "C3Mech configuration is not a regular file: " + str(source_path))
  try:
    source_bytes = source_path.read_bytes()
  except OSError as error:
    raise C3MechConfigurationError(
        "could not read C3Mech configuration: " + str(source_path)) from error
  return _parse_c3mech_configuration(source_path, source_bytes)


def load_c3mech_configuration_snapshot(source_path, source_bytes):
  """Validate captured configuration bytes from one absolute source path.

  This function does not access the path. The caller must supply a normalized
  absolute path identifying the regular file whose bytes were captured while
  protecting that read against replacement. The returned source path and
  SHA-256 digest describe the supplied bytes.
  """
  if not isinstance(source_path, (str, os.PathLike)):
    raise C3MechConfigurationError(
        "C3Mech configuration snapshot path must be a string or path-like " +
        "object")
  try:
    source_path = Path(source_path)
  except (TypeError, ValueError) as error:
    raise C3MechConfigurationError(
        "invalid C3Mech configuration snapshot path: " + str(source_path)) \
        from error
  if "\0" in str(source_path):
    raise C3MechConfigurationError(
        "C3Mech configuration snapshot path contains a null character")
  if not source_path.is_absolute():
    raise C3MechConfigurationError(
        "C3Mech configuration snapshot path must be absolute: " +
        str(source_path))
  normalized_source_path = Path(os.path.abspath(source_path))
  if source_path != normalized_source_path:
    raise C3MechConfigurationError(
        "C3Mech configuration snapshot path must be normalized: " +
        str(source_path))
  if not isinstance(source_bytes, bytes):
    raise C3MechConfigurationError(
        "C3Mech configuration snapshot content must be bytes")
  return _parse_c3mech_configuration(source_path, source_bytes)


def get_repository_submodules():
  """Return the key for every submodule in the repository.

  The keys follow ORDERED_KEYS order.
  """
  return tuple(PUBLIC_SUBMODULE_KEYS)


def validate_dependency_definitions():
  """Fail if any submodule dependency is not a known internal key."""
  for key, dependencies in DEPENDENCIES.items():
    unknown = sorted(dependencies - set(DEPENDENCIES))
    if unknown:
      raise RuntimeError(
          "Internal dependency table error: " + key +
          " references unknown " + ", ".join(unknown))


def validate_submodule_selection(version, selected_submodules):
  """Validate an explicit ordered subset of repository submodule keys."""
  validate_dependency_definitions()
  if not isinstance(selected_submodules, (list, tuple)):
    raise UserInputError("selected_submodules must be a list or tuple")
  if not all(isinstance(key, str) and key for key in selected_submodules):
    raise UserInputError("selected_submodules must contain nonempty keys")

  selected = tuple(selected_submodules)
  if not selected:
    raise UserInputError("selected_submodules must not be empty")
  if len(selected) != len(set(selected)):
    raise UserInputError("selected_submodules contains duplicate keys")
  repository_submodules = get_repository_submodules()
  unknown = sorted(set(selected) - set(repository_submodules))
  if unknown:
    raise UserInputError("unknown selected submodule keys: " +
                         ", ".join(unknown))
  expected_order = tuple(
      key for key in repository_submodules if key in set(selected))
  if selected != expected_order:
    raise UserInputError("selected_submodules must follow ORDERED_KEYS order")

  encodable = set(MID(ORDERED_KEYS, BINARY_KEYS, version=version)._keys)
  unencodable = sorted(set(selected) - encodable)
  if unencodable:
    raise UserInputError(
        "selected_submodules cannot be encoded with MID version " + version +
        ": " + ", ".join(unencodable))

  selected_set = set(selected)
  dependency_errors = []
  for key in selected:
    missing = sorted(DEPENDENCIES[key] - selected_set)
    if missing:
      dependency_errors.append(key + " requires missing " +
                               ", ".join(missing))
  if dependency_errors:
    raise UserInputError("submodule dependency violation: " +
                         " | ".join(dependency_errors))
  return selected


def print_not_found(what, dir_or_file, path):
  print(what + " " + dir_or_file + " '" + path + "' does not exist")


def get_submodules_dir(abs_dir):
  abs_dir_norm = os.path.normcase(os.path.abspath(os.path.normpath(abs_dir)))

  def looks_like_submodules_dir(path):
    return (os.path.isdir(path) and os.path.isdir(os.path.join(path, "UOG"))
            and os.path.isdir(os.path.join(path, "LLNL")))

  # Allow passing the sub-module directory directly, independent of its name.
  if looks_like_submodules_dir(abs_dir_norm):
    return abs_dir_norm

  # Fallback: infer SUBMODULES next to a compiler/scripts directory.
  return os.path.normcase(
      os.path.normpath(os.path.join(abs_dir_norm, os.path.join("..",
                                                               "SUBMODULES"))))


# Helper to get max carbon in a combination
def max_carbon(combo):
  return max([carbon_map.get(b, -1) for b in combo if b in carbon_map] + [0])


def exceeds_carbon_limit(carbon_count, maximum_carbon_count):
  """Return whether a finite carbon-count limit excludes a selection."""
  return (maximum_carbon_count is not None
          and carbon_count > maximum_carbon_count)


def get_base_modules():
  return ["C1-C2", "C3-C4", "C5", "C5cy", "C6", "C6cy", "C7"]


def get_ht_htlt_modules(abs_dir, cantera_mode=None, submodule_keys=None):
  """Return existing HT and LT-HT paths for public or selected keys."""
  if submodule_keys is None:
    submodule_keys = get_repository_submodules()
  if cantera_mode is None:
    cantera_mode = CANTERA_MODE
  elif not isinstance(cantera_mode, bool):
    raise UserInputError("cantera_mode must be Boolean or None")
  compatibility = "cantera" if cantera_mode else "chemkin_pro"
  c0_rel = tool_compatible_submodule_path("C0", compatibility)
  c12_rel = tool_compatible_submodule_path("C1-C2", compatibility)
  n_rel = tool_compatible_submodule_path("UOG_N", compatibility)

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
      n_rel,
      os.path.join("ITV_POLIMI", "PAH_BLOCK.CKI"),
      os.path.join("LLNL", "LLNL_BLOCK_DMC_EC.CKI"),
      os.path.join("UOG", "LT-HT", "UOG_MTBE_LT-HT.MECH"),
      os.path.join("LLNL", "LLNL_BLOCK_LARGE_METHYL_ESTERS.CKI"),
      os.path.join("ITV_POLIMI", "OMEs.CKI"),
  ]

  required_extension_HT = [
      os.path.join("UOG", "HT", "UOG_" + "C-N" + "_HT.MECH")
  ]
  required_extension_HTLT = [
      os.path.join("UOG", "LT-HT", "UOG_" + "C-N" + "_LT-HT.MECH")
  ]

  modules_ht = base_modules_UOG_HT + LLNL_base_modules_HT + optional_modules + required_extension_HT  # + optional_modules_HT
  modules_htlt = base_modules_UOG_HTLT + LLNL_base_modules_HTLT + optional_modules + required_extension_HTLT  #  + optional_modules_HTLT

  if submodule_keys is not None:
    requested = {key: "" for key in submodule_keys}
    selected_ht, selected_ltht = match_submodules(
        requested, modules_ht, modules_htlt)
    modules_ht = list(selected_ht.values())
    modules_htlt = list(selected_ltht.values())

  # Use the provided directory as-is (normalized); do not rewrite it here.
  submodules_dir = os.path.abspath(os.path.normpath(abs_dir))
  if not os.path.isdir(submodules_dir):
    raise UserInputError("sub-modules directory does not exist: '" +
                         submodules_dir + "'")
  ok = True
  modules_ht_final = []
  for f in modules_ht:
    cur_path = os.path.join(submodules_dir, f)
    if (not os.path.isfile(cur_path)):
      print_not_found("", "file", cur_path)
      ok = False
    modules_ht_final.append(os.path.abspath(os.path.normpath(cur_path)))
  modules_htlt_final = []
  for f in modules_htlt:
    cur_path = os.path.join(submodules_dir, f)
    if (not os.path.isfile(cur_path)):
      print_not_found("", "file", cur_path)
      ok = False
    modules_htlt_final.append(os.path.abspath(os.path.normpath(cur_path)))
  if not ok:
    raise UserInputError(
        "could not find all required sub-module files under '" +
        submodules_dir + "'")

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
      ('UOG_MTBE' in s),
      ('LLNL_BLOCK_LARGE_METHYL_ESTERS' in s),
      ('OMEs' in s),
      sorted(s)  # To break ties lexicographically
  )


def match_submodules(submodules, modules_ht, modules_htlt):
  """
    For each key in `submodules` find its unique match in the HT and LT-HT
    module lists (case-insensitive).

    Returns two dictionaries:  submodules_ht, submodules_htlt
    Raises ValueError if more than one candidate matches the same key.
    """

  def find_match(smod, modules_list, label):
    smod_l = smod.lower()

    # ---------- special cases ---------------------------------------------
    if smod_l == "llnl_block":
      expected = "llnl_block_ht" if label == "HT" else "llnl_block.cki"
      matches = [
          m for m in modules_list if expected in os.path.basename(m).lower()
      ]

    elif smod_l == "llnl_block_dmc_ec":
      matches = [
          m for m in modules_list
          if "llnl_block_dmc_ec" in os.path.basename(m).lower()
      ]

    elif smod_l == "pah_block":
      matches = [
          m for m in modules_list
          if "pah_block" in os.path.basename(m).lower()
      ]

    else:
      # ---------- generic two-pass search --------------------------------
      # 1) Prefer UOG_<smod>_
      matches = [
          m for m in modules_list
          if (f"{smod_l}_" in os.path.basename(m).lower()
              and os.path.basename(m).lower().startswith("uog_"))
      ]

      # 2) Otherwise look for '<smod>_' OR '<smod>.'
      if not matches:
        base_matches = [
            m for m in modules_list
            if (f"{smod_l}_" in os.path.basename(m).lower()
                or f"{smod_l}." in os.path.basename(m).lower())
        ]
        matches = base_matches

    # ---------- evaluate result ------------------------------------------
    if len(matches) > 1:
      raise ValueError(f"second match for '{smod}' in {label}: " +
                       " / ".join(matches))

    return matches[0] if matches else None

  # ------------------------------------------------------------------------
  submodules_ht = {}
  submodules_htlt = {}

  for smod in submodules:
    ht_match = find_match(smod, modules_ht, "HT")
    htlt_match = find_match(smod, modules_htlt, "LT-HT")

    if ht_match:
      submodules_ht[smod] = ht_match
    if htlt_match:
      submodules_htlt[smod] = htlt_match

  return submodules_ht, submodules_htlt


def _get_submodule_filenames(abs_dir, submodule_keys, cantera_mode=None):
  """Return HT and LT-HT filenames for the given ordered internal keys."""
  validate_dependency_definitions()
  submodules = {}
  for dep in submodule_keys:
    submodules[dep] = ""
  modules_ht, modules_htlt = get_ht_htlt_modules(
      abs_dir, cantera_mode, submodule_keys)
  submodules_ht, submodules_htlt = match_submodules(submodules, modules_ht,
                                                    modules_htlt)

  missing_ht = [k for k in submodule_keys if k not in submodules_ht]
  missing_ltht = [k for k in submodule_keys if k not in submodules_htlt]

  if missing_ht or missing_ltht:
    msg = "could not find sub-module file matches"
    if missing_ht:
      msg += "; HT: " + ", ".join(missing_ht)
    if missing_ltht:
      msg += "; LT-HT: " + ", ".join(missing_ltht)
    msg += ". Check your SUBMODULES directory and expected filenames."
    raise UserInputError(msg)

  submodules_filenames = {
      "HT": submodules_ht,
      "LT-HT": submodules_htlt,
  }

  return submodules_filenames


def get_submodule_filenames(abs_dir, cantera_mode=None):
  """Return every public submodule filename in identifier order."""
  return _get_submodule_filenames(abs_dir, get_repository_submodules(),
                                  cantera_mode)


def get_selected_submodule_filenames(abs_dir, version, selected_submodules,
                                     cantera_mode=None):
  """Return HT and LT-HT filenames for an explicit submodule selection."""
  selected = validate_submodule_selection(version, selected_submodules)
  return _get_submodule_filenames(abs_dir, selected, cantera_mode)

def normalize_submodule_filenames_for_tool_independent_keys(filenames):
  """Return filenames normalized for tool-independent submodel keys."""
  return [
      normalize_submodule_filename_for_tool_independent_key(f)
      for f in filenames
  ]

def get_ht_ltht_pairs(abs_dir):
  """Return ordered (LT-HT, HT) file pairs from C3 sub-module mapping."""
  submodules_filenames = get_submodule_filenames(abs_dir)
  ht_map = submodules_filenames["HT"]
  ltht_map = submodules_filenames["LT-HT"]

  missing_ht = [k for k in ltht_map.keys() if k not in ht_map]
  missing_ltht = [k for k in ht_map.keys() if k not in ltht_map]
  if missing_ht or missing_ltht:
    raise UserInputError("HT/LT-HT sub-module key mismatch: "
                         "missing HT keys=" + str(sorted(missing_ht)) +
                         ", missing LT-HT keys=" + str(sorted(missing_ltht)))

  ordered_keys = [k for k in ORDERED_KEYS if (k in ht_map and k in ltht_map)]
  extra_keys = sorted(
      [k for k in ht_map.keys() if k not in ORDERED_KEYS and k in ltht_map])
  all_keys = ordered_keys + extra_keys

  pairs = []
  for key in all_keys:
    parent = os.path.normpath(ltht_map[key])
    ht_ref = os.path.normpath(ht_map[key])
    pairs.append((parent, ht_ref))
  return pairs


def is_ht(filenames, submodules_dir):
  submodules_filenames = get_submodule_filenames(submodules_dir)
  ht_files = set(list(submodules_filenames["HT"].values()))
  ht_files = normalize_submodule_filenames_for_tool_independent_keys(ht_files)
  filenames = normalize_submodule_filenames_for_tool_independent_keys(
      filenames)
  filenames = get_relative_submodule_paths(filenames, submodules_dir)
  ht_files = get_relative_submodule_paths(ht_files, submodules_dir)
  for f in filenames:
    if f not in ht_files:
      return False
  return True

def is_ltht(filenames, submodules_dir):
  submodules_filenames = get_submodule_filenames(submodules_dir)
  ltht_files = set(list(submodules_filenames["LT-HT"].values()))
  ltht_files = normalize_submodule_filenames_for_tool_independent_keys(
      ltht_files)
  filenames = normalize_submodule_filenames_for_tool_independent_keys(
      filenames)
  filenames = get_relative_submodule_paths(filenames, submodules_dir)
  ltht_files = get_relative_submodule_paths(ltht_files, submodules_dir)
  for f in filenames:
    if f not in ltht_files:
      return False
  return True


def _generate_submodel_selections(version, selected_submodules=None):
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

  midgen = MID(ORDERED_KEYS, BINARY_KEYS, version=version)
  encodable_keys = set(midgen._keys)
  if selected_submodules is None:
    selected_submodules = tuple(
        key for key in midgen._keys if key in get_repository_submodules())
  else:
    selected_submodules = validate_submodule_selection(
        version, selected_submodules)
  selected_set = set(selected_submodules)

  combinations_list = generate_valid_combinations(DEPENDENCIES)
  combinations_final = []
  for combo in combinations_list:
    # Keep generate-all consistent with MID encoding for the selected version.
    if set(combo) - encodable_keys:
      continue
    if set(combo) - selected_set:
      continue

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

  return sorted(combinations_final, key=sort_key), len(combinations_list)


def generate_submodel_selections(version, selected_submodules=None):
  """Return every valid submodule selection encodable for one version."""
  selections, _ = _generate_submodel_selections(version,
                                                 selected_submodules)
  return selections


def generate_submodels(options):

  selected_submodules = getattr(options, "selected_submodules", None)
  if selected_submodules is None:
    submodules_filenames = get_submodule_filenames(options.submodules_dir)
  else:
    submodules_filenames = get_selected_submodule_filenames(
        options.submodules_dir, options.version, selected_submodules)

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

  sorted_combos, unfiltered_count = _generate_submodel_selections(
      options.version, selected_submodules)
  midgen = MID(ORDERED_KEYS, BINARY_KEYS, version=options.version)
  n = len(sorted_combos)
  print(
      "Found", n, "possible combinations (" + str(unfiltered_count - n) +
      " options excluded)")
  # for combo in sorted_combos:
  #  print(combo)
  # print("stop")
  # sys.exit(1)
  grouped_combos = defaultdict(dict)
  for module_set in sorted_combos:
    cnum = max_carbon(module_set)
    if exceeds_carbon_limit(cnum, options.max_c):
      continue

    if cnum not in grouped_combos:
      grouped_combos[cnum] = {}
      dir_name = CARBON_BLOCK_NAMES.get(cnum, f"C{cnum}")
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
    Stable, mixed-radix model-ID encoder/decoder.

    Versions 4.0 and 4.0.1 encode only CODING_KEYS_V4_0.
    Later V4 versions retain that numeric space and encode added submodules
    in higher-order mixed-radix digits. A selection containing only V4.0.1
    submodules therefore retains its V4.0.1 MID.
    """

    BASE = 36
    CHARS = string.digits + string.ascii_lowercase
    START = ""            # optional leading char
    WITH_VERSION = False  # optional "4.0_" prefix inside ID body

    # ----------------------------------------------------------------

    def __init__(
        self,
        ordered_keys: Sequence[str],
        binary_keys: Sequence[str],
        version: str,
    ) -> None:

        self.version = version
        self._binary_keys = frozenset(binary_keys)

        available_keys = tuple(ordered_keys)

        # Which keys participate in the numeric code?
        if version in {"4.0", "4.0.1"}:
            self._keys: Sequence[str] = CODING_KEYS_V4_0
            required_prefix = CODING_KEYS_V4_0
            required_binary_keys = BINARY_KEYS_V4_0
        elif version == "4.1.0":
            self._keys = CODING_KEYS_V4_1_0
            required_prefix = CODING_KEYS_V4_1_0
            required_binary_keys = BINARY_KEYS_V4_1_0
        elif re.fullmatch(r"4\.[A-Za-z0-9_.+-]+", version):
            self._keys = available_keys
            required_prefix = CODING_KEYS_V4_1_0
            required_binary_keys = BINARY_KEYS_V4_1_0
        else:
            raise UserInputError(f"Unsupported version '{version}'")
        if available_keys[:len(required_prefix)] != required_prefix:
            raise UserInputError(
                "MID keys must begin with the unchanged keys for version " +
                version)
        actual_binary_keys = self._binary_keys.intersection(required_prefix)
        if actual_binary_keys != required_binary_keys:
            raise UserInputError(
                "MID binary keys conflict with the unchanged keys for " +
                "version " + version)

        # Mixed-radix base per digit
        self._bases: List[int] = []
        for key in self._keys:
            if key in CODING_KEYS_V4_0:
                is_binary = key in BINARY_KEYS_V4_0
            elif key in CODING_KEYS_V4_1_0:
                is_binary = key in BINARY_KEYS_V4_1_0
            else:
                is_binary = key in self._binary_keys
            self._bases.append(2 if is_binary else 3)
        self._v4_0_key_count = len(CODING_KEYS_V4_0)
        self._v4_0_capacity = 1
        for base in self._bases[:self._v4_0_key_count]:
            self._v4_0_capacity *= base

    # ----------------------------------------------------------------
    #  Internal helpers
    # ----------------------------------------------------------------

    def _int_to_base36(self, n: int) -> str:
        if n == 0:
            return self.CHARS[0]
        out: List[str] = []
        while n:
            out.append(self.CHARS[n % self.BASE])
            n //= self.BASE
        return "".join(reversed(out))

    def _base36_to_int(self, s: str) -> int:
        val = {c: i for i, c in enumerate(self.CHARS)}
        n = 0
        for ch in s.lower():
            n = n * self.BASE + val[ch]
        return n

    # ----------------------------------------------------------------
    #  Public helpers
    # ----------------------------------------------------------------

    def max_mid(self) -> str:
        capacity = self._v4_0_capacity
        for base in self._bases[self._v4_0_key_count:]:
            capacity *= base
        n = capacity - 1
        body = self._int_to_base36(n).upper()
        if self.WITH_VERSION:
            body = f"{self.version}_{body}"
        return f"{self.START}{body}"

    # ----------------------------------------------------------------
    #  Encode
    # ----------------------------------------------------------------

    def combo_to_id(self, selection: Dict[str, str]) -> str:
        unknown = [k for k in selection if k not in self._keys]
        if unknown:
            raise UserInputError(
                f"Invalid submodules for MID version {self.version}: {unknown}"
            )

        digits = []
        for key, base in zip(self._keys, self._bases):
            if key not in selection:
                digit = 0
            elif base == 2:
                digit = 1
            else:
                digit = 1 if selection[key] == "HT" else 2
            digits.append(digit)

        n = 0
        for digit, base in zip(
            digits[:self._v4_0_key_count],
            self._bases[:self._v4_0_key_count],
        ):
            n = n * base + digit

        multiplier = self._v4_0_capacity
        for digit, base in zip(
            digits[self._v4_0_key_count:],
            self._bases[self._v4_0_key_count:],
        ):
            n += digit * multiplier
            multiplier *= base

        body = self._int_to_base36(n).upper()
        if self.WITH_VERSION:
            body = f"{self.version}_{body}"
        return f"{self.START}{body}"

    # ----------------------------------------------------------------
    #  Decode
    # ----------------------------------------------------------------

    def id_to_combo(self, mid: str) -> Dict[str, str]:
        if not re.fullmatch(r"[A-Za-z0-9]+", mid):
            raise UserInputError("MID contains invalid characters")

        if self.START:
            if not mid.startswith(self.START):
                raise UserInputError("Missing start char")
            mid = mid[len(self.START):]

        if self.WITH_VERSION:
            ver, body = mid.split("_", 1)
            if ver != self.version:
                raise UserInputError("MID belongs to another version")
            id_body = body
        else:
            id_body = mid

        n = self._base36_to_int(id_body)

        v4_0_value = n % self._v4_0_capacity
        extension_value = n // self._v4_0_capacity

        v4_0_digits: List[int] = []
        for base in reversed(self._bases[:self._v4_0_key_count]):
            v4_0_digits.append(v4_0_value % base)
            v4_0_value //= base
        v4_0_digits.reverse()

        extension_digits: List[int] = []
        for base in self._bases[self._v4_0_key_count:]:
            extension_digits.append(extension_value % base)
            extension_value //= base
        if extension_value:
            raise UserInputError(f"Invalid MID '{mid}': out of range")

        digits = v4_0_digits + extension_digits

        selection: Dict[str, str] = {}
        for key, digit, base in zip(self._keys, digits, self._bases):
            if digit == 0:
                continue
            if base == 2:
                selection[key] = "LT-HT"
            elif digit == 1:
                selection[key] = "HT"
            else:
                selection[key] = "LT-HT"
        return selection


def get_grouped_combos_mid(options):
  print("Generating model from MID '" + options.mid + "'")
  midgen = MID(ORDERED_KEYS, BINARY_KEYS, version=options.version)

  # Decide which physical sub-modules to map to ambiguous keys (C0, C1-C2)
  global CANTERA_MODE
  CANTERA_MODE = bool(options.mid_cantera)

  selection = midgen.id_to_combo(options.mid)

  print("MID '" + options.mid + "' decoded as:")
  for key, temp in selection.items():
    print(f"{key:<20} {temp}")

  selection_keys = set(selection.keys())
  unavailable = sorted(selection_keys - set(get_repository_submodules()))
  if unavailable:
    raise UserInputError(
        "MID selects submodules not supplied in this public release: " +
        ", ".join(unavailable))
  # Enforce dependency constraints for decoded MIDs.
  for key in selection_keys:
    missing = DEPENDENCIES[key] - selection_keys
    if missing:
      raise UserInputError(
          "MID '" + options.mid +
          "' decodes to an invalid sub-module combination.\n"
          "Sub-module '" + key + "' is missing required dependencies: " +
          ", ".join(sorted(missing)))

  # Enforce selection policy used for official generated combinations.
  has_carbon = bool((set(get_base_modules()) & selection_keys)
                    or ({"LLNL_BLOCK", "LLNL_BLOCK_DMC_EC", "PAH_BLOCK"}
                        & selection_keys))
  if has_carbon and "UOG_N" in selection_keys and "UOG_C-N" not in selection_keys:
    raise UserInputError(
        "MID '" + options.mid +
        "' decodes to an excluded combination "
        "(UOG_N with carbon chemistry requires UOG_C-N).")

  if DMC_EC_FEW and (((max_carbon(selection_keys) > 2 or "UOG_N" in selection_keys)
                      and max_carbon(selection_keys) < 8)
                     and "LLNL_BLOCK_DMC_EC" in selection_keys):
    raise UserInputError(
        "MID '" + options.mid +
        "' decodes to an excluded combination based on the DMC+EC "
        "selection policy.")

  if 'C0' not in selection:
    raise UserInputError(
        "Required sub-module 'C0' is missing. Please double check the "
        "provided MID '" + options.mid + "'")

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
      raise RuntimeError("Internal temperature label error: unexpected value '" +
                         temp + "'")
    else:
      #print(key, "temperature-independent")
      n_temp_independent += 1

  if n_temp_independent == len(selection):
    all_ht = False
    all_lt_ht = False
  elif all_lt_ht and all_ht:
    raise RuntimeError("Internal classification error: all HT and all LT-HT "
                       "cannot both be true")

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
    raise UserInputError("duplicate file paths detected in yaml input")


def get_relative_submodule_paths(used_paths, submodules_dir):
  """
    Return a dict {relative_path : absolute_path} for every entry in
    `used_paths` that is located inside `submodules_dir`.
    """

  # Canonical form of the base directory
  base = os.path.abspath(submodules_dir)
  base = os.path.normcase(os.path.normpath(base))

  used_paths_rel = {}

  for p in used_paths:
    # Canonical absolute path
    p_abs = os.path.abspath(p)
    p_norm = os.path.normcase(os.path.normpath(p_abs))

    # Ensure the file is really under the sub-modules directory
    try:
      common = os.path.commonpath([base, p_norm])
    except ValueError as exc:
      raise UserInputError("Path '" + p_abs + "' is not inside '" +
                           submodules_dir + "'") from exc
    if common != base:
      raise UserInputError("Path '" + p_abs + "' is not inside '" +
                           submodules_dir + "'")

    # Canonical relative path
    rel = os.path.relpath(p_abs, base)
    rel = os.path.normcase(os.path.normpath(rel))

    if rel in used_paths_rel:
      raise UserInputError(f"Duplicate relative path '{rel}'")
    used_paths_rel[rel] = p_abs

  return used_paths_rel


def construct_path_to_key_temp(submodules_filenames, submodules_dir):
  # --- Build mapping of file paths to keys and temperatures ---
  path_to_key_temp = {}
  # IMPORTANT: submodules_filenames is ORDERED!
  for temp in submodules_filenames:
    for key, p in submodules_filenames[temp].items():
      p_rel = get_relative_submodule_paths([p], submodules_dir)
      path_to_key_temp[list(p_rel.keys())[0]] = (key, temp)

  alias_candidates = []
  for key, basenames in TOOL_COMPATIBLE_SUBMODULE_BASENAMES.items():
    for compatibility in basenames:
      alias_candidates.append(
          (tool_compatible_submodule_path(key, compatibility), (key, "LT-HT")))
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


def add_verified_tool_compatible_path_aliases(
    used_paths_rel, path_to_key_temp, submodules_dir):
  """Classify capitalization variants that identify the same physical file.

  The selected paths remain unchanged. A capitalization variant is accepted
  only when ``os.path.samefile`` verifies the expected repository file.
  """
  for selected_rel, selected_abs in used_paths_rel.items():
    selected_basename = os.path.basename(selected_rel)
    selected_basename_casefold = selected_basename.casefold()
    canonical_basename = None
    for submodule_basenames in TOOL_COMPATIBLE_SUBMODULE_BASENAMES.values():
      for recognized_basename in submodule_basenames.values():
        if selected_basename_casefold == recognized_basename.casefold():
          canonical_basename = recognized_basename
          break
      if canonical_basename is not None:
        break

    if canonical_basename is None:
      if ("_ic" in selected_basename_casefold or
          "_cantera" in selected_basename_casefold):
        raise UserInputError(
            "unknown IC submodule filename: '" +
            selected_abs + "'")
      continue

    canonical_rel = os.path.normcase(os.path.normpath(os.path.join(
        os.path.dirname(selected_rel), canonical_basename)))
    if canonical_rel not in path_to_key_temp:
      raise UserInputError(
          "recognized submodule file is unavailable in the selected "
          "SUBMODULES directory: '" + canonical_rel + "'")
    canonical_abs = os.path.join(submodules_dir, canonical_rel)
    if not os.path.samefile(selected_abs, canonical_abs):
      raise UserInputError(
          "submodule filename capitalization identifies a different file: '" +
          selected_abs + "' and '" + canonical_abs + "'")
    if (selected_rel in path_to_key_temp and
        path_to_key_temp[selected_rel] != path_to_key_temp[canonical_rel]):
      raise RuntimeError(
          "submodule path alias has conflicting classifications: '" +
          selected_rel + "'")
    path_to_key_temp[selected_rel] = path_to_key_temp[canonical_rel]


def check_HT_and_LT_HT_combi(used_paths_rel, path_to_key_temp, yaml_file_path):
  seen_keys = {}
  for p in used_paths_rel:
    if p not in path_to_key_temp:
      raise UserInputError(f"unknown sub-module '{used_paths_rel[p]}'. " +
                           "Check your input or update the compiler script.")
    smod = path_to_key_temp[p][0]
    if smod in seen_keys:
      raise UserInputError("HT and LT-HT version of sub-module '" + smod +
                           "' must not be combined.\n"
                           "Conflicting files:\n"
                           "  '" + used_paths_rel[p] + "'\n"
                           "  '" + seen_keys[path_to_key_temp[p][0]] + "'\n"
                           "Check YAML input file '" + yaml_file_path + "'")
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
  CANTERA_MODE = detect_cantera_mode({"LT-HT": {"C0": core_rel}})
  c0_basenames = TOOL_COMPATIBLE_SUBMODULE_BASENAMES["C0"]

  # Build mapping AFTER CANTERA_MODE is set (self-consistent mapping)
  submodules_filenames = get_submodule_filenames(submodules_dir_copy)

  # Validate and classify used paths
  used_paths = [submodules_files.core] + submodules_files.submodules
  check_duplicate(used_paths)

  path_to_key_temp = construct_path_to_key_temp(submodules_filenames,
                                                submodules_dir_copy)
  used_paths_rel = get_relative_submodule_paths(used_paths,
                                                submodules_dir_copy)
  add_verified_tool_compatible_path_aliases(
      used_paths_rel, path_to_key_temp, submodules_dir_copy)

  # Forbid mixing tool-compatible submodule variants.
  selected_basenames = {
      os.path.basename(path).casefold() for path in used_paths_rel.keys()
  }
  c1_c2_basenames = TOOL_COMPATIBLE_SUBMODULE_BASENAMES["C1-C2"]
  n_basenames = TOOL_COMPATIBLE_SUBMODULE_BASENAMES["UOG_N"]
  has_c12_can = c1_c2_basenames["cantera"].casefold() in selected_basenames
  has_c12_chemkin_pro = (
      c1_c2_basenames["chemkin_pro"].casefold() in selected_basenames)
  has_n_can = n_basenames["cantera"].casefold() in selected_basenames
  has_n_chemkin_pro = (
      n_basenames["chemkin_pro"].casefold() in selected_basenames)
  c0_paths = {
      compatibility: tool_compatible_submodule_label("C0", compatibility)
      for compatibility in c0_basenames
  }
  c1_c2_paths = {
      compatibility: tool_compatible_submodule_label("C1-C2", compatibility)
      for compatibility in c1_c2_basenames
  }
  n_paths = {
      compatibility: tool_compatible_submodule_label("UOG_N", compatibility)
      for compatibility in n_basenames
  }

  if has_c12_can and has_c12_chemkin_pro:
    raise UserInputError("Both IC and LOWMX/LOWSP "
                         "C1-C2 submodule files were selected.\n"
                         "Please select only one of:\n"
                         "  " + c1_c2_paths["chemkin_pro"] + "\n"
                         "  " + c1_c2_paths["cantera"] + "\n"
                         "YAML file: '" + yaml_file_path + "'")

  if CANTERA_MODE and has_c12_chemkin_pro:
    raise UserInputError(
        "IC C0 core requires the IC C1-C2 "
        "sub-module.\n"
        "Selected core : " + c0_paths["cantera"] + "\n"
        "Incompatible : " + c1_c2_paths["chemkin_pro"] + "\n"
        "YAML file: '" + yaml_file_path + "'")
  if (not CANTERA_MODE) and has_c12_can:
    raise UserInputError(
        "LOWMX/LOWSP C0 core must not be combined with an "
        "IC C1-C2 submodule.\n"
        "Selected core : " + c0_paths["chemkin_pro"] + "\n"
        "Incompatible : " + c1_c2_paths["cantera"] + "\n"
        "YAML file: '" + yaml_file_path + "'")

  if has_n_can and has_n_chemkin_pro:
    raise UserInputError("Both IC and LOWMX/LOWSP "
                         "UOG_N submodule files were selected.\n"
                         "Please select only one of:\n"
                         "  " + n_paths["chemkin_pro"] + "\n"
                         "  " + n_paths["cantera"] + "\n"
                         "YAML file: '" + yaml_file_path + "'")
  if CANTERA_MODE and has_n_chemkin_pro:
    raise UserInputError(
        "IC C0 core requires the IC UOG_N "
        "submodule.\n"
        "Selected core : " + c0_paths["cantera"] + "\n"
        "Incompatible : " + n_paths["chemkin_pro"] + "\n"
        "YAML file: '" + yaml_file_path + "'")
  if (not CANTERA_MODE) and has_n_can:
    raise UserInputError(
        "LOWMX/LOWSP C0 core requires the LOWMX/LOWSP "
        "UOG_N submodule.\n"
        "Selected core : " + c0_paths["chemkin_pro"] + "\n"
        "Incompatible : " + n_paths["cantera"] + "\n"
        "YAML file: '" + yaml_file_path + "'")

  check_HT_and_LT_HT_combi(used_paths_rel, path_to_key_temp, yaml_file_path)

  # Build selection and sorted submodules using the used paths and path_to_key_temp
  selection = {}
  selected_by_key = {}
  for p_rel, p_abs in used_paths_rel.items():
    if p_rel not in path_to_key_temp:
      raise UserInputError("unknown sub-module '" + used_paths_rel[p_rel] +
                           "'. Check your input or update the compiler script.")
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
  if __package__:
    from .chemmodkit.input import make_submodulefiles_from_yaml
  else:
    from chemmodkit.input import make_submodulefiles_from_yaml

  submodules_files = make_submodulefiles_from_yaml(options.yaml_file_path,
                                                   options.submodules_dir)

  submodules_files, selection = normalize_and_check_submodule_paths(
      submodules_files, options.submodules_dir, options.yaml_file_path)
  used_paths = [submodules_files.core] + submodules_files.submodules

  midgen = MID(ORDERED_KEYS, BINARY_KEYS, version=options.version)
  id_str = midgen.combo_to_id(selection)
  print("Generated MID:", id_str)

  grouped_combos = defaultdict(dict)
  cnum = max_carbon(selection.keys())
  grouped_combos[cnum]["modules"] = [selection]
  grouped_combos[cnum]["mid"] = [id_str]
  temp_str = ""
  all_ht = is_ht(used_paths, options.submodules_dir)
  all_lt_ht = is_ltht(used_paths, options.submodules_dir)

  if all_ht == all_lt_ht:
    grouped_combos[cnum]["temperature"] = [""]
  elif all_ht:
    temp_str = "_HT"
    grouped_combos[cnum]["temperature"] = ["HT"]
  elif all_lt_ht:
    temp_str = "_LT-HT"
    grouped_combos[cnum]["temperature"] = ["LT-HT"]
  else:
    raise RuntimeError("Internal classification error: unreachable temperature "
                       "branch")

  grouped_combos[cnum]["output_chunks"] = [
      sanitize_filename(list(selection.keys())) + temp_str
  ]

  grouped_combos[cnum]["output_dir"] = options.output_dir

  return grouped_combos
