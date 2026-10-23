import json
import logging

import pytest

from src.etl import read_csv, transform_customers, transform_orders
from src.main import RAW_DIR, run

CONTACT_CSV = """\
contactid,firstname,lastname,emailaddress1,createdon,statecode
CST-001,Jane,Doe,jane.doe@example.com,2023-01-15T10:30:00Z,0
CST-002,John,Smith,john.smith@domain.com,2023-02-20T14:15:00Z,0
CST-003,Alice,Vance,,2023-03-05T00:00:00Z,1
CST-004,Bob,Ross,bob.ross@paint.org,2023-04-12T08:00:00Z,0
CST-005,Charlie,Brown,charlie@peanuts.com,2023-05-01T12:00:00Z,1
"""

SALES_ORDER_CSV = """\
salesorderid,customerid,totalamount,createdon
ORD-1001,CST-001,250.50,2023-06-01T09:15:00Z
ORD-1002,CST-001,49.99,2023-06-02T11:20:00Z
ORD-1003,CST-002,1200.00,2023-06-03T16:45:00Z
ORD-1004,CST-004,15.75,2023-06-05T18:00:00Z
"""

REJECTED_ORDERS_CSV = """\
tx_id,customer_id,amount_usd,tx_timestamp,reason
ORD-1005,CST-999,99.00,2023-06-06T10:00:00Z,orphan order: customer CST-999 not found in Contact
"""


# --- full run on the mock data from the brief ---


@pytest.fixture
def output(tmp_path):
    run(RAW_DIR, tmp_path / "cdm_lakehouse", tmp_path / "quarantine")
    return tmp_path


def test_contact_csv(output):
    assert (output / "cdm_lakehouse/Contact/Contact.csv").read_text(encoding="utf-8") == CONTACT_CSV


def test_sales_order_csv(output):
    assert (output / "cdm_lakehouse/SalesOrder/SalesOrder.csv").read_text(
        encoding="utf-8"
    ) == SALES_ORDER_CSV


def test_orphan_order_is_quarantined(output):
    assert (output / "quarantine/SalesOrder_rejected.csv").read_text(
        encoding="utf-8"
    ) == REJECTED_ORDERS_CSV


def test_no_customer_is_quarantined(output):
    lines = (output / "quarantine/Contact_rejected.csv").read_text(encoding="utf-8").splitlines()
    assert lines == ["cust_id,full_name,email_addr,signup_date,user_status,reason"]


def test_partitions_point_to_the_written_files(output):
    lakehouse = output / "cdm_lakehouse"
    manifest = json.loads((lakehouse / "model.json").read_text(encoding="utf-8"))
    for entity in manifest["entities"]:
        for partition in entity["partitions"]:
            header = (lakehouse / partition["location"]).read_text(encoding="utf-8").splitlines()[0]
            assert header.split(",") == [attribute["name"] for attribute in entity["attributes"]]


def test_problems_are_logged(tmp_path, caplog):
    caplog.set_level(logging.WARNING)
    run(RAW_DIR, tmp_path / "cdm_lakehouse", tmp_path / "quarantine")
    assert "raw_customers.csv line 7: record was split over two lines" in caplog.text
    assert "customer CST-003: invalid email 'invalid-email-format'" in caplog.text
    assert "record ORD-1005 rejected: orphan order" in caplog.text


# --- reader ---


def write_file(tmp_path, text):
    path = tmp_path / "raw.csv"
    path.write_text(text, encoding="utf-8")
    return path


def test_record_split_over_two_lines_is_joined(tmp_path):
    path = write_file(tmp_path, "a,b,c\n1,x\n,y\n")
    assert read_csv(path, ["a", "b", "c"]) == [{"a": "1", "b": "x ", "c": "y"}]


def test_empty_lines_are_skipped(tmp_path):
    path = write_file(tmp_path, "a,b\n1,2\n\n3,4\n")
    assert read_csv(path, ["a", "b"]) == [{"a": "1", "b": "2"}, {"a": "3", "b": "4"}]


def test_line_with_too_many_fields_is_skipped(tmp_path):
    path = write_file(tmp_path, "a,b\n1,2,3\n4,5\n")
    assert read_csv(path, ["a", "b"]) == [{"a": "4", "b": "5"}]


def test_incomplete_last_record_is_skipped(tmp_path):
    path = write_file(tmp_path, "a,b\n1,2\n3\n")
    assert read_csv(path, ["a", "b"]) == [{"a": "1", "b": "2"}]


def test_file_saved_by_excel_is_read(tmp_path):
    # BOM at the start, Windows line ends, spaces around the column names
    path = tmp_path / "raw.csv"
    path.write_bytes("﻿ a , b \r\n1,2\r\n".encode("utf-8"))
    assert read_csv(path, ["a", "b"]) == [{"a": "1", "b": "2"}]


def test_wrong_header_raises(tmp_path):
    path = write_file(tmp_path, "a,x\n1,2\n")
    with pytest.raises(ValueError, match="expected columns"):
        read_csv(path, ["a", "b"])


# --- rejected rows that the mock data does not have ---


def test_customer_with_unknown_status_is_rejected():
    row = {
        "cust_id": "CST-010",
        "full_name": "Ann Lee",
        "email_addr": "ann@lee.com",
        "signup_date": "2023-01-01",
        "user_status": "pending",
    }
    contacts, rejected = transform_customers([row])
    assert contacts == []
    assert rejected == [{**row, "reason": "unknown user_status 'pending'"}]


def test_order_with_bad_amount_is_rejected():
    row = {
        "tx_id": "ORD-2000",
        "customer_id": "CST-001",
        "amount_usd": "12,50",
        "tx_timestamp": "2023-06-01T09:15:00Z",
    }
    orders, rejected = transform_orders([row], {"CST-001"})
    assert orders == []
    assert rejected[0]["reason"].startswith("totalamount:")
