from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.models import Contact, SalesOrder


def test_contact_is_written_in_cdm_format():
    contact = Contact(
        contactid="CST-001",
        firstname="Jane",
        lastname="Doe",
        emailaddress1=None,
        createdon=datetime(2023, 1, 15, 10, 30, tzinfo=UTC),
        statecode=0,
    )
    assert contact.model_dump(mode="json") == {
        "contactid": "CST-001",
        "firstname": "Jane",
        "lastname": "Doe",
        "emailaddress1": None,
        "createdon": "2023-01-15T10:30:00Z",
        "statecode": 0,
    }


def test_amount_is_written_with_two_decimals():
    order = SalesOrder(
        salesorderid="ORD-1",
        customerid="CST-001",
        totalamount="1200",
        createdon=datetime(2023, 6, 1, tzinfo=UTC),
    )
    assert order.model_dump(mode="json")["totalamount"] == "1200.00"


@pytest.mark.parametrize("amount", ["abc", "12.345", "NaN"])
def test_bad_amount_is_rejected(amount):
    with pytest.raises(ValidationError):
        SalesOrder(
            salesorderid="ORD-1",
            customerid="CST-001",
            totalamount=amount,
            createdon=datetime(2023, 6, 1, tzinfo=UTC),
        )


def test_empty_id_is_rejected():
    with pytest.raises(ValidationError):
        SalesOrder(
            salesorderid="  ",
            customerid="CST-001",
            totalamount="1.00",
            createdon=datetime(2023, 6, 1, tzinfo=UTC),
        )


def test_field_order_matches_the_brief():
    assert list(Contact.model_fields) == [
        "contactid",
        "firstname",
        "lastname",
        "emailaddress1",
        "createdon",
        "statecode",
    ]
    assert list(SalesOrder.model_fields) == [
        "salesorderid",
        "customerid",
        "totalamount",
        "createdon",
    ]
