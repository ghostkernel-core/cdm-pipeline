from datetime import UTC, datetime

import pytest

from src.cleaning import clean_email, map_status, parse_timestamp, split_name


def utc(*args):
    return datetime(*args, tzinfo=UTC)


# --- timestamps ---


def test_timestamp_with_z_stays_the_same():
    assert parse_timestamp("2023-01-15T10:30:00Z") == utc(2023, 1, 15, 10, 30)


def test_timestamp_without_zone_is_utc():
    assert parse_timestamp("2023-02-20 14:15:00") == utc(2023, 2, 20, 14, 15)


def test_date_only_is_midnight_utc():
    assert parse_timestamp("2023-03-05") == utc(2023, 3, 5)


def test_timestamp_with_offset_is_converted():
    assert parse_timestamp("2023-01-15T10:30:00+02:00") == utc(2023, 1, 15, 8, 30)


@pytest.mark.parametrize("value", ["", "   ", "not-a-date", "15/01/2023"])
def test_bad_timestamp_raises(value):
    with pytest.raises(ValueError):
        parse_timestamp(value)


# --- email ---


def test_email_is_lowercased():
    assert clean_email("JOHN.SMITH@DOMAIN.COM") == "john.smith@domain.com"


def test_email_is_trimmed():
    assert clean_email("  jane.doe@example.com ") == "jane.doe@example.com"


@pytest.mark.parametrize("value", ["invalid-email-format", "a@b", "a b@c.com", ""])
def test_invalid_email_returns_none(value):
    assert clean_email(value) is None


# --- names ---


def test_simple_name():
    assert split_name("Jane Doe") == ("Jane", "Doe")


def test_name_with_extra_spaces():
    assert split_name("  Charlie   Brown ") == ("Charlie", "Brown")


def test_name_with_more_than_two_words():
    assert split_name("Vincent van Gogh") == ("Vincent", "van Gogh")


def test_single_word_name():
    assert split_name("Cher") == ("Cher", None)


def test_empty_name():
    assert split_name("   ") == (None, None)


# --- status ---


@pytest.mark.parametrize("value, expected", [("active", 0), ("ACTIVE", 0), (" inactive ", 1)])
def test_status_mapping(value, expected):
    assert map_status(value) == expected


def test_unknown_status_raises():
    with pytest.raises(ValueError, match="unknown user_status"):
        map_status("pending")
