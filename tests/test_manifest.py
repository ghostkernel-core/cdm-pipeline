"""Checks for model.json.

modeljsonschema.json is Microsoft's official JSON schema for model.json, copied from
https://github.com/microsoft/CDM/blob/master/docs/schema/modeljsonschema.json
(Microsoft, licensed CC BY 4.0).

reference_model.json is the "Expected model.json Structure Reference" from the task brief.
"""

import json
from pathlib import Path

from jsonschema import Draft7Validator

from src.manifest import build_manifest

TESTS_DIR = Path(__file__).parent


def load(name: str) -> dict:
    return json.loads((TESTS_DIR / name).read_text(encoding="utf-8"))


def test_manifest_matches_the_reference_in_the_brief():
    assert build_manifest() == load("reference_model.json")


def test_manifest_is_valid_against_the_official_schema():
    schema = load("modeljsonschema.json")
    Draft7Validator.check_schema(schema)
    # The schema marks the partition "location" as a URI. The brief uses paths
    # relative to cdm_lakehouse/ (Contact/Contact.csv), so only the structure is
    # checked here, not string formats.
    errors = [error.message for error in Draft7Validator(schema).iter_errors(build_manifest())]
    assert errors == []
