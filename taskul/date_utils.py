"""Date parsing utilities for flexible date input formats."""
import re
from datetime import date, timedelta


def parse_date(value: str | None) -> str | None:
    """
    Parse a date string in various formats and return YYYY-MM-DD format.

    Supported formats:
    - YYYY-MM-DD
    - YYYY/MM/DD
    - YYYYMMDD
    - MMDD (4 digits) - interpreted as nearest future date

    Returns None if value is None or empty string.
    Raises ValueError if format is invalid.
    """
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None

    # Already in YYYY-MM-DD format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        _validate_date(value)
        return value

    # YYYY/MM/DD format
    if re.match(r"^\d{4}/\d{2}/\d{2}$", value):
        parts = value.split("/")
        result = f"{parts[0]}-{parts[1]}-{parts[2]}"
        _validate_date(result)
        return result

    # YYYYMMDD format (8 digits)
    if re.match(r"^\d{8}$", value):
        result = f"{value[:4]}-{value[4:6]}-{value[6:8]}"
        _validate_date(result)
        return result

    # MMDD format (4 digits) - nearest future date
    if re.match(r"^\d{4}$", value):
        month = int(value[:2])
        day = int(value[2:4])
        return _nearest_future_date(month, day)

    raise ValueError(f"Invalid date format: {value}. Use YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD, or MMDD.")


def _validate_date(date_str: str) -> None:
    """Validate a YYYY-MM-DD date string."""
    try:
        parts = date_str.split("-")
        date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid date: {date_str}") from e


def _nearest_future_date(month: int, day: int) -> str:
    """
    Given month and day, return the nearest future date in YYYY-MM-DD format.
    If today matches, return today.
    """
    if not (1 <= month <= 12):
        raise ValueError(f"Invalid month: {month}")
    if not (1 <= day <= 31):
        raise ValueError(f"Invalid day: {day}")

    today = date.today()
    current_year = today.year

    # Try this year
    try:
        candidate = date(current_year, month, day)
        if candidate >= today:
            return candidate.isoformat()
    except ValueError:
        pass  # Invalid date for this year (e.g., Feb 30)

    # Try next year
    try:
        candidate = date(current_year + 1, month, day)
        return candidate.isoformat()
    except ValueError:
        raise ValueError(f"Invalid date: month={month}, day={day}")
