"""Read-side queries for institutional people."""

from datetime import date

from apps.people.models import Person

MINOR_AGE_YEARS = 18


def people(*, include_inactive=True):
    queryset = Person.objects.select_related(
        "student_profile", "teacher_profile", "guardian_profile", "user_account"
    ).order_by("last_name", "first_name", "id")
    return queryset if include_inactive else queryset.filter(is_active=True)


def is_minor(birth_date, *, as_of=None):
    """
    Whether a person born on ``birth_date`` is under ``MINOR_AGE_YEARS`` as of
    ``as_of`` (today by default). Returns ``None`` when ``birth_date`` is
    unknown, never ``False`` -- unknown must not read as "confirmed adult"
    (RNF-LEG-001).
    """
    if birth_date is None:
        return None
    reference = as_of or date.today()
    had_birthday = (reference.month, reference.day) >= (birth_date.month, birth_date.day)
    age = reference.year - birth_date.year - (0 if had_birthday else 1)
    return age < MINOR_AGE_YEARS
