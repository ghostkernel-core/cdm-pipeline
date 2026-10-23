"""Read the raw CSV files, turn them into CDM entities and write the results."""

import csv
import logging
from pathlib import Path

from pydantic import BaseModel, ValidationError

from src.cleaning import clean_email, map_status, parse_timestamp, split_name
from src.models import Contact, SalesOrder

log = logging.getLogger(__name__)

CUSTOMER_COLUMNS = ["cust_id", "full_name", "email_addr", "signup_date", "user_status"]
ORDER_COLUMNS = ["tx_id", "customer_id", "amount_usd", "tx_timestamp"]


def read_csv(path: Path, expected_columns: list[str]) -> list[dict]:
    """Read a raw CSV file into a list of dicts (one per record).

    A record can be cut in two by a line break inside a field, as with
    CST-005 in raw_customers.csv. The first part then has too few fields,
    so we glue it to the next line before using it.
    """
    rows = []
    # utf-8-sig also reads files saved with a BOM (Excel "CSV UTF-8", Notepad)
    with open(path, newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)
        header = [name.strip() for name in next(reader)]
        if header != expected_columns:
            raise ValueError(f"{path.name}: expected columns {expected_columns}, got {header}")

        pending = None  # first part of a record that was cut by a line break
        for fields in reader:
            if not fields:
                continue  # empty line
            if pending:
                # the line break becomes a space, the cleaning rules trim it later
                fields = pending[:-1] + [pending[-1] + " " + fields[0]] + fields[1:]
                log.warning(
                    "%s line %d: record was split over two lines, joined it",
                    path.name,
                    reader.line_num,
                )
                pending = None

            if len(fields) < len(header):
                pending = fields
            elif len(fields) > len(header):
                log.error(
                    "%s line %d: %d fields instead of %d, skipped",
                    path.name,
                    reader.line_num,
                    len(fields),
                    len(header),
                )
            else:
                rows.append(dict(zip(header, fields)))

    if pending:
        log.error("%s: last record is incomplete, skipped", path.name)
    return rows


def transform_customers(rows: list[dict]) -> tuple[list[Contact], list[dict]]:
    """raw_customers rows -> CDM Contact. Returns (contacts, rejected rows)."""
    contacts, rejected = [], []
    for row in rows:
        try:
            email = clean_email(row["email_addr"])
            firstname, lastname = split_name(row["full_name"])
            contact = Contact(
                contactid=row["cust_id"],
                firstname=firstname,
                lastname=lastname,
                emailaddress1=email,
                createdon=parse_timestamp(row["signup_date"]),
                statecode=map_status(row["user_status"]),
            )
        except ValueError as error:
            reject(row, row["cust_id"], error, rejected)
            continue

        if email is None and row["email_addr"].strip():
            log.warning(
                "customer %s: invalid email '%s', set to empty",
                contact.contactid,
                row["email_addr"],
            )
        contacts.append(contact)
    return contacts, rejected


def transform_orders(
    rows: list[dict], contact_ids: set[str]
) -> tuple[list[SalesOrder], list[dict]]:
    """raw_orders rows -> CDM SalesOrder. Orders of unknown customers are rejected."""
    orders, rejected = [], []
    for row in rows:
        try:
            order = SalesOrder(
                salesorderid=row["tx_id"],
                customerid=row["customer_id"],
                totalamount=row["amount_usd"].strip(),
                createdon=parse_timestamp(row["tx_timestamp"]),
            )
            if order.customerid not in contact_ids:
                raise ValueError(f"orphan order: customer {order.customerid} not found in Contact")
        except ValueError as error:
            reject(row, row["tx_id"], error, rejected)
            continue
        orders.append(order)
    return orders, rejected


def reject(row: dict, record_id: str, error: ValueError, rejected: list[dict]) -> None:
    """Keep the raw row as it came in, plus the reason it was rejected."""
    if isinstance(error, ValidationError):
        # Pydantic errors are long; keep one short line per field
        reason = "; ".join(f"{err['loc'][0]}: {err['msg']}" for err in error.errors())
    else:
        reason = str(error)
    log.warning("record %s rejected: %s", record_id, reason)
    rejected.append({**row, "reason": reason})


def write_entity(path: Path, model: type[BaseModel], records: list[BaseModel]) -> None:
    """Write CDM records to CSV, columns in the same order as the model."""
    write_csv(
        path, list(model.model_fields), [record.model_dump(mode="json") for record in records]
    )


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
