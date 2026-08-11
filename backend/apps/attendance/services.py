"""
Domain services for Jornada Diaria y Estados.

RF-JOR-001 lives here: configurable jornada parameters, versioned by
``effective_from`` and never overwritten (AGENTS.md #8, #12). RF-JOR-002
(daily status derivation) and RF-JOR-003 (precedence between events) extend
this same module instead of putting their rules in views or serializers.
"""

from dataclasses import dataclass
from datetime import datetime

from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone

from apps.academics.models import AcademicCycle
from apps.attendance.models import AttendanceEvent, DayStatus, JornadaParameters
from apps.audit.services import record_event
from apps.common.db import unique_violation_as
from apps.common.models import DomainError

ORIGIN_PRECEDENCE = {
    AttendanceEvent.Origin.SCAN: 0,
    AttendanceEvent.Origin.MANUAL: 1,
    AttendanceEvent.Origin.DECLARED: 2,
}


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
        raise DomainError(f"No jornada parameters are configured for shift '{shift}' on {on_date}.")
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


def record_attendance_event(
    *,
    student,
    shift,
    event_date,
    movement_type,
    origin,
    captured_at,
    transmission=AttendanceEvent.Transmission.INDIVIDUAL,
    actor=None,
):
    """
    Store a new attendance event. Never mutates or replaces an existing one:
    conflicting events for the same student/shift/date/movement all coexist,
    and RF-JOR-003's precedence rule decides which one is used later.
    """
    _require_active(student, "Student")
    _require_active(shift, "Shift")

    event = AttendanceEvent.objects.create(
        student=student,
        shift=shift,
        event_date=event_date,
        movement_type=movement_type,
        origin=origin,
        transmission=transmission,
        captured_at=captured_at,
    )
    record_event(
        actor=actor,
        action="attendance.event.recorded",
        resource="AttendanceEvent",
        resource_identifier=str(event.pk),
        context={
            "student_id": str(student.public_id),
            "shift_id": str(shift.public_id),
            "event_date": str(event_date),
            "movement_type": movement_type,
            "origin": origin,
            "transmission": transmission,
        },
    )
    return event


def resolve_prevailing_event(*, student, shift, event_date, movement_type):
    """
    The event that prevails for a student/shift/date/movement combination
    (RF-JOR-003): scan origin outranks manual, which outranks declared;
    within the same origin, the most recent ``captured_at`` wins. Transmission
    never affects the outcome. Returns ``None`` when nothing matches, and
    never mutates or removes any of the events it considered.
    """
    candidates = AttendanceEvent.objects.filter(
        student=student,
        shift=shift,
        event_date=event_date,
        movement_type=movement_type,
        is_active=True,
    ).annotate(
        _origin_rank=Case(
            *[When(origin=origin, then=Value(rank)) for origin, rank in ORIGIN_PRECEDENCE.items()],
            output_field=IntegerField(),
        )
    )
    return candidates.order_by("_origin_rank", "-captured_at").first()


@dataclass
class DayStatusResult:
    status: str
    entry_event: AttendanceEvent | None
    parameters: JornadaParameters


def derive_day_status(*, student, shift, event_date, as_of=None):
    """
    The student's daily attendance status for a jornada (RF-JOR-002), derived
    from their movement events and the jornada's current parameters. Never
    captured manually, and recalculating it never alters the events it reads.

    Returns ``None`` when there is no entry event yet and the jornada's
    closing time for ``event_date`` hasn't passed as of ``as_of`` — the day
    genuinely has no final status yet.
    """
    as_of = as_of or timezone.now()
    academic_cycle = resolve_academic_cycle_for(shift=shift, event_date=event_date)
    parameters = get_effective_parameters(
        shift=shift, academic_cycle=academic_cycle, on_date=event_date
    )
    entry_event = resolve_prevailing_event(
        student=student,
        shift=shift,
        event_date=event_date,
        movement_type=AttendanceEvent.MovementType.ENTRY,
    )

    if entry_event is not None:
        entry_time = timezone.localtime(entry_event.captured_at).time()
        status = DayStatus.PRESENT if entry_time <= parameters.entry_limit_time else DayStatus.LATE
        return DayStatusResult(status=status, entry_event=entry_event, parameters=parameters)

    closing_datetime = timezone.make_aware(datetime.combine(event_date, parameters.closing_time))
    if as_of >= closing_datetime:
        return DayStatusResult(
            status=DayStatus.ABSENT_PENDING_JUSTIFICATION, entry_event=None, parameters=parameters
        )
    return None
