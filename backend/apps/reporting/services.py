"""
Domain services for Alertas de asistencia (RF-JOR-007).

Two of the four alert types this app surfaces are detected upstream, in
apps.attendance (``permanencia_sin_cierre``, ``inconsistencia``): this
module never re-derives that detection logic. It only *projects* attendance's
already-computed alerts through ``sync_attendance_alerts``, reading them via
``apps.attendance.services``' read-only query functions rather than the
``AttendanceAlert`` table directly (domain-map's "no tablas acopladas sin API
interna clara" boundary). The other two (``ausente_sin_registro``,
``frecuencia_ausencias``) are detected here, from the same read-only roster
query.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.attendance import services as attendance_services
from apps.attendance.models import AttendanceAlert, DayStatus
from apps.audit.services import record_event
from apps.common.db import constraint_name, unique_violation_as
from apps.common.models import DomainError
from apps.reporting.models import AbsenceThresholdParameters, Alert

ACTIVE_ALERT_CONSTRAINT = "unique_active_alert_per_student_day_type"


def _require_active(instance, label):
    if not instance.is_active:
        raise DomainError(f"No se puede usar {label} '{instance}': su registro esta inactivo.")


@transaction.atomic
def set_absence_threshold_parameters(
    *, shift, academic_cycle, max_absences, lookback_days, effective_from, actor=None
):
    """
    Register a new version of a shift's "ausencias frecuentes" threshold,
    effective from a date. Existing versions are never mutated: the same
    vigencia idiom as ``attendance.JornadaParameters``.
    """
    _require_active(shift, "la jornada")
    _require_active(academic_cycle, "el ciclo escolar")
    if academic_cycle.institution_id != shift.institution.pk:
        raise DomainError("La jornada y el ciclo escolar deben pertenecer a la misma institucion.")

    with unique_violation_as(
        {
            "unique_absence_threshold_parameters_effective_from": (
                "Ya existen parametros de umbral de ausencias para esa jornada, ciclo "
                "y fecha de vigencia."
            )
        }
    ):
        parameters = AbsenceThresholdParameters.objects.create(
            shift=shift,
            academic_cycle=academic_cycle,
            max_absences=max_absences,
            lookback_days=lookback_days,
            effective_from=effective_from,
        )

    record_event(
        actor=actor,
        action="reporting.absence_threshold.set",
        resource="AbsenceThresholdParameters",
        resource_identifier=str(parameters.pk),
        context={
            "shift_id": str(shift.public_id),
            "academic_cycle_id": str(academic_cycle.public_id),
            "effective_from": str(effective_from),
        },
    )
    return parameters


def get_effective_absence_threshold(*, shift, academic_cycle, on_date):
    """The absence threshold in force for ``shift``/``academic_cycle`` on ``on_date``."""
    parameters = (
        AbsenceThresholdParameters.objects.filter(
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
            f"La jornada '{shift}' no tiene umbral de ausencias configurado para el {on_date}."
        )
    return parameters


def _raise_alert(
    *,
    alert_type,
    student,
    shift,
    event_date,
    section,
    target_roles,
    context,
    source_attendance_alert=None,
    actor=None,
):
    """
    Record an ``Alert``, unless an active one of the same type already
    exists for this student/shift/day. Alerts are append-only like their
    ``attendance`` counterparts, but each evaluation run is idempotent so
    re-running it doesn't pile up duplicates. Returns ``None`` when the
    dedupe guard skips the raise.

    The query below is only a fast path. What actually enforces the rule is
    the partial unique constraint on the model: two evaluations running at
    once would both find nothing and both insert, so the loser is recognised
    by the constraint it violates and skipped just the same.
    """
    if Alert.objects.filter(
        student=student,
        shift=shift,
        event_date=event_date,
        alert_type=alert_type,
        is_active=True,
    ).exists():
        return None

    try:
        with transaction.atomic():
            alert = Alert.objects.create(
                alert_type=alert_type,
                student=student,
                shift=shift,
                section=section,
                event_date=event_date,
                target_roles=target_roles,
                context=context,
                source_attendance_alert=source_attendance_alert,
            )
    except IntegrityError as exc:
        if constraint_name(exc) != ACTIVE_ALERT_CONSTRAINT:
            raise
        return None
    record_event(
        actor=actor,
        action="reporting.alert.raised",
        resource="Alert",
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


def _supersede_alert(*, alert, reason, actor=None):
    """Deactivate a projected alert whose backing condition no longer holds."""
    alert.is_active = False
    alert.save(update_fields=["is_active", "updated_at"])
    record_event(
        actor=actor,
        action="reporting.alert.superseded",
        resource="Alert",
        resource_identifier=str(alert.pk),
        context={
            "alert_type": alert.alert_type,
            "student_id": str(alert.student.public_id),
            "event_date": str(alert.event_date),
            "reason": reason,
        },
    )


@transaction.atomic
def sync_attendance_alerts(*, shift, event_date=None, actor=None):
    """
    Project attendance's own ``permanencia_sin_cierre``/``inconsistencia``
    alerts into this app's alert surface, without re-deriving the conditions
    that raise them. A source alert that has since been superseded in
    ``attendance`` (RF-JOR-006's recalculation) supersedes its local
    projection too, keeping both surfaces consistent.
    """
    created = []
    superseded = []

    source_alerts = attendance_services.list_alerts(
        shift=shift,
        event_date=event_date,
        alert_type=[
            AttendanceAlert.AlertType.PERMANENCIA_SIN_CIERRE,
            AttendanceAlert.AlertType.INCONSISTENCIA,
        ],
    )
    for source_alert in source_alerts:
        if source_alert.is_active:
            alert = _raise_alert(
                alert_type=source_alert.alert_type,
                student=source_alert.student,
                shift=source_alert.shift,
                event_date=source_alert.event_date,
                section=source_alert.section,
                target_roles=source_alert.target_roles,
                context=source_alert.context,
                source_attendance_alert=source_alert,
                actor=actor,
            )
            if alert is not None:
                created.append(alert)
        else:
            for projection in Alert.objects.filter(
                source_attendance_alert=source_alert, is_active=True
            ):
                _supersede_alert(alert=projection, reason="source_superseded", actor=actor)
                superseded.append(projection)

    return created, superseded


@transaction.atomic
def evaluate_absence_alerts(*, shift, event_date, as_of=None, actor=None):
    """
    RF-JOR-007: a student with no registered entry once the jornada's entry
    limit has elapsed gets an ``ausente_sin_registro`` alert for the
    section's coordinator.
    """
    as_of = as_of or timezone.now()
    roster = attendance_services.list_roster_day_statuses(
        shift=shift, event_date=event_date, as_of=as_of
    )
    created = []
    for entry in roster:
        entry_limit_datetime = timezone.make_aware(
            datetime.combine(event_date, entry.parameters.entry_limit_time)
        )
        if entry.entry_event is None and as_of >= entry_limit_datetime:
            alert = _raise_alert(
                alert_type=Alert.AlertType.ABSENCE_NOT_REGISTERED,
                student=entry.student,
                shift=shift,
                event_date=event_date,
                section=entry.section,
                target_roles=[Alert.TargetRole.SECTION_COORDINATOR],
                context={},
                actor=actor,
            )
            if alert is not None:
                created.append(alert)
    return created


@transaction.atomic
def evaluate_frequent_absence_alerts(*, shift, event_date, actor=None):
    """
    RF-JOR-007: a student who accumulates ``max_absences`` (or more)
    ``ausente_pendiente_justificar`` days within the trailing
    ``lookback_days`` school days (per the jornada's ``school_days``, ending
    at ``event_date``) gets a ``frecuencia_ausencias`` alert.
    """
    academic_cycle = attendance_services.resolve_academic_cycle_for(
        shift=shift, event_date=event_date
    )
    try:
        threshold = get_effective_absence_threshold(
            shift=shift, academic_cycle=academic_cycle, on_date=event_date
        )
    except DomainError:
        # Frequent-absence alerting is an opt-in enhancement, not a hard
        # requirement like jornada parameters: no threshold configured for
        # this shift/cycle yet simply means nothing to evaluate.
        return []
    parameters = attendance_services.get_effective_parameters(
        shift=shift, academic_cycle=academic_cycle, on_date=event_date
    )
    school_days = set(parameters.school_days)

    # A day that is not lectivo is skipped, so the walk back covers more
    # calendar days than ``lookback_days``. The bound keeps a school_days
    # value outside 1..7 — which the API rejects but a direct service call
    # could still pass — from spinning forever instead of failing.
    window_dates = []
    cursor = event_date
    max_calendar_days = threshold.lookback_days * 7
    while len(window_dates) < threshold.lookback_days and max_calendar_days > 0:
        if not school_days or cursor.isoweekday() in school_days:
            window_dates.append(cursor)
        cursor -= timedelta(days=1)
        max_calendar_days -= 1
    if len(window_dates) < threshold.lookback_days:
        raise DomainError(
            f"Los parametros de la jornada '{shift}' no declaran dias lectivos utilizables, "
            f"asi que no puede construirse una ventana de ausencias de "
            f"{threshold.lookback_days} dias."
        )

    roster = attendance_services.list_roster_day_statuses(shift=shift, event_date=event_date)
    # One batched read for the whole roster across the whole window: a
    # per-pair derive_day_status here costs three queries times students
    # times days, which is what makes a full jornada unservable.
    statuses = attendance_services.derive_day_statuses(
        students=[entry.student for entry in roster], shift=shift, event_dates=window_dates
    )
    created = []
    for entry in roster:
        absence_count = 0
        for day in window_dates:
            result = statuses.get((entry.student.pk, day))
            if result is not None and result.status == DayStatus.ABSENT_PENDING_JUSTIFICATION:
                absence_count += 1
        if absence_count >= threshold.max_absences:
            alert = _raise_alert(
                alert_type=Alert.AlertType.FREQUENT_ABSENCES,
                student=entry.student,
                shift=shift,
                event_date=event_date,
                section=entry.section,
                target_roles=[Alert.TargetRole.SECTION_COORDINATOR],
                context={"absence_count": absence_count, "lookback_days": threshold.lookback_days},
                actor=actor,
            )
            if alert is not None:
                created.append(alert)
    return created


@dataclass
class DailyAlertEvaluationResult:
    shift: object
    event_date: object
    synced_alerts: list
    superseded_source_alerts: list
    absence_alerts: list
    frequent_absence_alerts: list


@transaction.atomic
def evaluate_daily_alerts(*, shift, event_date, as_of=None, actor=None):
    """Run every RF-JOR-007 alert evaluation for one jornada day in one call."""
    synced_alerts, superseded_source_alerts = sync_attendance_alerts(
        shift=shift, event_date=event_date, actor=actor
    )
    absence_alerts = evaluate_absence_alerts(
        shift=shift, event_date=event_date, as_of=as_of, actor=actor
    )
    frequent_absence_alerts = evaluate_frequent_absence_alerts(
        shift=shift, event_date=event_date, actor=actor
    )
    return DailyAlertEvaluationResult(
        shift=shift,
        event_date=event_date,
        synced_alerts=synced_alerts,
        superseded_source_alerts=superseded_source_alerts,
        absence_alerts=absence_alerts,
        frequent_absence_alerts=frequent_absence_alerts,
    )


@transaction.atomic
def acknowledge_alert(*, alert, actor):
    """Mark an alert as atendida, recording who attended it and when."""
    if not alert.is_active:
        raise DomainError("No se puede atender una alerta que fue superada.")
    if alert.acknowledged_at is not None:
        raise DomainError("La alerta ya fue atendida.")

    # Compare-and-set rather than read-then-save: two concurrent requests
    # both clear the checks above, and only the one whose UPDATE still
    # matches an unacknowledged row may claim the alert. The other gets the
    # same DomainError a sequential retry would have got, instead of
    # silently overwriting who attended it.
    now = timezone.now()
    claimed = Alert.objects.filter(
        pk=alert.pk, is_active=True, acknowledged_at__isnull=True
    ).update(acknowledged_at=now, acknowledged_by=actor, updated_at=now)
    if not claimed:
        raise DomainError("La alerta ya fue atendida.")
    alert.refresh_from_db()
    record_event(
        actor=actor,
        action="reporting.alert.acknowledged",
        resource="Alert",
        resource_identifier=str(alert.pk),
        context={
            "alert_type": alert.alert_type,
            "student_id": str(alert.student.public_id),
            "event_date": str(alert.event_date),
        },
    )
    return alert


def list_alerts(*, shift=None, event_date=None, alert_type=None, is_active=None, acknowledged=None):
    queryset = Alert.objects.select_related("student", "shift", "section", "acknowledged_by")
    if shift is not None:
        queryset = queryset.filter(shift=shift)
    if event_date is not None:
        queryset = queryset.filter(event_date=event_date)
    if alert_type is not None:
        queryset = queryset.filter(alert_type=alert_type)
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    if acknowledged is not None:
        queryset = queryset.filter(acknowledged_at__isnull=not acknowledged)
    return queryset
