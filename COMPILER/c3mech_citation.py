"""Render Citation File Format content from one C3Mech configuration."""

import yaml


class C3MechCitationError(ValueError):
  """Fatal error while rendering C3Mech citation content."""
  pass


def _reference_description(references):
  count = len(references)
  noun = ("publications" if all(
      reference.publication_type == "article" for reference in references)
          else "works")
  if count == 1:
    return "the " + noun[:-1]
  if count == 2:
    return "both " + noun
  return "all " + str(count) + " " + noun


def _publication_data(publication):
  data = {
      "type": publication.publication_type,
      "title": publication.cff_title or publication.title,
      "authors": [
          {
              "family-names": author.family_names,
              "given-names": author.given_names,
          }
          for author in publication.authors
      ],
  }
  if publication.publication_type == "article":
    data.update({
        "year": publication.year,
        "journal": publication.journal,
        "volume": publication.volume,
        "doi": publication.doi,
        "url": publication.url,
    })
    if publication.issue is not None:
      data["issue"] = publication.issue
    if publication.article_number is not None:
      data["number"] = publication.article_number
    else:
      data["start"] = publication.start_page
      data["end"] = publication.end_page
  return data


def render_citation_cff(configuration):
  """Return complete Citation File Format 1.2.0 text with terminal LF.

  The preferred citation is selected explicitly for the model's major
  version. References contain the remaining selected model family
  publications, applicable corrigenda, and only the selected minor version's
  publications.
  """
  major = configuration.model.version.split(".")[0]
  major_selection = configuration.citation.major_versions.get(major)
  if major_selection is None:
    raise C3MechCitationError(
        "citation catalog has no model major version " + major)
  publications = configuration.citation.publications
  preferred_id = major_selection.preferred_publication_id
  if preferred_id not in publications:
    raise C3MechCitationError(
        "preferred citation is missing from publication catalog: " +
        preferred_id)
  preferred = publications[preferred_id]
  references = tuple(
      citation for citation in configuration.header_citations
      if citation.identifier != preferred_id)
  message = ("If you use " + configuration.model.name +
             ", cite the publication under preferred-citation")
  if references:
    message += (" and " + _reference_description(references) +
                " under references")
  message += "."
  citation = {
      "cff-version": "1.2.0",
      "message": message,
      "title": configuration.citation.cff_title,
      "version": configuration.model.version,
      "authors": [
          {
              "family-names": author.family_names,
              "given-names": author.given_names,
          }
          for author in preferred.authors
      ],
      "repository-code": configuration.project.source_repository_url,
      "preferred-citation": _publication_data(preferred),
  }
  if references:
    citation["references"] = [
        _publication_data(publication) for publication in references
    ]
  return yaml.safe_dump(
      citation, allow_unicode=True, sort_keys=False, width=1000000)
