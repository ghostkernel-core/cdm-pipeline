"""Run the pipeline: raw CSVs -> CDM entities in cdm_lakehouse/ + model.json.

Usage (from the project folder):  python -m src.main
"""

import logging
from pathlib import Path

from src.etl import (
    CUSTOMER_COLUMNS,
    ORDER_COLUMNS,
    read_csv,
    transform_customers,
    transform_orders,
    write_csv,
    write_entity,
)
from src.manifest import location, write_manifest
from src.models import Contact, SalesOrder

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
LAKEHOUSE_DIR = ROOT / "cdm_lakehouse"
QUARANTINE_DIR = ROOT / "quarantine"
LOG_FILE = ROOT / "logs" / "pipeline.log"

log = logging.getLogger(__name__)


def run(
    raw_dir: Path = RAW_DIR,
    lakehouse_dir: Path = LAKEHOUSE_DIR,
    quarantine_dir: Path = QUARANTINE_DIR,
) -> None:
    # Extract
    customers = read_csv(raw_dir / "raw_customers.csv", CUSTOMER_COLUMNS)
    orders = read_csv(raw_dir / "raw_orders.csv", ORDER_COLUMNS)

    # Transform: contacts first, the orders are checked against them
    contacts, rejected_customers = transform_customers(customers)
    contact_ids = {contact.contactid for contact in contacts}
    sales_orders, rejected_orders = transform_orders(orders, contact_ids)

    # Load
    write_entity(lakehouse_dir / location(Contact), Contact, contacts)
    write_entity(lakehouse_dir / location(SalesOrder), SalesOrder, sales_orders)
    write_manifest(lakehouse_dir / "model.json")
    write_csv(
        quarantine_dir / "Contact_rejected.csv", CUSTOMER_COLUMNS + ["reason"], rejected_customers
    )
    write_csv(
        quarantine_dir / "SalesOrder_rejected.csv", ORDER_COLUMNS + ["reason"], rejected_orders
    )

    log.info(
        "Contact: %d read, %d written, %d quarantined",
        len(customers),
        len(contacts),
        len(rejected_customers),
    )
    log.info(
        "SalesOrder: %d read, %d written, %d quarantined",
        len(orders),
        len(sales_orders),
        len(rejected_orders),
    )


def setup_logging() -> None:
    LOG_FILE.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
        ],
    )


if __name__ == "__main__":
    setup_logging()
    run()
