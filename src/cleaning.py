"""Cleaning rules for the raw source fields."""

import re
from datetime import UTC, datetime

# Some source timestamps have no time zone. All the others end in Z (UTC),
# so we take the ones without a zone as UTC too.
SOURCE_TZ = UTC

STATUS_CODES = {"active": 0, "inactive": 1}

# Simple check: something@something.something, no spaces.
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def parse_timestamp(value: str) -> datetime:
    """Parse an ISO 8601 date or datetime string and return it in UTC."""
    value = value.strip()
    if not value:
        raise ValueError("timestamp is empty")

    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=SOURCE_TZ)
    return parsed.astimezone(UTC)


def clean_email(value: str) -> str | None:
    """Return the email in lowercase, or None if it is not a valid email."""
    email = value.strip().lower()
    if EMAIL_PATTERN.match(email):
        return email
    return None


def split_name(full_name: str) -> tuple[str | None, str | None]:
    """Split a full name into first name and last name.

    The first word is the first name and the rest is the last name,
    so "Vincent van Gogh" keeps "van Gogh" together.
    """
    parts = full_name.split()
    if not parts:
        return None, None
    first_name = parts[0]
    last_name = " ".join(parts[1:]) or None
    return first_name, last_name


def map_status(value: str) -> int:
    """Map user_status to the CDM statecode (0 = active, 1 = inactive)."""
    status = value.strip().lower()
    if status not in STATUS_CODES:
        raise ValueError(f"unknown user_status '{value}'")
    return STATUS_CODES[status]
