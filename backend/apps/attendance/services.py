"""
Domain services for Jornada Diaria y Estados.

RF-JOR-001 lives here: configurable jornada parameters, versioned by
``effective_from`` and never overwritten (AGENTS.md #8, #12). RF-JOR-002
(daily status derivation) and RF-JOR-003 (precedence between events) extend
this same module instead of putting their rules in views or serializers.
RF-JOR-004 (daily closure) reads the enrolment-lifecycle domain to know who
is actively enrolled in a jornada; attendance-governance already depends on
it (see ``docs/architecture/domain-map.md``).
"""

from dataclasses import dataclass
from datetime import datetime

from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone

from apps.academics.models import AcademicCycle
from apps.attendance.models import (
    AttendanceAlert,
    AttendanceEvent,
    DayStatus,
    JornadaParameters,
    RecalculationReason,
)
from apps.audit.services import record_event
from apps.common.db import unique_violation_as
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment

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
    recalculate_days_for_parameters_change(
        shift=shift, academic_cycle=academic_cycle, effective_from=effective_from, actor=actor
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
    _flag_declared_exit_without_entry(event=event, actor=actor)
    if event_date < timezone.localdate():
        recalculate_day(
            student=student,
            shift=shift,
            event_date=event_date,
            reason=RecalculationReason.LATE_EVENT,
            actor=actor,
        )
    return event


def _flag_declared_exit_without_entry(*, event, actor):
    """
    RF-JOR-005: a declared exit for a student with no registered entry is a
    contradiction between sources — the declaration asserts the student left
    a jornada they never entered. Both facts stay stored as-is (this never
    touches ``event`` or the missing entry); it only raises an inconsistency
    alert identifying the declaring teacher and section as the conflicting
    source.
    """
    if event.origin != AttendanceEvent.Origin.DECLARED:
        return
    if event.movement_type != AttendanceEvent.MovementType.EXIT:
        return

    entry_event = resolve_prevailing_event(
        student=event.student,
        shift=event.shift,
        event_date=event.event_date,
        movement_type=AttendanceEvent.MovementType.ENTRY,
    )
    if entry_event is not None:
        return

    enrolment = _active_enrolment_for(
        student=event.student, shift=event.shift, event_date=event.event_date
    )
    _raise_alert(
        alert_type=AttendanceAlert.AlertType.INCONSISTENCIA,
        student=event.student,
        shift=event.shift,
        event_date=event.event_date,
        section=enrolment.section if enrolment is not None else None,
        target_roles=[AttendanceAlert.TargetRole.SECTION_COORDINATOR],
        context={
            "declared_event_id": str(event.public_id),
            "declared_by": getattr(actor, "username", "") if actor else "",
            "reason": "declared_exit_without_entry",
        },
        actor=actor,
    )


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


def _active_enrolment_for(*, student, shift, event_date):
    """The student's active enrolment covering ``event_date`` in ``shift``, if any."""
    try:
        academic_cycle = resolve_academic_cycle_for(shift=shift, event_date=event_date)
    except DomainError:
        return None
    return (
        Enrolment.objects.filter(
            student=student,
            academic_cycle=academic_cycle,
            status=Enrolment.EnrolmentStatus.ACTIVE,
            section__offering__shift=shift,
        )
        .select_related("section")
        .first()
    )


def _raise_alert(*, alert_type, student, shift, event_date, section, target_roles, context, actor):
    """
    Record an ``AttendanceAlert``. Alerts are append-only, like events: a
    reevaluation raises a new one instead of mutating a prior alert.
    """
    alert = AttendanceAlert.objects.create(
        alert_type=alert_type,
        student=student,
        shift=shift,
        section=section,
        event_date=event_date,
        target_roles=target_roles,
        context=context,
    )
    record_event(
        actor=actor,
        action="attendance.alert.raised",
        resource="AttendanceAlert",
        resource_identifier=str(alert.pk),
        context={
            "alert_type": alert_type,
            "student_id": str(student.public_id),
            "shift_id": str(shift.public_id),
            "event_date": str(event_date),
            **context,
        },
    )
    return alert


@dataclass
class StudentJornadaClosureStatus:
    student: object
    status: str | None
    entry_event: AttendanceEvent | None
    exit_event: AttendanceEvent | None
    permanence_without_closure: bool


@dataclass
class JornadaClosureResult:
    shift: object
    academic_cycle: AcademicCycle
    event_date: object
    parameters: JornadaParameters
    statuses: list
    alerts: list


def close_jornada(*, shift, event_date, as_of=None, actor=None):
    """
    RF-JOR-004: consolidate the daily status of every actively enrolled
    student of ``shift`` on ``event_date``, identifying who never registered
    an entry and who entered without a matching exit ("permanencia sin
    cierre"). The latter raises an alert for the control point staff and the
    section's coordinator. Never mutates or removes the events it reads.
    """
    _require_active(shift, "Shift")
    academic_cycle = resolve_academic_cycle_for(shift=shift, event_date=event_date)
    parameters = get_effective_parameters(
        shift=shift, academic_cycle=academic_cycle, on_date=event_date
    )
    if as_of is None:
        as_of = timezone.make_aware(datetime.combine(event_date, parameters.closing_time))

    enrolments = Enrolment.objects.filter(
        academic_cycle=academic_cycle,
        status=Enrolment.EnrolmentStatus.ACTIVE,
        section__offering__shift=shift,
        student__is_active=True,
    ).select_related("student", "section")

    statuses = []
    alerts = []
    for enrolment in enrolments:
        student = enrolment.student
        result = derive_day_status(student=student, shift=shift, event_date=event_date, as_of=as_of)
        exit_event = resolve_prevailing_event(
            student=student,
            shift=shift,
            event_date=event_date,
            movement_type=AttendanceEvent.MovementType.EXIT,
        )
        permanence_without_closure = (
            result is not None and result.entry_event is not None and exit_event is None
        )
        if permanence_without_closure:
            alert = _raise_alert(
                alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
                student=student,
                shift=shift,
                event_date=event_date,
                section=enrolment.section,
                target_roles=[
                    AttendanceAlert.TargetRole.CONTROL_POINT,
                    AttendanceAlert.TargetRole.SECTION_COORDINATOR,
                ],
                context={"entry_event_id": str(result.entry_event.public_id)},
                actor=actor,
            )
            alerts.append(alert)
        statuses.append(
            StudentJornadaClosureStatus(
                student=student,
                status=result.status if result is not None else None,
                entry_event=result.entry_event if result is not None else None,
                exit_event=exit_event,
                permanence_without_closure=permanence_without_closure,
            )
        )

    return JornadaClosureResult(
        shift=shift,
        academic_cycle=academic_cycle,
        event_date=event_date,
        parameters=parameters,
        statuses=statuses,
        alerts=alerts,
    )


# --------------------------------------------------------------------------- #
# RF-JOR-006 — recalculo ante cambios
# --------------------------------------------------------------------------- #


def _supersede_alert(*, alert, reason, actor=None):
    """
    Deactivate a persisted alert whose triggering condition no longer holds,
    without touching its content (AGENTS.md #12: corrections add new
    entries, they don't rewrite history) — the alert stays stored and
    queryable, just no longer active.
    """
    alert.is_active = False
    alert.save(update_fields=["is_active", "updated_at"])
    record_event(
        actor=actor,
        action="attendance.alert.superseded",
        resource="AttendanceAlert",
        resource_identifier=str(alert.pk),
        context={
            "alert_type": alert.alert_type,
            "student_id": str(alert.student.public_id),
            "event_date": str(alert.event_date),
            "reason": reason,
        },
    )


@dataclass
class DayRecalculationResult:
    student: object
    shift: object
    event_date: object
    status: str | None
    entry_event: AttendanceEvent | None
    exit_event: AttendanceEvent | None
    superseded_alerts: list
    raised_alerts: list
    reason: str


def recalculate_day(*, student, shift, event_date, reason, actor=None):
    """
    Re-evaluate a student's derived state for one jornada day (RF-JOR-006).

    ``DayStatus`` itself is never persisted (RF-JOR-002), so it is always
    "recalculated" simply by reading it again — this function never writes
    to ``AttendanceEvent``. What can go stale is a previously *persisted*
    alert whose triggering condition no longer holds once a later-arriving
    event or a parameter change is taken into account: a
    ``permanencia_sin_cierre`` alert is superseded once a matching exit
    shows up (or raised if the entry only arrived after closure already
    ran), and an ``inconsistencia`` alert is superseded once a prevailing
    entry resolves the declared exit that caused it. Raising a new
    ``inconsistencia`` alert stays exclusively the job of
    ``_flag_declared_exit_without_entry`` at event-creation time, since
    events are never removed, so a previously-unflagged inconsistency can't
    newly appear here.

    ``reason`` is a ``RecalculationReason`` value used only for the audit
    trail. This is also the entry point a future asistencia-justificaciones
    app should call (with ``reason=RecalculationReason.JUSTIFICATION_RESOLVED``)
    once a justification resolves for a day — nothing here assumes that
    domain exists.
    """
    result = derive_day_status(student=student, shift=shift, event_date=event_date)
    entry_event = result.entry_event if result is not None else None
    exit_event = resolve_prevailing_event(
        student=student,
        shift=shift,
        event_date=event_date,
        movement_type=AttendanceEvent.MovementType.EXIT,
    )

    superseded_alerts = []
    raised_alerts = []

    permanence_without_closure = (
        result is not None and entry_event is not None and exit_event is None
    )
    active_permanence_alerts = list(
        AttendanceAlert.objects.filter(
            student=student,
            shift=shift,
            event_date=event_date,
            alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
            is_active=True,
        )
    )
    if permanence_without_closure and not active_permanence_alerts:
        enrolment = _active_enrolment_for(student=student, shift=shift, event_date=event_date)
        raised_alerts.append(
            _raise_alert(
                alert_type=AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
                student=student,
                shift=shift,
                event_date=event_date,
                section=enrolment.section if enrolment is not None else None,
                target_roles=[
                    AttendanceAlert.TargetRole.CONTROL_POINT,
                    AttendanceAlert.TargetRole.SECTION_COORDINATOR,
                ],
                context={"entry_event_id": str(entry_event.public_id), "reason": reason},
                actor=actor,
            )
        )
    elif not permanence_without_closure and active_permanence_alerts:
        # Every still-active alert of this type gets superseded together: a
        # repeated close_jornada run raises a new one each time by design
        # (append-only), so more than one can be active at once.
        for alert in active_permanence_alerts:
            _supersede_alert(alert=alert, reason=reason, actor=actor)
            superseded_alerts.append(alert)

    active_inconsistencia_alerts = AttendanceAlert.objects.filter(
        student=student,
        shift=shift,
        event_date=event_date,
        alert_type=AttendanceAlert.AlertType.INCONSISTENCIA,
        is_active=True,
    )
    if entry_event is not None:
        for alert in active_inconsistencia_alerts:
            _supersede_alert(alert=alert, reason=reason, actor=actor)
            superseded_alerts.append(alert)

    record_event(
        actor=actor,
        action="attendance.day.recalculated",
        resource="AttendanceEvent",
        resource_identifier=f"{student.pk}:{shift.pk}:{event_date}",
        context={
            "reason": reason,
            "student_id": str(student.public_id),
            "shift_id": str(shift.public_id),
            "event_date": str(event_date),
            "status": result.status if result is not None else None,
            "superseded_alert_ids": [str(alert.pk) for alert in superseded_alerts],
            "raised_alert_ids": [str(alert.pk) for alert in raised_alerts],
        },
    )

    return DayRecalculationResult(
        student=student,
        shift=shift,
        event_date=event_date,
        status=result.status if result is not None else None,
        entry_event=entry_event,
        exit_event=exit_event,
        superseded_alerts=superseded_alerts,
        raised_alerts=raised_alerts,
        reason=reason,
    )


def recalculate_days_for_parameters_change(
    *, shift, academic_cycle, effective_from, actor=None, until_date=None
):
    """
    Reconcile every day that could be affected by a new ``JornadaParameters``
    version (RF-JOR-006): only days on or after ``effective_from`` that
    already have a persisted alert are candidates, since those are the only
    artifacts a parameter change can make stale — a day with no alert has
    nothing to reconcile, and ``derive_day_status`` already reads the
    correct vigente version on its own.
    """
    until_date = until_date or timezone.localdate()
    seen = set()
    results = []
    candidates = AttendanceAlert.objects.filter(
        shift=shift,
        event_date__gte=effective_from,
        event_date__lte=until_date,
        is_active=True,
    ).select_related("student")
    for alert in candidates:
        key = (alert.student_id, alert.event_date)
        if key in seen:
            continue
        seen.add(key)
        results.append(
            recalculate_day(
                student=alert.student,
                shift=shift,
                event_date=alert.event_date,
                reason=RecalculationReason.PARAMETERS_CHANGED,
                actor=actor,
            )
        )
    return results


def list_alerts(*, shift=None, event_date=None, alert_type=None, student=None, is_active=None):
    """
    Read-only alert lookup. Other domains (e.g. RF-JOR-007's
    ``reporting-notifications`` alert surface) consume alerts through this
    function instead of querying ``AttendanceAlert`` directly, per the
    domain-map's "no tablas acopladas sin API interna clara" boundary.
    """
    queryset = AttendanceAlert.objects.select_related("student", "shift", "section")
    if shift is not None:
        queryset = queryset.filter(shift=shift)
    if event_date is not None:
        queryset = queryset.filter(event_date=event_date)
    if alert_type is not None:
        if isinstance(alert_type, (list, tuple, set)):
            queryset = queryset.filter(alert_type__in=alert_type)
        else:
            queryset = queryset.filter(alert_type=alert_type)
    if student is not None:
        queryset = queryset.filter(student=student)
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    return queryset


@dataclass
class RosterDayStatus:
    student: object
    section: object | None
    status: str | None
    entry_event: AttendanceEvent | None
    exit_event: AttendanceEvent | None
    parameters: JornadaParameters


def list_roster_day_statuses(*, shift, event_date, as_of=None):
    """
    The derived status of every actively enrolled student of ``shift`` on
    ``event_date`` (a read RF-JOR-007 consumes to evaluate absence alerts).
    Unlike ``close_jornada``, this is a pure read: no closing-time gating
    beyond what ``derive_day_status`` already applies on its own, and no
    alert side effects.
    """
    academic_cycle = resolve_academic_cycle_for(shift=shift, event_date=event_date)
    parameters = get_effective_parameters(
        shift=shift, academic_cycle=academic_cycle, on_date=event_date
    )
    enrolments = Enrolment.objects.filter(
        academic_cycle=academic_cycle,
        status=Enrolment.EnrolmentStatus.ACTIVE,
        section__offering__shift=shift,
        student__is_active=True,
    ).select_related("student", "section")

    statuses = []
    for enrolment in enrolments:
        student = enrolment.student
        result = derive_day_status(student=student, shift=shift, event_date=event_date, as_of=as_of)
        exit_event = resolve_prevailing_event(
            student=student,
            shift=shift,
            event_date=event_date,
            movement_type=AttendanceEvent.MovementType.EXIT,
        )
        statuses.append(
            RosterDayStatus(
                student=student,
                section=enrolment.section,
                status=result.status if result is not None else None,
                entry_event=result.entry_event if result is not None else None,
                exit_event=exit_event,
                parameters=parameters,
            )
        )
    return statuses
