"""Format C3Mech configuration values for the species dictionary."""

import unicodedata


AUTHOR_LINE_WIDTH = 85
_LATEX_TEXT_ESCAPES = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_text(text, protect_spaces=False):
  """Return one configuration string escaped for LaTeX document text.

  When protect_spaces is true, Unicode space-separator characters become
  LaTeX nonbreaking spaces.
  """
  output = []
  for character in text:
    if protect_spaces and unicodedata.category(character) == "Zs":
      output.append("~")
    else:
      output.append(_LATEX_TEXT_ESCAPES.get(character, character))
  return "".join(output)


def configured_authors(configuration):
  """Return authors in order with nonbreaking spaces inside each name.

  Author lines are separated by a LaTeX line break and a source newline.
  """
  names = [
      latex_text(author.name, protect_spaces=True)
      for author in configuration.authors
  ]
  lines = []
  line = ""
  for name in names:
    candidate = name if not line else line + ", " + name
    if line and len(candidate) > AUTHOR_LINE_WIDTH:
      lines.append(line)
      line = name
    else:
      line = candidate
  lines.append(line)
  return "\\\\\n".join(lines)


def resolve_identity(name, authors, configuration=None):
  """Use exact custom values, or fill missing values from configuration."""
  if name is not None and authors is not None:
    return name, authors
  if configuration is None:
    raise ValueError(
        "C3Mech configuration is required for species dictionary defaults")
  if name is None:
    name = latex_text(configuration.model.species_dictionary_title)
  if authors is None:
    authors = configured_authors(configuration)
  return name, authors
