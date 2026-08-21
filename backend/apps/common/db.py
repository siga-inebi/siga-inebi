"""
Database-level guards shared by the domain services.

Uniqueness is enforced by the database, not by a read followed by a write:
checking first and inserting afterwards leaves a window where two concurrent
requests both pass the check and the loser crashes with an ``IntegrityError``
(HTTP 500) instead of the ``DomainError`` the API promises.
"""

from contextlib import contextmanager

from django.db import IntegrityError, transaction

from apps.common.exceptions import DomainError


def constraint_name(exc):
    """Name of the violated constraint, when the driver reports one."""
    diagnostics = getattr(exc.__cause__, "diag", None)
    return getattr(diagnostics, "constraint_name", None)


@contextmanager
def unique_violation_as(messages):
    """
    Translate a unique-constraint violation into a ``DomainError``.

    ``messages`` maps constraint name to the message the API should return.
    A violation that is not in the map is re-raised: an unexpected constraint
    is a bug, and hiding it behind a 400 would make it invisible.

    The body runs in a savepoint so the surrounding transaction stays usable
    after the rollback.
    """
    try:
        with transaction.atomic():
            yield
    except IntegrityError as exc:
        message = messages.get(constraint_name(exc))
        if message is None:
            raise
        raise DomainError(message) from exc
