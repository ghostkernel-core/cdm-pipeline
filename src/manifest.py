"""Build the CDM model.json manifest from the entity models."""

import json
from pathlib import Path
from typing import cast

from src.models import CdmEntity, Contact, SalesOrder

CSV_FORMAT = {"$type": "CsvFormatSettings", "columnHeaders": True, "delimiter": ","}


def location(model: type[CdmEntity]) -> str:
    """Partition file of an entity, relative to the lakehouse folder."""
    name = model.__name__
    return f"{name}/{name}.csv"


def entity(model: type[CdmEntity]) -> dict:
    name = model.__name__
    return {
        "$type": "LocalEntity",
        "name": name,
        "description": model.cdm_description,
        "attributes": [
            {
                "name": field_name,
                # json_schema_extra is the dict that cdm_field() in models.py sets
                "dataType": cast(dict, field.json_schema_extra)["cdm_data_type"],
                "description": field.description,
            }
            for field_name, field in model.model_fields.items()
        ],
        "partitions": [
            {
                "name": f"{name}Partitions",
                "location": location(model),
                "fileFormatSettings": CSV_FORMAT,
            }
        ],
    }


def build_manifest() -> dict:
    return {
        "name": "EnterpriseDataLake",
        "description": "CDM Manifest for Ingested Customer and Sales Data",
        "version": "1.0",
        "entities": [entity(Contact), entity(SalesOrder)],
        "relationships": [
            {
                "$type": "SingleKeyRelationship",
                "name": "Contact_SalesOrder_Relationship",
                "fromAttribute": {"entityName": "SalesOrder", "attributeName": "customerid"},
                "toAttribute": {"entityName": "Contact", "attributeName": "contactid"},
            }
        ],
    }


def write_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_manifest(), indent=2) + "\n", encoding="utf-8", newline="\n")
