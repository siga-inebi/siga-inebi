"""
Domain services for Jornada Diaria y Estados.

RF-JOR-001 lives here: configurable jornada parameters, versioned by
``effective_from`` and never overwritten (AGENTS.md #8, #12). RF-JOR-002
(daily status derivation) and RF-JOR-003 (precedence between events) extend
this same module instead of putting their rules in views or serializers.
RF-JOR-004 (daily closure) reads the enrolment-lifecycle domain to know who
is actively enrolled in a jornada; attendance-governance already depends on
it (see ``docs/architecture/domain-map.md``).

RF-CRE-001 (credential issuance with an opaque identifier) and RF-CRE-006
(resolving that identifier back to a student) live at the bottom of this
module: the credential is what a scan resolves, so it belongs to the same
attendance-capture domain rather than to a module of its own.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Case, IntegerField, Value, When
from django.utils import timezone

from apps.academics.models import AcademicCycle
from apps.attendance.models import (
    AttendanceAlert,
    AttendanceEvent,
    DayStatus,
    JornadaParameters,
    RecalculationReason,
    StudentCredential,
)
from apps.audit.services import record_event
from apps.common.codes import create_with_generated_code
from apps.common.db import unique_violation_as
from apps.common.exceptions import DomainError
from apps.common.opaque import generate_opaque_identifier
from apps.enrolments.models import Enrolment
from apps.enrolments.services import active_enrolments
from apps.students.models import Student

ORIGIN_PRECEDENCE = {
    AttendanceEvent.Origin.SCAN: 0,
    AttendanceEvent.Origin.MANUAL: 1,
    AttendanceEvent.Origin.DECLARED: 2,
}


def _require_active(instance, label):
    if not instance.is_active:
        raise DomainError(f"No se puede usar {label} '{instance}': su registro esta inactivo.")


@transaction.atomic
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
    _require_active(shift, "la jornada")
    _require_active(academic_cycle, "el ciclo escolar")
    if academic_cycle.institution_id != shift.institution.pk:
        raise DomainError("La jornada y el ciclo escolar deben pertenecer a la misma institucion.")

    with unique_violation_as(
        {
            "unique_jornada_parameters_effective_from": (
                "Ya existen parametros para esa jornada, ciclo y fecha de vigencia."
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
        raise DomainError(
            f"La jornada '{shift}' no tiene parametros configurados para el {on_date}."
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
        raise DomainError(f"Ningun ciclo escolar cubre el {event_date} para la jornada '{shift}'.")
    return academic_cycle


@transaction.atomic
def record_attendance_event(
    *,
    student,
    shift,
    event_date,
    movement_type,
    origin,
    captured_at,
    transmission=AttendanceEvent.Transmission.INDIVIDUAL,
    operator=None,
    manual_reason=None,
    actor=None,
):
    """
    Store a new attendance event. Never mutates or replaces an existing one:
    conflicting events for the same student/shift/date/movement all coexist,
    and RF-JOR-003's precedence rule decides which one is used later.

    RF-ASI-012: a manual registration (no scan involved) must name who
    authorized it and why, from the configurable reason catalog -- both
    required here, at the service boundary, not only by the view's
    permission check, for the same defense-in-depth reason RF-ASI-001
    checks the scan operator in ``record_scan_movement`` instead of trusting
    the caller.
    """
    _require_active(student, "el estudiante")
    _require_active(shift, "la jornada")
    if origin == AttendanceEvent.Origin.MANUAL:
        if operator is None:
            raise DomainError("Un registro manual debe identificar quien lo autorizo.")
        if manual_reason is None:
            raise DomainError("Un registro manual debe indicar un motivo de la lista configurable.")
        _require_active(manual_reason, "el motivo")

    event = AttendanceEvent.objects.create(
        student=student,
        shift=shift,
        event_date=event_date,
        movement_type=movement_type,
        origin=origin,
        transmission=transmission,
        captured_at=captured_at,
        operator=operator,
        manual_reason=manual_reason,
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
            **({"operator_id": operator.pk} if operator is not None else {}),
            **(
                {"manual_reason_id": str(manual_reason.public_id)}
                if manual_reason is not None
                else {}
            ),
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


# --------------------------------------------------------------------------- #
# RF-ASI-005 — tipos de movimiento admitidos por punto de control
# --------------------------------------------------------------------------- #


@transaction.atomic
def configure_control_point_movement_types(*, control_point, allows_entry, allows_exit, actor):
    """
    RF-ASI-005: configure which movement types a control point accepts.

    Both flags default to allowed at creation, so this only matters once
    someone narrows a point on purpose (a turnstile that only ever sees
    people leaving, say) -- and that narrowing is what gets audited here,
    not the unconfigured default.
    """
    if not allows_entry and not allows_exit:
        raise DomainError(
            f"El punto de control '{control_point}' debe admitir al menos un tipo de movimiento."
        )
    if actor is None:
        raise DomainError(
            "La configuracion del punto de control debe identificar quien la autorizo."
        )

    control_point.allows_entry = allows_entry
    control_point.allows_exit = allows_exit
    control_point.save(update_fields=["allows_entry", "allows_exit", "updated_at"])
    record_event(
        actor=actor,
        action="attendance.control_point.movement_types_configured",
        resource="ControlPoint",
        resource_identifier=str(control_point.public_id),
        context={"allows_entry": allows_entry, "allows_exit": allows_exit},
    )
    return control_point


# --------------------------------------------------------------------------- #
# RF-ASI-001/002/004/010 — captura por escaneo, supresion de duplicados e
# idempotencia
# --------------------------------------------------------------------------- #


@dataclass
class ScanConfirmation:
    """
    RF-ASI-003: exactly what the operator needs to verify the person in
    front of them is who the scan says -- photo, full name, grade and
    section. Deliberately excludes everything else the student record
    carries (health, grades, family contact, address): those belong to
    the expediente, not to this confirmation screen.
    """

    student: object
    full_name: str
    grade_name: str | None
    section_name: str | None
    photo_url: str | None


@dataclass
class ScanCaptureResult:
    client_event_id: str
    outcome: str  # "created" | "duplicate_suppressed" | "already_processed"
    event: AttendanceEvent
    duplicate_of: AttendanceEvent | None = None
    confirmation: ScanConfirmation | None = None


@dataclass
class RejectedScanItem:
    client_event_id: str
    outcome: str = "rejected"
    reason: str = ""


def resolve_scan_confirmation(*, student, shift, event_date):
    """RF-ASI-003: build the confirmation snapshot for a resolved scan subject."""
    enrolment = _active_enrolment_for(student=student, shift=shift, event_date=event_date)
    grade = enrolment.section.offering.grade if enrolment is not None else None
    return ScanConfirmation(
        student=student,
        full_name=f"{student.person.first_name} {student.person.last_name}".strip(),
        grade_name=grade.name if grade is not None else None,
        section_name=enrolment.section.name if enrolment is not None else None,
        photo_url=student.photo.url if student.photo else None,
    )


@transaction.atomic
def record_scan_movement(
    *,
    student,
    shift,
    control_point,
    movement_type,
    captured_at,
    client_event_id,
    operator,
    batch_id="",
    transmission=AttendanceEvent.Transmission.INDIVIDUAL,
    actor=None,
):
    """
    Register one scanned movement (RF-ASI-002), enforcing:

    - RF-ASI-001: an operator is mandatory. The view already requires an
      authenticated, permissioned actor before this is ever called, but a
      future caller that skips the view (a management command, say) must not
      be able to bypass this — so it's checked here too, not just there.
    - RF-ASI-010: idempotency by client-generated ``client_event_id``. A
      resend of an already-registered id is a no-op that returns the
      original event, never a duplicate or an error.
    - RF-ASI-004: duplicate suppression within the jornada's configured
      window, evaluated on student/shift/date/movement_type alone --
      independent of operator, device or control point. A suppressed
      duplicate is recorded as an auditable rejection, not as a movement.
    """
    if operator is None:
        raise DomainError("Un movimiento por escaneo debe registrarlo un operador autenticado.")

    _require_active(student, "el estudiante")
    _require_active(shift, "la jornada")
    _require_active(control_point, "el punto de control")

    if client_event_id:
        existing = AttendanceEvent.objects.filter(client_event_id=client_event_id).first()
        if existing is not None:
            return ScanCaptureResult(
                client_event_id=client_event_id,
                outcome="already_processed",
                event=existing,
                confirmation=resolve_scan_confirmation(
                    student=student, shift=shift, event_date=existing.event_date
                ),
            )

    if movement_type == AttendanceEvent.MovementType.ENTRY and not control_point.allows_entry:
        raise DomainError(f"El punto de control '{control_point}' no admite ingresos.")
    if movement_type == AttendanceEvent.MovementType.EXIT and not control_point.allows_exit:
        raise DomainError(f"El punto de control '{control_point}' no admite egresos.")

    event_date = timezone.localtime(captured_at).date()
    academic_cycle = resolve_academic_cycle_for(shift=shift, event_date=event_date)
    parameters = get_effective_parameters(
        shift=shift, academic_cycle=academic_cycle, on_date=event_date
    )
    suppression_window = timedelta(minutes=parameters.duplicate_suppression_minutes)

    duplicate = (
        AttendanceEvent.objects.filter(
            student=student,
            shift=shift,
            event_date=event_date,
            movement_type=movement_type,
            is_active=True,
            captured_at__gte=captured_at - suppression_window,
            captured_at__lte=captured_at + suppression_window,
        )
        .order_by("-captured_at")
        .first()
    )
    if duplicate is not None:
        record_event(
            actor=operator,
            action="attendance.event.rejected_duplicate",
            resource="AttendanceEvent",
            resource_identifier=str(duplicate.pk),
            context={
                "student_id": str(student.public_id),
                "shift_id": str(shift.public_id),
                "event_date": str(event_date),
                "movement_type": movement_type,
                "existing_captured_at": duplicate.captured_at.isoformat(),
                "client_event_id": client_event_id,
            },
        )
        return ScanCaptureResult(
            client_event_id=client_event_id,
            outcome="duplicate_suppressed",
            event=duplicate,
            duplicate_of=duplicate,
            confirmation=resolve_scan_confirmation(
                student=student, shift=shift, event_date=event_date
            ),
        )

    with unique_violation_as(
        {
            "unique_attendance_event_client_event_id": (
                "Ese client_event_id ya se uso para otro movimiento."
            )
        }
    ):
        event = AttendanceEvent.objects.create(
            student=student,
            shift=shift,
            event_date=event_date,
            movement_type=movement_type,
            origin=AttendanceEvent.Origin.SCAN,
            transmission=transmission,
            captured_at=captured_at,
            control_point=control_point,
            operator=operator,
            client_event_id=client_event_id,
            batch_id=batch_id,
        )

    record_event(
        actor=actor or operator,
        action="attendance.event.recorded",
        resource="AttendanceEvent",
        resource_identifier=str(event.pk),
        context={
            "student_id": str(student.public_id),
            "shift_id": str(shift.public_id),
            "event_date": str(event_date),
            "movement_type": movement_type,
            "origin": AttendanceEvent.Origin.SCAN,
            "transmission": transmission,
            "control_point_id": str(control_point.public_id),
            "client_event_id": client_event_id,
            "batch_id": batch_id,
        },
    )
    if event_date < timezone.localdate():
        recalculate_day(
            student=student,
            shift=shift,
            event_date=event_date,
            reason=RecalculationReason.LATE_EVENT,
            actor=actor or operator,
        )
    return ScanCaptureResult(
        client_event_id=client_event_id,
        outcome="created",
        event=event,
        confirmation=resolve_scan_confirmation(student=student, shift=shift, event_date=event_date),
    )


def record_scan_batch(*, items, operator, actor=None):
    """
    RF-ASI-010's batch form: process each already-resolved item through
    ``record_scan_movement`` independently, so one rejected item (an
    inactive student, say) never aborts the rest of the batch. Returns
    results in the same order as ``items``.
    """
    results = []
    for item in items:
        try:
            results.append(record_scan_movement(operator=operator, actor=actor, **item))
        except DomainError as exc:
            results.append(
                RejectedScanItem(client_event_id=item.get("client_event_id", ""), reason=str(exc))
            )
    return results


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


def resolve_prevailing_events(*, students, shift, event_dates, movement_type):
    """
    Batched ``resolve_prevailing_event``: the prevailing event of one
    movement type for many students across many days, in a single query.

    Returns ``{(student.pk, event_date): AttendanceEvent}``, leaving out the
    pairs that have no matching event at all.
    """
    students = list(students)
    event_dates = list(event_dates)
    if not students or not event_dates:
        return {}

    # One pass over the globally ordered candidates: the first row seen for a
    # (student, day) group is that group's prevailing event, because the
    # ordering is exactly the one ``resolve_prevailing_event`` applies per
    # pair — scan over manual over declared, then the most recent capture.
    candidates = (
        AttendanceEvent.objects.filter(
            student__in=students,
            shift=shift,
            event_date__in=event_dates,
            movement_type=movement_type,
            is_active=True,
        )
        .annotate(
            _origin_rank=Case(
                *[
                    When(origin=origin, then=Value(rank))
                    for origin, rank in ORIGIN_PRECEDENCE.items()
                ],
                output_field=IntegerField(),
            )
        )
        .order_by("_origin_rank", "-captured_at")
    )
    prevailing = {}
    for event in candidates:
        prevailing.setdefault((event.student_id, event.event_date), event)
    return prevailing


@dataclass
class DayStatusResult:
    status: str
    entry_event: AttendanceEvent | None
    parameters: JornadaParameters


def _classify_day(*, entry_event, parameters, event_date, as_of):
    """
    RF-JOR-002's classification rule, applied to an already-resolved
    prevailing entry event and the parameters in force. Kept apart so the
    single-pair and batched readers below can never drift apart.
    """
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
    return _classify_day(
        entry_event=entry_event, parameters=parameters, event_date=event_date, as_of=as_of
    )


def derive_day_statuses(*, students, shift, event_dates, as_of=None):
    """
    Batched ``derive_day_status`` over a set of students and a set of days —
    same RF-JOR-002 rules, same results, same ``None`` meaning.

    A caller that needs a whole roster across a whole window (RF-JOR-007's
    "ausencias frecuentes" evaluation, for one) would otherwise pay three
    queries per (student, day) pair, which grows as the product of both. Here
    the prevailing entries resolve in a single query and each cycle's
    parameter versions load once, so the cost no longer depends on the size
    of the roster or the length of the window.

    Returns ``{(student.pk, event_date): DayStatusResult | None}``.
    """
    as_of = as_of or timezone.now()
    students = list(students)
    event_dates = list(dict.fromkeys(event_dates))
    if not students or not event_dates:
        return {}

    resolved_cycles = []
    versions_by_cycle = {}
    parameters_by_date = {}
    for event_date in event_dates:
        academic_cycle = next(
            (cycle for cycle in resolved_cycles if cycle.starts_on <= event_date <= cycle.ends_on),
            None,
        )
        if academic_cycle is None:
            academic_cycle = resolve_academic_cycle_for(shift=shift, event_date=event_date)
            resolved_cycles.append(academic_cycle)
        if academic_cycle.pk not in versions_by_cycle:
            versions_by_cycle[academic_cycle.pk] = list(
                JornadaParameters.objects.filter(
                    shift=shift, academic_cycle=academic_cycle, is_active=True
                ).order_by("-effective_from")
            )
        # Same vigencia rule as ``get_effective_parameters``: the newest
        # version already in force on the day, picked from the versions
        # loaded once per cycle rather than re-queried per day.
        parameters = next(
            (
                version
                for version in versions_by_cycle[academic_cycle.pk]
                if version.effective_from <= event_date
            ),
            None,
        )
        if parameters is None:
            raise DomainError(
                f"La jornada '{shift}' no tiene parametros configurados para el {event_date}."
            )
        parameters_by_date[event_date] = parameters

    prevailing_entries = resolve_prevailing_events(
        students=students,
        shift=shift,
        event_dates=event_dates,
        movement_type=AttendanceEvent.MovementType.ENTRY,
    )

    return {
        (student.pk, event_date): _classify_day(
            entry_event=prevailing_entries.get((student.pk, event_date)),
            parameters=parameters_by_date[event_date],
            event_date=event_date,
            as_of=as_of,
        )
        for student in students
        for event_date in event_dates
    }


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
    _require_active(shift, "la jornada")
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


@transaction.atomic
def recalculate_day(*, student, shift, event_date, reason, as_of=None, actor=None):
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
    as_of = as_of or timezone.now()
    result = derive_day_status(student=student, shift=shift, event_date=event_date, as_of=as_of)
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
    # "Sin cierre" only means anything once the jornada's closing time has
    # gone by: before that, an entry with no exit yet is simply a student
    # still inside. ``close_jornada`` gets this for free by running at
    # closing time; a recalculation can land on a day still in progress, so
    # it has to check.
    closure_has_passed = result is not None and as_of >= timezone.make_aware(
        datetime.combine(event_date, result.parameters.closing_time)
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
    if permanence_without_closure and closure_has_passed and not active_permanence_alerts:
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


@transaction.atomic
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
        if isinstance(alert_type, list | tuple | set):
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


def list_roster_day_statuses(
    *, shift, event_date, as_of=None, grade=None, section=None, students=None
):
    """
    The derived status of every actively enrolled student of ``shift`` on
    ``event_date`` (a read RF-JOR-007 consumes to evaluate absence alerts, and
    RF-JOR-008's presence query narrows with ``grade``/``section``/``students``).
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
    )
    if grade is not None:
        enrolments = enrolments.filter(section__offering__grade=grade)
    if section is not None:
        enrolments = enrolments.filter(section=section)
    if students is not None:
        enrolments = enrolments.filter(student__in=students)
    enrolments = list(enrolments.select_related("student", "section"))
    students = [enrolment.student for enrolment in enrolments]

    # Two batched reads for the whole roster instead of two per student: a
    # jornada's roster is the size of a school, and this read backs an
    # endpoint.
    results = derive_day_statuses(
        students=students, shift=shift, event_dates=[event_date], as_of=as_of
    )
    exit_events = resolve_prevailing_events(
        students=students,
        shift=shift,
        event_dates=[event_date],
        movement_type=AttendanceEvent.MovementType.EXIT,
    )

    statuses = []
    for enrolment in enrolments:
        student = enrolment.student
        result = results.get((student.pk, event_date))
        statuses.append(
            RosterDayStatus(
                student=student,
                section=enrolment.section,
                status=result.status if result is not None else None,
                entry_event=result.entry_event if result is not None else None,
                exit_event=exit_events.get((student.pk, event_date)),
                parameters=parameters,
            )
        )
    return statuses


