"""Target CDM entities.

Every field carries its CDM data type and description. The CSV headers and
model.json are both built from these classes, so they always match.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, ClassVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

# CDM expects UTC timestamps written as YYYY-MM-DDTHH:MM:SSZ
UtcDateTime = Annotated[
    datetime,
    PlainSerializer(
        lambda value: value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        return_type=str,
    ),
]

# Money stays a Decimal (no float rounding) and is written with 2 decimals
Amount = Annotated[
    Decimal,
    Field(max_digits=18, decimal_places=2),
    PlainSerializer(lambda value: f"{value:.2f}", return_type=str),
]


def cdm_field(data_type: str, description: str, **kwargs):
    return Field(description=description, json_schema_extra={"cdm_data_type": data_type}, **kwargs)


class Contact(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    cdm_description: ClassVar[str] = "Standard CDM Contact entity for individual customers"

    contactid: str = cdm_field("string", "Unique primary key for the contact", min_length=1)
    firstname: str | None = cdm_field("string", "First name of the contact")
    lastname: str | None = cdm_field("string", "Last name of the contact")
    emailaddress1: str | None = cdm_field("string", "Primary email address")
    createdon: UtcDateTime = cdm_field("dateTime", "ISO 8601 creation timestamp")
    statecode: int = cdm_field("int64", "Status code: 0 for Active, 1 for Inactive")


class SalesOrder(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    cdm_description: ClassVar[str] = "Standard CDM SalesOrder entity for transactions"

    salesorderid: str = cdm_field("string", "Unique order identifier", min_length=1)
    customerid: str = cdm_field("string", "Foreign key reference to Contact", min_length=1)
    totalamount: Amount = cdm_field("decimal", "Total order amount in USD")
    createdon: UtcDateTime = cdm_field("dateTime", "ISO 8601 transaction timestamp")
