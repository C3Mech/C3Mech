from collections import Counter
from pathlib import Path
import re
import textwrap
import unicodedata
from urllib.parse import urlparse

MIN_HEADER_WIDTH = 80
MAX_HEADER_WIDTH = 120
HEADER_WIDTH = 102
CONTENT_WIDTH = HEADER_WIDTH - 4
AUTHOR_WIDTH = 24
HEADER_TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "templates" /
    "chemical_model_headers" / "C3Mech_header.txt.in")

_FIELD_PATTERN = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
_INFORMATION_ADDRESS_MARKER = "\0INFORMATION_ADDRESS\0"
_WRAP_WORD_PATTERN = (
    r"[^ \t\n\r\v\f]*" + re.escape(_INFORMATION_ADDRESS_MARKER) +
    r"[^ \t\n\r\v\f]*")
_ASCII_PUNCTUATION = str.maketrans({
    "\u00a0": " ",
    "\u00ab": '"',
    "\u00bb": '"',
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2026": "...",
    "\u202f": " ",
    "\u2212": "-",
})
_PROTECTED_SPACES = {"\u00a0", "\u202f"}
_EXPECTED_FIELDS = Counter({
    "SEPARATOR_BLOCK": 4,
    "TITLE_BLOCK": 1,
    "CONSORTIUM_NAME": 1,
    "CONSORTIUM_ABBREVIATION": 1,
    "INTRODUCTORY_ORGANIZATIONS": 1,
    "MODEL_NAME": 2,
    "REPOSITORY_SERVICE": 1,
    "INFORMATION_ADDRESS": 1,
    "SOURCE_URL_BLOCK": 1,
    "CITATIONS_BLOCK": 1,
    "WORKING_GROUPS_BLOCK": 1,
    "AUTHORS_BLOCK": 1,
    "WARNING_BLOCK": 1,
})
_BLOCK_FIELDS = {
    "SEPARATOR_BLOCK",
    "SOURCE_URL_BLOCK",
    "TITLE_BLOCK",
    "CITATIONS_BLOCK",
    "WORKING_GROUPS_BLOCK",
    "AUTHORS_BLOCK",
    "WARNING_BLOCK",
}
class C3MechHeaderError(ValueError):
  """Fatal error while rendering a C3Mech chemical kinetic model header."""
  pass


def _ascii_header_prose(content):
  """Return one ASCII representation of CHEMKIN-format header prose."""
  nonprinting = [
      character for character in content
      if (unicodedata.category(character)[0] == "C" or
          unicodedata.category(character) in {"Zl", "Zp"})
  ]
  if nonprinting:
    raise C3MechHeaderError(
        "fixed width header content contains a nonprinting character: " +
        repr(nonprinting[0]))
  unsupported = [
      character for character in content
      if unicodedata.category(character).startswith("M") or
      unicodedata.east_asian_width(character) in {"W", "F"}
  ]
  if unsupported:
    raise C3MechHeaderError(
        "fixed width header content contains a combining or double width "
        "character: " + repr(unsupported[0]))
  decomposed = unicodedata.normalize(
      "NFD", content.translate(_ASCII_PUNCTUATION))
  ascii_content = "".join(
      character for character in decomposed
      if not unicodedata.category(character).startswith("M"))
  non_ascii = next(
      (character for character in ascii_content if not character.isascii()),
      None)
  if non_ascii is not None:
    raise C3MechHeaderError(
        "fixed width header content cannot be represented as ASCII: " +
        repr(non_ascii))
  return ascii_content


def _content_width(header_width):
  if (not isinstance(header_width, int) or isinstance(header_width, bool) or
      not MIN_HEADER_WIDTH <= header_width <= MAX_HEADER_WIDTH):
    raise C3MechHeaderError(
        "header_width must be an integer from " + str(MIN_HEADER_WIDTH) +
        " through " + str(MAX_HEADER_WIDTH))
  return header_width - 4


