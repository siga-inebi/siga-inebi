"""
School-year calendar rules for Guatemala.

The ciclo escolar runs inside one calendar year: it opens in the second half of
January and closes at the end of October, which is the shape the MINEDUC
calendar has had for years. Nobody at the establishment wants to look that up
and type two dates to register "Ciclo 2027", and a typo there silently shifts
every date-bounded rule that hangs off the cycle (enrolment validity, teaching
assignments, attendance percentages).

So the dates are DERIVED here and offered as defaults. They stay editable: a
ministerial agreement can move the calendar, and a system that cannot represent
that would be worse than one that guesses well.
"""

from datetime import date, timedelta

# Nominal opening and closing days of the cycle.
OPENING_MONTH = 1
OPENING_DAY = 15
CLOSING_MONTH = 10
CLOSING_DAY = 31

SATURDAY = 5
ONE_DAY = timedelta(days=1)


def _is_weekend(value):
    return value.weekday() >= SATURDAY


def _next_weekday(value):
    """First working day on or after ``value``."""
    while _is_weekend(value):
        value += ONE_DAY
    return value


def _previous_weekday(value):
    """Last working day on or before ``value``."""
    while _is_weekend(value):
        value -= ONE_DAY
    return value


def cycle_start(year):
    """
    Opening date: 15 January, moved FORWARD to the next working day.

    Forward and not backward: classes cannot start before the date the calendar
    declares, so a Saturday the 15th means Monday the 17th.
    """
    return _next_weekday(date(year, OPENING_MONTH, OPENING_DAY))


def cycle_end(year):
    """
    Closing date: 31 October, moved BACKWARD to the previous working day.

    Backward, because the cycle cannot spill into November: the closing date
    bounds the recovery windows and the evaluation units inside it.
    """
    return _previous_weekday(date(year, CLOSING_MONTH, CLOSING_DAY))


def cycle_dates(year):
    """``(starts_on, ends_on)`` for the school year of ``year``."""
    return cycle_start(year), cycle_end(year)


def cycle_name(year):
    """
    Display name derived from the year: "Ciclo 2027".

    Institutions name cycles after their year and nothing else; asking for the
    name separately only creates the chance of a cycle called "Ciclo 2026" whose
    year column says 2027.
    """
    return f"Ciclo {year}"