# --------------------------------------------------------------------------- #
# RF-JOR-008/009 — presencia en tiempo real y porcentaje de asistencia
# --------------------------------------------------------------------------- #


def list_present_students(
    *, shift, event_date=None, grade=None, section=None, students=None, as_of=None
):
    """
    Actively enrolled students of ``shift`` who have an entry registered and
    no exit yet, as of right now (RF-JOR-008). A pure filter over
    ``list_roster_day_statuses``: no new query shape, no side effects.
    """
    event_date = event_date or timezone.localdate()
    roster = list_roster_day_statuses(
        shift=shift,
        event_date=event_date,
        as_of=as_of,
        grade=grade,
        section=section,
        students=students,
    )
    return [entry for entry in roster if entry.entry_event is not None and entry.exit_event is None]


ATTENDANCE_PERCENTAGE_REGULATORY_NOTICE = (
    "Este porcentaje es un indicador informativo derivado de los movimientos "
    "registrados; no sustituye los criterios reglamentarios oficiales para "
    "evaluar la asistencia del estudiante."
)


@dataclass
class AttendancePercentageResult:
    student: object
    shift: object
    academic_cycle: AcademicCycle
    as_of_date: object
    elapsed_school_days: int
    present_days: int
    late_days: int
    percentage: float | None
    regulatory_notice: str = ATTENDANCE_PERCENTAGE_REGULATORY_NOTICE