def _frame(content, content_width=CONTENT_WIDTH):
  content = _ascii_header_prose(content)
  if len(content) > content_width:
    raise C3MechHeaderError(
        "header content exceeds " + str(content_width) + " characters: " +
        content)
  return "! " + content.ljust(content_width) + " !"


def _wrap_paragraph(paragraph, width=CONTENT_WIDTH):
  paragraph = "".join(
      part if part in _PROTECTED_SPACES else _ascii_header_prose(part)
      for part in re.split("([\u00a0\u202f])", paragraph))
  lines = textwrap.wrap(
      paragraph,
      width=width,
      break_long_words=False,
      break_on_hyphens=False)
  if not lines:
    raise C3MechHeaderError("header paragraph must not be empty")
  if any(len(line) > width for line in lines):
    raise C3MechHeaderError(
        "header paragraph contains a word exceeding " + str(width) +
        " characters: " + paragraph)
  return [_ascii_header_prose(line) for line in lines]


def _format_publication_authors(authors):
  names = tuple(author.citation_name for author in authors)
  return ", ".join(names)


def _format_series(values):
  if len(values) == 1:
    return values[0]
  if len(values) == 2:
    return values[0] + " and " + values[1]
  return ", ".join(values[:-1]) + ", and " + values[-1]


def _render_introductory_organizations(configuration):
  affiliation_ids = []
  for author in configuration.authors:
    for affiliation_id in author.affiliation_ids:
      if affiliation_id not in configuration.affiliations:
        raise C3MechHeaderError(
            "author " + author.identifier +
            " references missing affiliation " + affiliation_id)
      if affiliation_id not in affiliation_ids:
        affiliation_ids.append(affiliation_id)
  return _format_series(tuple(
      configuration.affiliations[affiliation_id].organization
      for affiliation_id in affiliation_ids))


def _render_citations(configuration, content_width):
  lines = []
  for number, citation in enumerate(configuration.header_citations, start=1):
    prefix = str(number) + ") "
    title = citation.title
    title_before_closing_marks = title
    while (title_before_closing_marks and
           (title_before_closing_marks[-1] in "\"'’”" or
            unicodedata.category(title_before_closing_marks[-1]) in
            {"Pe", "Pf"})):
      title_before_closing_marks = title_before_closing_marks[:-1]
    if not title_before_closing_marks.endswith(
        (".", "?", "!", "…", "。", "！", "？")):
      title += "."
    if citation.publication_type == "article":
      volume_issue = citation.volume
      if citation.issue is not None:
        volume_issue += "(" + citation.issue + ")"
      locator = citation.article_number
      if locator is None:
        locator = citation.start_page + "-" + citation.end_page
      paragraph = (
          _format_publication_authors(citation.authors) +
          " (" + str(citation.year) + "). " + title + " " +
          citation.journal + ", " + volume_issue + ", " +
          locator + ". https://doi.org/" + citation.doi)
    else:
      authors = _format_publication_authors(citation.authors)
      year = "" if citation.year is None else " (" + str(citation.year) + ")"
      paragraph = authors + year + ", " + title
      if citation.doi is not None or citation.url is not None:
        link = ("https://doi.org/" + citation.doi
                if citation.doi is not None else citation.url)
        paragraph += " Preprint. " + link
    wrapped = _wrap_paragraph(
        paragraph, width=content_width - 6)
    lines.extend(
        (prefix if index == 0 else " " * len(prefix)) + line
        for index, line in enumerate(wrapped))
  return lines


