"""Parsing helpers for values that arrive from the outside world."""

import uuid

from apps.common.models import DomainError


def parse_uuid(value, *, field):
    """
    Turn a query-string value into a UUID.

    Filtering a UUID column with a malformed string raises Django's
    ``ValidationError`` deep inside the ORM and surfaces as a 500, so the value
    is validated before it ever reaches a queryset. Returns ``None`` for an
    absent or empty value, which callers read as "filter not applied".
    """
    if value in (None, ""):
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError) as exc:
        raise DomainError(f"'{value}' is not a valid {field} identifier.") from exc
