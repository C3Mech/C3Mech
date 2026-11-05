"""Format and recognize compiler-generated timestamps."""

import datetime
import re
from collections import Counter
from email.utils import parsedate_to_datetime


TIMESTAMP_FORMAT = "%d/%m/%Y %H:%M:%S"
NORMALIZED_TIMESTAMP = "01/01/1970 00:00:00"
NORMALIZED_CANTERA_DATE = "Thu, 01 Jan 1970 00:00:00 +0000"
FILE_TYPES = ("Kinetics", "Thermodynamic", "Transport")
TIMESTAMP_PATTERN = re.compile(
    r"^(?P<prefix>! | +)(?P<filetype>Kinetics|Thermodynamic|Transport) "
    r"data for (?P<model_name>[^\r\n]+), generated on "
    r"(?P<timestamp>\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})\.$",
    re.MULTILINE)
TIMESTAMP_CANDIDATE_PATTERN = re.compile(
    r"^(?:! ?| +)[^ \r\n]+ data for [^\r\n]+, generated on [^\r\n]*$",
    re.MULTILINE)
CANTERA_GENERATOR_PATTERN = re.compile(r"^generator: (?:ck2yaml|c3mech-lmrr)$", re.MULTILINE)
CANTERA_DATE_PATTERN = re.compile(
    r"^date: (?P<date>[A-Z][a-z]{2}, [0-9]{2} [A-Z][a-z]{2} [0-9]{4} "
    r"[0-9]{2}:[0-9]{2}:[0-9]{2} [+-][0-9]{4})$", re.MULTILINE)
CANTERA_DATE_CANDIDATE_PATTERN = re.compile(r"^date:[^\r\n]*$", re.MULTILINE)


def _recognized_timestamps(text):
  records = []
  for match in TIMESTAMP_PATTERN.finditer(text):
    timestamp = match.group("timestamp")
    datetime.datetime.strptime(timestamp, TIMESTAMP_FORMAT)
    records.append({
        "filetype": match.group("filetype"),
        "model_name": match.group("model_name"),
        "timestamp": timestamp,
    })
  return records


def normalize_generation_timestamps(text, expected_filetypes,
                                    expected_model_name):
  """Replace strictly recognized timestamps after validating their types."""
  expected = Counter(expected_filetypes)
  unknown = set(expected) - set(FILE_TYPES)
  if unknown:
    raise ValueError("unknown expected timestamp type: " +
                     ", ".join(sorted(unknown)))
  candidates = list(TIMESTAMP_CANDIDATE_PATTERN.finditer(text))
  recognized = list(TIMESTAMP_PATTERN.finditer(text))
  if len(candidates) != len(recognized):
    raise ValueError("malformed generation timestamp")
  records = _recognized_timestamps(text)
  observed = Counter(record["filetype"] for record in records)
  if observed != expected:
    raise ValueError("generation timestamp mismatch: expected " +
                     str(dict(expected)) + ", found " + str(dict(observed)))
  unexpected_names = {
      record["model_name"] for record in records
      if record["model_name"] != expected_model_name
  }
  if unexpected_names:
    raise ValueError("generation timestamp model mismatch: expected '" +
                     expected_model_name + "', found " +
                     ", ".join("'" + name + "'"
                               for name in sorted(unexpected_names)))

  def replace_timestamp(match):
    matched_line = match.group(0)
    start = match.start("timestamp") - match.start()
    end = match.end("timestamp") - match.start()
    return matched_line[:start] + NORMALIZED_TIMESTAMP + matched_line[end:]

  return TIMESTAMP_PATTERN.sub(replace_timestamp, text)


def normalize_cantera_generation_date(text):
  """Replace the ck2yaml conversion date with a fixed value."""
  generators = CANTERA_GENERATOR_PATTERN.findall(text)
  if not generators:
    return text
  dates = list(CANTERA_DATE_PATTERN.finditer(text))
  candidates = CANTERA_DATE_CANDIDATE_PATTERN.findall(text)
  if len(generators) != 1 or len(dates) != 1 or len(candidates) != 1:
    raise ValueError("ck2yaml generation date mismatch")
  try:
    parsedate_to_datetime(dates[0].group("date"))
  except (TypeError, ValueError) as error:
    raise ValueError("ck2yaml generation date mismatch") from error
  return CANTERA_DATE_PATTERN.sub(
      "date: " + NORMALIZED_CANTERA_DATE, text)


def normalize_generated_file_bytes(data, expected_filetypes,
                                   expected_model_name):
  """Return strict UTF-8 bytes with stable line endings and timestamps."""
  text = data.decode("utf-8")
  text = text.replace("\r\n", "\n")
  if "\r" in text:
    raise ValueError("isolated carriage return in generated file")
  normalized = normalize_generation_timestamps(
      text, expected_filetypes, expected_model_name)
  normalized = normalize_cantera_generation_date(normalized)
  return normalized.encode("utf-8")


def format_generation_timestamp_line(filetype, model_name, generated_at):
  """Return one timestamp line and verify that normalization recognizes it."""
  if filetype not in FILE_TYPES:
    raise ValueError("unknown timestamp type: " + filetype)
  line = ("! " + filetype + " data for " + model_name + ", generated on " +
          generated_at.strftime(TIMESTAMP_FORMAT) + ".")
  normalized = normalize_generation_timestamps(line, (filetype,), model_name)
  expected = ("! " + filetype + " data for " + model_name +
              ", generated on " + NORMALIZED_TIMESTAMP + ".")
  if normalized != expected:
    raise RuntimeError("generated timestamp line was not normalized exactly")
  return line + "\n\n"
