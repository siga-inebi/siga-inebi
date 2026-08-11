"""
Domain services for Jornada Diaria y Estados.

RF-JOR-001 lives here: configurable jornada parameters, versioned by
``effective_from`` and never overwritten (AGENTS.md #8, #12). Later phases of
this same app (RF-JOR-002, RF-JOR-003) extend this module instead of putting
their rules in views or serializers.
"""

from apps.academics.models import AcademicCycle
from apps.attendance.models import JornadaParameters
from apps.audit.services import record_event
from apps.common.db import unique_violation_as
from apps.common.models import DomainError


def _require_active(instance, label):
    if not instance.is_active:
        raise DomainError(f"{label} '{instance}' is inactive and cannot be used.")


def set_jornada_parameters(
    *,
    shift,
    academic_cycle,
    entry_limit_time,
    tolerance_minutes,
    closing_time,
    duplicate_suppression_minutes,
    school_days,
    effective_from,
    actor=None,
):
    """
    Register a new version of a jornada's parameters, effective from a date.

    Existing versions are never mutated: a later ``effective_from`` simply
    supersedes them for dates on or after it (RF-JOR-001, and RF-JOR-006
    later).
    """
    _require_active(shift, "Shift")
    _require_active(academic_cycle, "Academic cycle")
    if academic_cycle.institution_id != shift.institution.pk:
        raise DomainError("Shift and academic cycle must belong to the same institution.")

    with unique_violation_as(
        {
            "unique_jornada_parameters_effective_from": (
                "Jornada parameters already exist for this shift, cycle, and effective date."
            )
        }
    ):
        parameters = JornadaParameters.objects.create(
            shift=shift,
            academic_cycle=academic_cycle,
            entry_limit_time=entry_limit_time,
            tolerance_minutes=tolerance_minutes,
            closing_time=closing_time,
            duplicate_suppression_minutes=duplicate_suppression_minutes,
            school_days=school_days,
            effective_from=effective_from,
        )

    record_event(
        actor=actor,
        action="attendance.jornada_parameters.set",
        resource="JornadaParameters",
        resource_identifier=str(parameters.pk),
        context={
            "shift_id": str(shift.public_id),
            "academic_cycle_id": str(academic_cycle.public_id),
            "effective_from": str(effective_from),
        },
    )
    return parameters


def get_effective_parameters(*, shift, academic_cycle, on_date):
    """The parameters in force for ``shift``/``academic_cycle`` on ``on_date``."""
    parameters = (
        JornadaParameters.objects.filter(
            shift=shift,
            academic_cycle=academic_cycle,
            effective_from__lte=on_date,
            is_active=True,
        )
        .order_by("-effective_from")
        .first()
    )
    if parameters is None:
        raise DomainError(
            f"No jornada parameters are configured for shift '{shift}' on {on_date}."
        )
    return parameters


def resolve_academic_cycle_for(*, shift, event_date):
    """The academic cycle covering ``event_date`` for ``shift``'s institution."""
    academic_cycle = AcademicCycle.objects.filter(
        institution_id=shift.institution.pk,
        starts_on__lte=event_date,
        ends_on__gte=event_date,
    ).first()
    if academic_cycle is None:
        raise DomainError(f"No academic cycle covers {event_date} for shift '{shift}'.")
    return academic_cycle
