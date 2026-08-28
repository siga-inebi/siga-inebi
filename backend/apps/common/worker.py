"""
RNF-REN-004 — how the worker process is allowed to run.

Two constraints, and they exist for the same reason: the establishment runs
one host, and during the school day that host belongs to the scanning point.
A confirmation there has a 2 s budget (RNF-REN-001), so anything that
competes for CPU or for database connections while the porton is open is
taken out of that budget.

``window_is_open``
    The worker only drains inside a configurable time window, read in the
    establishment's local clock (RNF-LOC-001) because that is the clock the
    school day is written in.

``single_worker_lock``
    Concurrency of one, enforced by a PostgreSQL advisory lock rather than by
    a PID file or by trusting the process manager. The lock lives in the same
    database the jobs do: it cannot be left behind by a killed process, and it
    holds across hosts if the deployment ever grows a second one.
"""

import logging
from contextlib import contextmanager
from datetime import time

from django.db import connection

logger = logging.getLogger(__name__)


class InvalidWindow(ValueError):
    """Raised when a configured window bound is not a ``HH:MM`` time."""


def parse_window_time(value, *, setting):
    """Read a ``HH:MM`` setting into a ``time``, naming the setting if it is not one."""
    try:
        hour, minute = (int(part) for part in str(value).split(":", 1))
        return time(hour=hour, minute=minute)
    except (TypeError, ValueError) as exc:
        raise InvalidWindow(
            f"{setting} debe tener la forma HH:MM en hora local; se recibio '{value}'."
        ) from exc


def window_is_open(now, *, start, end):
    """
    Whether the local time ``now`` falls inside the window ``[start, end)``.

    ``start == end`` means a window with no closing edge — the worker drains
    around the clock. That is the escape hatch for a deployment that has no
    scanning to protect (a migration host, a restore rehearsal), and it is
    spelled as a degenerate window instead of a separate flag so there is only
    one setting to read when something is not draining.

    A window that crosses midnight is the *normal* case here, not an edge one:
    the hours outside a school day are the hours after it ends and before the
    next one starts.
    """
    if start == end:
        return True
    if start < end:
        return start <= now < end
    return now >= start or now < end


@contextmanager
def single_worker_lock(lock_id):
    """
    Yield whether this process is the one allowed to drain the queue.

    The lock is session-scoped, so it is released by the database the moment
    the connection goes away — including when the worker is killed rather than
    stopped. A file-based lock would survive that and lock out every later
    start until someone deleted it by hand.

    On a backend without advisory locks (the SQLite setting used for local
    exploration) the lock is skipped rather than faked: pretending to hold a
    lock that does not exist would make a development run look like a
    production guarantee.
    """
    if connection.vendor != "postgresql":
        logger.warning(
            "El motor '%s' no tiene bloqueos de asesoria: no se puede garantizar "
            "un solo trabajador (RNF-REN-004).",
            connection.vendor,
        )
        yield True
        return

    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [lock_id])
        acquired = bool(cursor.fetchone()[0])
    try:
        yield acquired
    finally:
        if acquired:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [lock_id])