def _render_authors(configuration, content_width):
  affiliation_width = content_width - AUTHOR_WIDTH - 2
  lines = [
      "Author".ljust(AUTHOR_WIDTH) + "| Institution",
      "-" * content_width,
  ]
  for author in configuration.authors:
    address_lines = []
    for affiliation_id in author.affiliation_ids:
      affiliation = configuration.affiliations[affiliation_id]
      affiliation_lines = list(affiliation.address_lines)
      organization_pattern = (
          r"(?<!\w)" + re.escape(affiliation.organization) + r"(?!\w)")
      if not any(re.search(organization_pattern, line)
                 for line in affiliation_lines):
        affiliation_lines.insert(0, affiliation.organization)
      for line in affiliation_lines:
        address_lines.extend(_wrap_paragraph(line, width=affiliation_width))
    row_count = max(2, len(address_lines))
    for index in range(row_count):
      name = _ascii_header_prose(author.name) if index == 0 else ""
      address = address_lines[index] if index < len(address_lines) else ""
      if len(name) > AUTHOR_WIDTH:
        raise C3MechHeaderError(
            "author name exceeds " + str(AUTHOR_WIDTH) +
            " characters: " + name)
      lines.append(
          name.ljust(AUTHOR_WIDTH) + "| " +
          address.ljust(affiliation_width))
  return lines


def _render_title(configuration, content_width):
  if configuration.model.header_title is None:
    return _ascii_header_prose(configuration.model.name).center(content_width)
  title = " " * 11 + _ascii_header_prose(
      configuration.model.header_title)
  if len(title) > content_width:
    raise C3MechHeaderError(
        "model.header_title exceeds the available header width")
  return title


def _read_template(template_path):
  try:
    template_bytes = Path(template_path).read_bytes()
    template = template_bytes.decode("utf-8")
  except (OSError, UnicodeError) as error:
    raise C3MechHeaderError(
        "could not read C3Mech header template: " + str(template_path)) \
        from error
  if any(character not in "\r\n" and
         (unicodedata.category(character)[0] == "C" or
          unicodedata.category(character) in {"Zl", "Zp"})
         for character in template):
    raise C3MechHeaderError(
        "C3Mech header template contains a nonprinting character")
  fields = Counter(_FIELD_PATTERN.findall(template))
  if fields != _EXPECTED_FIELDS:
    missing = sorted((_EXPECTED_FIELDS - fields).elements())
    additional = sorted((fields - _EXPECTED_FIELDS).elements())
    details = []
    if missing:
      details.append("missing fields: " + ", ".join(missing))
    if additional:
      details.append("unknown or repeated fields: " +
                     ", ".join(additional))
    raise C3MechHeaderError(
        "C3Mech header template fields are invalid: " + ". ".join(details))
  without_fields = _FIELD_PATTERN.sub("", template)
  if "{{" in without_fields or "}}" in without_fields:
    raise C3MechHeaderError(
        "C3Mech header template contains malformed field syntax")
  for line in template.splitlines():
    for field in _FIELD_PATTERN.findall(line):
      if field in _BLOCK_FIELDS and line != "{{" + field + "}}":
        raise C3MechHeaderError(
            "C3Mech header block field must occupy its own line: " + field)
  return template


