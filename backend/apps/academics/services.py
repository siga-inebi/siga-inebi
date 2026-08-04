"""
Domain services for the academic catalogue.

The catalogue is the structure enrolments are assigned to:

    Institution
      +-- Campus ("sede")
      |     +-- Shift ("jornada")
      +-- Level ("nivel")            (added in a later PR of this chain)
      +-- AcademicCycle ("ciclo")     (added in a later PR of this chain)

Every invariant lives here, never in views or serializers (AGENTS.md #8).

Uniqueness is delegated to the database constraints and translated back into a
``DomainError`` by ``unique_violation_as``. Reading first and writing afterwards
would leave a window for two concurrent requests to both pass the check.
"""

from django.db import transaction

from apps.academics.models import AcademicCycle, Campus, GradeOffering, Shift
from apps.audit.services import record_event
from apps.common.db import unique_violation_as
from apps.common.models import DomainError

# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _clean_code(value, *, field="code"):
    code = (value or "").strip().upper()
    if not code:
        raise DomainError(f"A non-empty {field} is required.")
    return code


def _clean_name(value, *, field="name"):
    name = (value or "").strip()
    if not name:
        raise DomainError(f"A non-empty {field} is required.")
    return name


def _require_active(instance, label):
    if not instance.is_active:
        raise DomainError(f"{label} '{instance}' is inactive and cannot be used.")


def _has_open_cycle_usage(offering_queryset):
    """True when any of those offerings belongs to a cycle that is not closed."""
    return offering_queryset.exclude(
        academic_cycle__status=AcademicCycle.CycleStatus.CLOSED
    ).exists()


def _audit(actor, action, instance, **context):
    record_event(
        actor=actor,
        action=action,
        resource=type(instance).__name__,
        resource_identifier=str(instance.pk),
        context=context,
    )


def _changed(instance, actor, action, **candidates):
    """
    Apply the fields whose value was actually supplied, persist only those, and
    audit what changed. ``None`` means "not supplied", never "set to null".
    """
    fields = [name for name, value in candidates.items() if value is not None]
    for name in fields:
        setattr(instance, name, candidates[name])

    instance.save(update_fields=[*fields, "updated_at"])
    _audit(actor, action, instance, fields=fields)
    return instance


# --------------------------------------------------------------------------- #
# campuses ("sedes")
# --------------------------------------------------------------------------- #


def _campus_conflicts(code):
    return {
        "unique_campus_code_per_institution": (
            f"Campus code '{code}' already exists for this institution."
        ),
        "unique_main_campus_per_institution": (
            "Another campus was promoted to main at the same time. Retry the operation."
        ),
    }


@transaction.atomic
def create_campus(*, institution, name, code, address="", is_main=False, actor=None):
    """
    Register a campus.

    Rules:
    - Code is normalised to upper case and unique per institution, including
      inactive campuses so history stays readable (ADR-0006).
    - At most one main campus per institution; promoting a new one demotes the
      previous main campus.
    """
    name = _clean_name(name)
    code = _clean_code(code)

    if is_main:
        Campus.objects.filter(institution=institution, is_main=True).update(is_main=False)

    with unique_violation_as(_campus_conflicts(code)):
        campus = Campus.objects.create(
            institution=institution,
            name=name,
            code=code,
            address=(address or "").strip(),
            is_main=is_main,
        )

    _audit(actor, "academics.campus.created", campus, code=code, is_main=is_main)
    return campus


@transaction.atomic
def update_campus(*, campus, name=None, address=None, is_main=None, actor=None):
    """Update the descriptive attributes of a campus. The code is immutable."""
    if name is not None:
        name = _clean_name(name)
    if address is not None:
        address = address.strip()

    if is_main is not None and is_main != campus.is_main and is_main:
        _require_active(campus, "Campus")
        Campus.objects.filter(institution=campus.institution, is_main=True).exclude(
            pk=campus.pk
        ).update(is_main=False)

    # ``is_main=False`` is a real value, so it cannot ride on the None convention.
    fields = {"name": name, "address": address}
    if is_main is not None and is_main != campus.is_main:
        campus.is_main = is_main
        fields["is_main"] = is_main

    with unique_violation_as(_campus_conflicts(campus.code)):
        return _changed(campus, actor, "academics.campus.updated", **fields)


@transaction.atomic
def deactivate_campus(*, campus, actor=None):
    """
    Deactivate a campus instead of deleting it (RF-EST-012).

    Rules:
    - Refused while any of its shifts is used by a cycle that is not closed.
    - Cascades to the campus shifts and clears the main flag.
    - Idempotent.
    """
    if not campus.is_active:
        return campus

    if _has_open_cycle_usage(GradeOffering.objects.filter(shift__campus=campus)):
        raise DomainError(
            f"Campus '{campus.name}' is used by an active cycle and cannot be deactivated."
        )

    campus.is_active = False
    campus.is_main = False
    campus.save(update_fields=["is_active", "is_main", "updated_at"])
    Shift.objects.filter(campus=campus, is_active=True).update(is_active=False)

    _audit(actor, "academics.campus.deactivated", campus, code=campus.code)
    return campus


# --------------------------------------------------------------------------- #
# shifts ("jornadas")
# --------------------------------------------------------------------------- #


def create_shift(*, campus, name, code, actor=None):
    """
    Register a shift for a campus (RF-EST-002).

    Rules:
    - Campus must be active.
    - Code is unique per campus, so two campuses may both have "MAT".
    """
    _require_active(campus, "Campus")
    name = _clean_name(name)
    code = _clean_code(code)

    conflicts = {
        "unique_shift_code_per_campus": (
            f"Shift code '{code}' already exists for campus '{campus.name}'."
        )
    }
    with unique_violation_as(conflicts):
        shift = Shift.objects.create(campus=campus, name=name, code=code)

    _audit(actor, "academics.shift.created", shift, campus_id=campus.pk, code=code)
    return shift


def update_shift(*, shift, name=None, actor=None):
    """Rename a shift. The code is immutable."""
    if name is None:
        return shift
    return _changed(shift, actor, "academics.shift.updated", name=_clean_name(name))


def deactivate_shift(*, shift, actor=None):
    """Deactivate a shift unless a non-closed cycle still offers grades in it."""
    if not shift.is_active:
        return shift

    if _has_open_cycle_usage(GradeOffering.objects.filter(shift=shift)):
        raise DomainError(
            f"Shift '{shift.name}' is used by an active cycle and cannot be deactivated."
        )

    shift.is_active = False
    shift.save(update_fields=["is_active", "updated_at"])
    _audit(actor, "academics.shift.deactivated", shift, code=shift.code)
    return shift