def compute_attendance_percentage(*, student, shift, as_of_date=None):
    """
    RF-JOR-009: the share of elapsed school days, since the student's active
    enrolment began, that resolved to present or late. A day still in
    progress (no closure yet, no final status) doesn't count in either the
    numerator or the denominator. Nothing here is persisted — like
    ``DayStatus``, this is recomputed from events and parameters every time.

    RF-JOR-011: every result — including the empty ones below, where there is
    nothing yet to report — carries ``regulatory_notice`` so a consumer that
    renders this into a report can never drop the disclaimer by only handling
    the "has a number" branch.
    """
    as_of_date = as_of_date or timezone.localdate()
    academic_cycle = resolve_academic_cycle_for(shift=shift, event_date=as_of_date)
    enrolment = (
        Enrolment.objects.filter(
            student=student,
            academic_cycle=academic_cycle,
            status=Enrolment.EnrolmentStatus.ACTIVE,
            section__offering__shift=shift,
        )
        .order_by("-effective_on")
        .first()
    )
    if enrolment is None:
        raise DomainError(
            f"El estudiante '{student}' no tiene inscripcion activa en la jornada "
            f"'{shift}' para el ciclo que cubre el {as_of_date}."
        )

    start_date = max(academic_cycle.starts_on, enrolment.effective_on)
    empty_result = AttendancePercentageResult(
        student=student,
        shift=shift,
        academic_cycle=academic_cycle,
        as_of_date=as_of_date,
        elapsed_school_days=0,
        present_days=0,
        late_days=0,
        percentage=None,
    )
    if start_date > as_of_date:
        return empty_result

    versions = list(
        JornadaParameters.objects.filter(
            shift=shift, academic_cycle=academic_cycle, is_active=True
        ).order_by("-effective_from")
    )

    def school_days_as_of(candidate_date):
        version = next((v for v in versions if v.effective_from <= candidate_date), None)
        return version.school_days if version is not None else None

    qualifying_dates = []
    current = start_date
    while current <= as_of_date:
        school_days = school_days_as_of(current)
        if school_days is not None and current.isoweekday() in school_days:
            qualifying_dates.append(current)
        current += timedelta(days=1)

    if not qualifying_dates:
        return empty_result

    results = derive_day_statuses(
        students=[student], shift=shift, event_dates=qualifying_dates, as_of=timezone.now()
    )
    resolved = [
        results.get((student.pk, event_date))
        for event_date in qualifying_dates
        if results.get((student.pk, event_date)) is not None
    ]
    present_days = sum(1 for result in resolved if result.status == DayStatus.PRESENT)
    late_days = sum(1 for result in resolved if result.status == DayStatus.LATE)
    elapsed_school_days = len(resolved)
    percentage = (
        round((present_days + late_days) / elapsed_school_days * 100, 2)
        if elapsed_school_days
        else None
    )
    return AttendancePercentageResult(
        student=student,
        shift=shift,
        academic_cycle=academic_cycle,
        as_of_date=as_of_date,
        elapsed_school_days=elapsed_school_days,
        present_days=present_days,
        late_days=late_days,
        percentage=percentage,
    )