def render_c3mech_header(configuration, template_path=HEADER_TEMPLATE_PATH,
                         header_width=HEADER_WIDTH):
  """Render a header from one explicit configuration and template path.

  The template must contain the exact insertion fields defined by this module.
  Consecutive nonblank template lines form one paragraph and are joined with
  spaces before wrapping. Blank lines and block fields end a paragraph. Block
  fields must occupy complete physical lines.
  ``header_width`` is the complete line width including both exclamation marks
  and their adjacent spaces. It must be an integer from 80 through 120. The
  returned string uses LF line endings and ends with one LF. Invalid template
  fields, unreadable templates, content that exceeds the available width,
  combining marks, and Unicode characters classified as wide or full width
  raise ``C3MechHeaderError``. Supported typographic punctuation, protected
  spaces, and decomposable accented characters in header input are converted
  to one ASCII representation. Other non-ASCII characters are rejected.
  """
  content_width = _content_width(header_width)
  template = _read_template(template_path)
  scalar_values = {
      "CONSORTIUM_NAME": configuration.project.consortium_name,
      "CONSORTIUM_ABBREVIATION":
          configuration.project.consortium_abbreviation,
      "INTRODUCTORY_ORGANIZATIONS":
          _render_introductory_organizations(configuration),
      "MODEL_NAME": configuration.model.name,
      "REPOSITORY_SERVICE": (
          "GitHub" if urlparse(
              configuration.project.source_repository_url).hostname ==
          "github.com" else "source"),
      "INFORMATION_ADDRESS": configuration.project.information_url[8:],
  }
  block_values = {
      "SEPARATOR_BLOCK": ["=" * content_width],
      "SOURCE_URL_BLOCK": [configuration.project.source_repository_url],
      "TITLE_BLOCK": [_render_title(configuration, content_width)],
      "CITATIONS_BLOCK": _render_citations(configuration, content_width),
      "WORKING_GROUPS_BLOCK": [
          (" Working Groups For " +
           _ascii_header_prose(configuration.model.name) + " ").center(
              content_width, "=")],
      "AUTHORS_BLOCK": _render_authors(configuration, content_width),
      "WARNING_BLOCK": [
          "!!! Please do not remove this header !!!".center(content_width)],
  }

  if len(configuration.project.source_repository_url) > content_width:
    raise C3MechHeaderError(
        "project.source_repository_url exceeds the available header width")

  output_lines = []
  paragraph_lines = []

  def flush_paragraph():
    if not paragraph_lines:
      return
    paragraph = " ".join(paragraph_lines)
    rendered_paragraph = _FIELD_PATTERN.sub(
        lambda field: scalar_values[field.group(1)], paragraph)
    if "{{INFORMATION_ADDRESS}}" in paragraph:
      marked_paragraph = _FIELD_PATTERN.sub(
          lambda field: (
              _INFORMATION_ADDRESS_MARKER
              if field.group(1) == "INFORMATION_ADDRESS"
              else scalar_values[field.group(1)]),
          paragraph)
      marked_information_word = re.search(
          _WRAP_WORD_PATTERN, marked_paragraph).group(0)
      rendered_information_word = marked_information_word.replace(
          _INFORMATION_ADDRESS_MARKER,
          scalar_values["INFORMATION_ADDRESS"])
      if len(rendered_information_word) > content_width:
        raise C3MechHeaderError(
            "project.information_url exceeds the available header width")
    output_lines.extend(_wrap_paragraph(
        rendered_paragraph, width=content_width))
    paragraph_lines.clear()

  for template_line in template.splitlines():
    match = _FIELD_PATTERN.fullmatch(template_line)
    if match and match.group(1) in _BLOCK_FIELDS:
      flush_paragraph()
      output_lines.extend(block_values[match.group(1)])
      continue

    if not template_line.strip():
      flush_paragraph()
      output_lines.append("")
    else:
      paragraph_lines.append(template_line)
  flush_paragraph()

  return "\n".join(
      _frame(line, content_width=content_width)
      for line in output_lines) + "\n"


def render_minimal_c3mech_header(model_name, model_version,
                                 header_width=HEADER_WIDTH):
  """Render a header for a model not described by the configuration.

  The header contains only the selected model name, selected model version,
  and the warning that the header must not be removed. The returned line
  format and width rules are identical to those used by
  ``render_c3mech_header``. The model name and version must contain only ASCII
  characters.
  """
  for field_name, value in (
      ("model_name", model_name), ("model_version", model_version)):
    if not isinstance(value, str) or not value or value != value.strip():
      raise C3MechHeaderError(
          field_name + " must be a nonempty string without surrounding " +
          "whitespace")
    if not value.isascii():
      raise C3MechHeaderError(field_name + " must contain ASCII only")
  content_width = _content_width(header_width)
  lines = [
      "=" * content_width,
      "",
      model_name.center(content_width),
      model_version.center(content_width),
      "",
      "!!! Please do not remove this header !!!".center(content_width),
      "=" * content_width,
  ]
  return "\n".join(
      _frame(line, content_width=content_width) for line in lines) + "\n"
