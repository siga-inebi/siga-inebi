"""
Sequential institutional codes ("EST-2026-0043", "DOC-007", "BAS1").

Nobody types these by hand well. A code entered manually is either a duplicate
the database rejects after the whole form was filled, or a hole in the series
that nobody notices until someone tries to read the list as a sequence. The
domain services generate the next free one and only fall back to what the
caller supplied.

Generation is a read followed by a write, so two concurrent requests CAN pick
the same code. That race is not prevented here: it is resolved by the unique
constraint plus ``create_with_generated_code``, which regenerates and retries.
Locking the whole table to hand out one code would serialise every enrolment
day for a collision that happens once in a thousand.
"""

import re

from django.db import IntegrityError, transaction

from apps.common.db import constraint_name


def next_sequential_code(*, queryset, field, prefix, width, separator="-"):
    """
    Next free code of the ``<prefix><separator><number>`` series.

    Only rows already in the series are read (the regex filter runs in the
    database), so a code from another series — an imported ministry code, or a
    hand written one — neither shifts the counter nor breaks the scan.

    :param queryset: rows the series must be unique across.
    :param field: name of the column holding the code.
    :param width: zero padding of the numeric part.
    """
    head = f"{prefix}{separator}"
    pattern = rf"^{re.escape(head)}[0-9]+$"
    highest = 0
    for value in queryset.filter(**{f"{field}__regex": pattern}).values_list(field, flat=True):
        highest = max(highest, int(value[len(head) :]))
    return f"{head}{highest + 1:0{width}d}"


def next_suffixed_code(*, queryset, field, prefix):
    """
    Next free code of the ``<prefix><number>`` series, without a separator.

    Grades read better glued to their level ("BAS1", "BAS2") than padded and
    separated, and the level code already carries the meaning.
    """
    pattern = rf"^{re.escape(prefix)}[0-9]+$"
    highest = 0
    for value in queryset.filter(**{f"{field}__regex": pattern}).values_list(field, flat=True):
        highest = max(highest, int(value[len(prefix) :]))
    return f"{prefix}{highest + 1}"


def create_with_generated_code(*, build, generate, constraint, attempts=5):
    """
    Create a record with a generated code, retrying if the code was taken.

    ``build(code)`` performs the insert and ``generate()`` returns a candidate
    code. Only a violation of ``constraint`` is retried: any other integrity
    error is a different bug and hiding it behind a retry loop would turn it
    into a mysterious failure five times slower.

    Each attempt runs in its own savepoint so the surrounding transaction stays
    usable after a rollback.
    """
    for remaining in reversed(range(attempts)):
        try:
            with transaction.atomic():
                return build(generate())
        except IntegrityError as exc:
            if remaining == 0 or constraint_name(exc) != constraint:
                raise
    # Unreachable: the loop either returns or re-raises on its last attempt.
    raise AssertionError("code generation retry loop ended without a result")