# --------------------------------------------------------------------------- #
# RF-CRE-001 — emision de credencial con identificador opaco
# --------------------------------------------------------------------------- #


def _is_enrolled(student):
    """
    Whether ``student`` currently holds an active enrolment.

    A predicate rather than a guard because the three callers owe the user
    different messages: the credential paths must not name the bearer
    (RF-CRE-006 forbids revealing a student on rejection), while the
    student-code path may echo back the code the caller already supplied.
    Sharing the rule and not the wording keeps one definition of "enrolled"
    without leaking through the one door that has to stay shut.
    """
    return active_enrolments(student=student).exists()


@transaction.atomic
def issue_credential(
    *,
    student,
    actor=None,
    issued_at=None,
    generate_identifier=generate_opaque_identifier,
):
    """
    Issue a credential for ``student`` and return it.

    ``generate_identifier`` is injected rather than called through a module
    global so a test can pin the token it asserts on, and so a future policy
    change (different length, different alphabet) does not have to reach into
    this function. Collisions are resolved by the unique constraint and a
    retry, never by reading before writing: two concurrent issuances would both
    pass a pre-check and the loser would surface as a 500.

    Only an actively enrolled student gets one: a credential is what opens a
    movement, and issuing one to somebody who is not enrolled would create a
    usable pass with no jornada behind it.
    """
    _require_active(student, "el estudiante")
    if not _is_enrolled(student):
        raise DomainError(
            f"El estudiante '{student}' no tiene inscripcion activa, asi que no se le puede "
            "emitir credencial."
        )
    issued_at = issued_at or timezone.now()

    def build(identifier):
        return StudentCredential.objects.create(
            student=student,
            opaque_identifier=identifier,
            status=StudentCredential.Status.ACTIVE,
            issued_at=issued_at,
        )

    with unique_violation_as(
        {"unique_active_student_credential": "El estudiante ya tiene una credencial vigente."}
    ):
        credential = create_with_generated_code(
            build=build,
            generate=generate_identifier,
            constraint="unique_credential_opaque_identifier",
        )

    # The identifier itself is deliberately absent from the audit context: the
    # trail records that a credential was issued and to whom, not the token,
    # which is the one secret the QR carries.
    record_event(
        actor=actor,
        action="attendance.credential.issued",
        resource="StudentCredential",
        resource_identifier=str(credential.public_id),
        context={
            "student_id": str(student.public_id),
            "issued_at": issued_at.isoformat(),
        },
    )
    return credential


# --------------------------------------------------------------------------- #
# RF-CRE-002 — contenido visible de la credencial
# --------------------------------------------------------------------------- #


@dataclass
class CredentialPrintContent:
    """
    RF-CRE-002: exactly what the printed/digital credential material shows --
    name, photo, grade, section, academic cycle and institution. Deliberately
    excludes everything else the student record carries (health, address,
    family contact), same boundary ``ScanConfirmation`` draws for the
    scan-confirmation screen (RF-ASI-003) -- a different requirement with a
    different field list, so it gets its own dataclass rather than reusing
    that one.
    """

    student: object
    full_name: str
    grade_name: str
    section_name: str
    academic_cycle_name: str
    institution_name: str
    photo_url: str | None


def resolve_credential_print_content(*, student):
    """RF-CRE-002: build the printable material for a student's active credential."""
    credential = StudentCredential.objects.filter(
        student=student, status=StudentCredential.Status.ACTIVE, is_active=True
    ).first()
    if credential is None:
        raise DomainError(f"El estudiante '{student}' no tiene una credencial vigente.")

    enrolment = active_enrolments(student=student).first()
    if enrolment is None:
        raise DomainError(f"El estudiante '{student}' no tiene inscripcion activa.")

    return CredentialPrintContent(
        student=student,
        full_name=f"{student.person.first_name} {student.person.last_name}".strip(),
        grade_name=enrolment.grade.name,
        section_name=enrolment.section.name,
        academic_cycle_name=enrolment.academic_cycle.name,
        institution_name=enrolment.academic_cycle.institution.name,
        photo_url=student.photo.url if student.photo else None,
    )


# --------------------------------------------------------------------------- #
# RF-CRE-003 — vigencia y revocacion
# --------------------------------------------------------------------------- #


@transaction.atomic
def revoke_credential(*, student, reason, actor):
    """RF-CRE-003: revoke the active credential without deleting its history."""
    if not reason:
        raise DomainError("La revocacion debe indicar un motivo.")
    if actor is None:
        raise DomainError("La revocacion debe identificar quien la autorizo.")

    credential = StudentCredential.objects.filter(
        student=student, status=StudentCredential.Status.ACTIVE, is_active=True
    ).first()
    if credential is None:
        raise DomainError(f"El estudiante '{student}' no tiene una credencial vigente.")

    credential.status = StudentCredential.Status.REVOKED
    credential.revocation_reason = reason
    credential.revoked_by = actor
    credential.save(update_fields=["status", "revocation_reason", "revoked_by", "updated_at"])
    record_event(
        actor=actor,
        action="attendance.credential.revoked",
        resource="StudentCredential",
        resource_identifier=str(credential.public_id),
        context={"student_id": str(student.public_id), "reason": reason},
    )
    return credential


def revoke_credential_for_closed_permanence(*, student, withdrawal_reason, effective_on, actor):
    credential = StudentCredential.objects.filter(
        student=student,
        status=StudentCredential.Status.ACTIVE,
        is_active=True,
    ).first()
    if credential is None:
        return None
    if actor is None:
        raise DomainError("El retiro debe identificar quien autorizo el cierre de acceso.")

    credential.status = StudentCredential.Status.REVOKED
    credential.revocation_reason = "Cierre de permanencia"
    credential.revoked_by = actor
    credential.save(update_fields=["status", "revocation_reason", "revoked_by", "updated_at"])
    record_event(
        actor=actor,
        action="attendance.credential.revoked_on_permanence_close",
        resource="StudentCredential",
        resource_identifier=str(credential.public_id),
        context={
            "student_id": str(student.public_id),
            "effective_on": effective_on.isoformat(),
            "withdrawal_reason_recorded": bool(withdrawal_reason),
        },
    )
    return credential


# --------------------------------------------------------------------------- #
# RF-CRE-006 — resolucion de identificador
# --------------------------------------------------------------------------- #


@dataclass
class CredentialResolution:
    credential: StudentCredential
    student: object
    enrolment: object


def _audit_scan_rejection(*, actor, reason, resource, resource_identifier="", student=None):
    """
    RNF-SEG-003: every rejected scan/resolution attempt is auditable, even
    though the rejection message itself stays deliberately vague about the
    student (see ``resolve_credential``'s docstring) -- the audit trail is
    internal, not part of the response a caller can probe.
    """
    context = {"result": "denied", "reason": reason}
    if student is not None:
        context["student_id"] = student.pk
    record_event(
        actor=actor,
        action="attendance.credential.resolution_rejected",
        resource=resource,
        resource_identifier=resource_identifier,
        context=context,
    )


def resolve_credential(*, opaque_identifier, actor=None):
    """
    The student behind an opaque identifier (RF-CRE-006).

    Every rejection says why without saying about whom. An unrecognised token
    and a revoked one both answer with a fact about the credential, never with
    a fact about a student, so a stranger holding a token cannot probe the
    endpoint to learn whether it belongs to anybody.

    Resolution is read-only and deliberately says nothing about the jornada:
    whether a movement is admissible at this hour is RF-JOR-001's parameters
    talking, not the credential's.
    """
    credential = (
        StudentCredential.objects.select_related("student", "student__person")
        .filter(opaque_identifier=opaque_identifier)
        .first()
    )
    if credential is None:
        _audit_scan_rejection(
            actor=actor, reason="unrecognized_credential", resource="StudentCredential"
        )
        raise DomainError("La credencial no es reconocida.")
    if credential.status != StudentCredential.Status.ACTIVE or not credential.is_active:
        _audit_scan_rejection(
            actor=actor,
            reason="revoked_credential",
            resource="StudentCredential",
            resource_identifier=str(credential.pk),
            student=credential.student,
        )
        raise DomainError("La credencial fue revocada.")

    enrolment = active_enrolments(student=credential.student).first()
    if enrolment is None:
        _audit_scan_rejection(
            actor=actor,
            reason="no_active_enrolment",
            resource="StudentCredential",
            resource_identifier=str(credential.pk),
            student=credential.student,
        )
        raise DomainError("El portador de la credencial no tiene inscripcion activa.")
    return CredentialResolution(
        credential=credential, student=credential.student, enrolment=enrolment
    )


def resolve_scan_subject(*, credential_identifier="", student_code="", actor=None):
    """
    The student a captured item refers to, whichever way it was identified.

    The credential is the real path (RF-CRE-006). ``student_code`` predates it
    and stays as the fallback the capture screen still offers when a credential
    is unavailable; the note on RF-ASI-002 in the traceability matrix records
    why it exists.

    Both paths raise ``DomainError``, so the batch loop has one failure shape to
    handle instead of one per lookup, and both carry the enrolment rule. They
    did not always: the check used to live only in ``resolve_credential``, where
    RF-CRE-006 declares it, so the same operation was accepted or refused
    depending on how the operator happened to identify the person. Somebody
    withdrawn from the establishment does not register attendance, and by which
    door the scan came in is not a fact about their enrolment.

    The manual and declared origins that go through ``record_attendance_event``
    stay outside this rule on purpose: an authorised operator recording a
    movement by hand for a just-withdrawn student can be a legitimate
    correction of history, and forbidding that is a business decision no
    requirement has taken.
    """
    if credential_identifier:
        return resolve_credential(opaque_identifier=credential_identifier, actor=actor).student
    try:
        student = Student.objects.get(student_code=student_code, is_active=True)
    except Student.DoesNotExist as exc:
        _audit_scan_rejection(actor=actor, reason="unregistered_student_code", resource="Student")
        raise DomainError(f"No existe estudiante con codigo '{student_code}'.") from exc
    if not _is_enrolled(student):
        _audit_scan_rejection(
            actor=actor,
            reason="no_active_enrolment",
            resource="Student",
            resource_identifier=str(student.pk),
            student=student,
        )
        raise DomainError(f"El estudiante con codigo '{student_code}' no tiene inscripcion activa.")
    return student
