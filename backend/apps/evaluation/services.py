"""
Domain services for evaluation.

RF-EVC-001: Estructura de unidades del ciclo
RF-EVC-002: Ventana de captura de notas
RF-EVC-003: Ventana de recuperacion
RF-EVC-004: Brecha excepcional autorizada
RF-EVC-005: Configuracion global heredable
RF-CAL-001: Registro de la nota de unidad
RF-CAL-002: Escala y validacion de la nota
RF-CAL-003: Distincion entre sin calificar y cero
RF-CAL-005: Correccion de notas registradas
RF-EVC-007: Estados de la unidad
RF-RES-001: Nota final de la subarea

All invariants and business rules live here, never in views or serializers (AGENTS.md #8).

Unique constraints are delegated to the database and translated back into a
DomainError by unique_violation_as. Reading first and writing afterwards
would leave a window for two concurrent requests to both pass the check.
"""

from datetime import date, datetime

from django.db.models import Avg
from django.utils import timezone

from apps.academics.models import AcademicCycle, Subject
from apps.audit.services import diff_fields, record_event
from apps.common.db import unique_violation_as
from apps.common.exceptions import DomainError
from apps.enrolments.models import Enrolment
from apps.evaluation.models import (
    GRADE_MAX_VALUE,
    GRADE_MIN_VALUE,
    CaptureExceptionGrant,
    CycleEvaluationConfig,
    EvaluationGlobalConfig,
    EvaluationUnit,
    Grade,
)
from apps.people.models import Person


def _unit_conflicts(*, number: int) -> dict:
    """Map constraint names to user-facing error messages."""
    return {
        "evaluation_unit_no_overlapping_dates": (
            "This unit overlaps with an existing unit in the same cycle. "
            "Unit dates must not overlap."
        ),
        "unique_unit_number_per_cycle": (
            f"A unit with number {number} already exists in this cycle."
        ),
    }


def _audit(actor, action, instance, *, changes=None, **context):
    """Record audit event for domain service action."""
    record_event(
        actor=actor,
        action=action,
        resource=type(instance).__name__,
        resource_identifier=str(instance.pk),
        context=context,
        changes=changes,
    )


def validate_capture_window_open(unit: EvaluationUnit, on_date=None) -> None:
    """
    Validate that the capture window is open for grade entry (RF-EVC-002).

    Args:
        unit: EvaluationUnit to check.
        on_date: Date to validate (default: today).

    Raises:
        DomainError: If capture window is closed on the given date.
    """
    if not unit.is_capture_window_open(on_date):
        raise DomainError(
            f"La ventana de captura de notas de la unidad '{unit.name}' esta cerrada. "
            f"Vigencia: del {unit.capture_starts_on} al {unit.capture_ends_on}."
        )


def validate_recovery_window_open(unit: EvaluationUnit, on_date=None) -> None:
    """
    Validate that the recovery window is open for recovery grade entry (RF-EVC-003).

    Args:
        unit: EvaluationUnit to check.
        on_date: Date to validate (default: today).

    Raises:
        DomainError: If no recovery window is configured, or it is closed on
            the given date.
    """
    if unit.recovery_starts_on is None or unit.recovery_ends_on is None:
        raise DomainError(f"La unidad '{unit.name}' no tiene ventana de recuperacion configurada.")
    if not unit.is_recovery_window_open(on_date):
        raise DomainError(
            f"La ventana de recuperacion de la unidad '{unit.name}' esta cerrada. "
            f"Vigencia: del {unit.recovery_starts_on} al {unit.recovery_ends_on}."
        )


def set_recovery_window(
    unit: EvaluationUnit,
    recovery_starts_on: date,
    recovery_ends_on: date,
    actor=None,
) -> EvaluationUnit:
    """
    Configure the recovery window for a unit (RF-EVC-003).

    Validates:
    - recovery_starts_on <= recovery_ends_on

    Args:
        unit: EvaluationUnit to configure.
        recovery_starts_on: Date when the recovery window opens.
        recovery_ends_on: Date when the recovery window closes.
        actor: User performing the action (for audit trail).

    Returns:
        EvaluationUnit: The updated unit.

    Raises:
        DomainError: If validation fails.
    """
    if recovery_starts_on > recovery_ends_on:
        raise DomainError(
            f"La fecha de inicio de la ventana de recuperacion ({recovery_starts_on}) no "
            f"puede ser posterior a la de fin ({recovery_ends_on})."
        )

    unit.recovery_starts_on = recovery_starts_on
    unit.recovery_ends_on = recovery_ends_on
    unit.save(update_fields=["recovery_starts_on", "recovery_ends_on", "updated_at"])

    _audit(
        actor,
        "evaluation.unit_recovery_window_set",
        unit,
        recovery_starts_on=str(recovery_starts_on),
        recovery_ends_on=str(recovery_ends_on),
    )

    return unit


def grant_capture_exception(
    evaluation_unit: EvaluationUnit,
    subject: Subject,
    teacher: Person,
    reason: str,
    expires_at: datetime,
    actor=None,
) -> CaptureExceptionGrant:
    """
    Grant an exceptional, time-boxed capture authorization (RF-EVC-004).

    Scoped to exactly one teacher, one subject and one unit. Expires on its
    own; no closing action is required.

    Args:
        evaluation_unit: Unit the grant applies to.
        subject: Subarea the grant is scoped to.
        teacher: Teacher authorized by the grant.
        reason: Justification for the exception (required).
        expires_at: Moment the grant lapses; must be in the future.
        actor: User granting the exception (for audit trail).

    Returns:
        CaptureExceptionGrant: The newly created grant.

    Raises:
        DomainError: If the reason is empty or expires_at is not in the future.
    """
    reason = (reason or "").strip()
    if not reason:
        raise DomainError("Se requiere un motivo para otorgar una excepcion de captura.")
    if expires_at <= timezone.now():
        raise DomainError("El vencimiento de la excepcion de captura debe ser futuro.")

    grant = CaptureExceptionGrant.objects.create(
        evaluation_unit=evaluation_unit,
        subject=subject,
        teacher=teacher,
        reason=reason,
        expires_at=expires_at,
    )

    _audit(
        actor,
        "evaluation.capture_exception_granted",
        grant,
        unit_id=str(evaluation_unit.public_id),
        subject_id=str(subject.public_id),
        teacher_id=str(teacher.public_id),
        reason=reason,
        expires_at=expires_at.isoformat(),
    )

    return grant


def has_active_capture_exception(
    evaluation_unit: EvaluationUnit,
    subject: Subject,
    teacher: Person,
    at: datetime = None,
) -> bool:
    """Check whether a non-expired capture exception grant covers this combination."""
    if at is None:
        at = timezone.now()
    return CaptureExceptionGrant.objects.filter(
        evaluation_unit=evaluation_unit,
        subject=subject,
        teacher=teacher,
        is_active=True,
        expires_at__gt=at,
    ).exists()


def validate_capture_allowed(
    evaluation_unit: EvaluationUnit,
    subject: Subject,
    teacher: Person,
    on_datetime: datetime = None,
) -> None:
    """
    Validate that a teacher may capture grades for a subject in a unit, either
    because the capture window is open and the unit is not closed (RF-EVC-002,
    RF-EVC-007), or because an active exceptional grant authorizes it
    (RF-EVC-004).

    Args:
        evaluation_unit: Unit the grade belongs to.
        subject: Subarea of the grade.
        teacher: Teacher attempting to capture the grade.
        on_datetime: Instant to validate against (default: now).

    Raises:
        DomainError: If the window is closed, or the unit itself is closed,
            and no active grant covers it.
    """
    at = on_datetime or timezone.now()
    if evaluation_unit.is_capture_window_open(at.date()) and not evaluation_unit.is_closed:
        return
    if has_active_capture_exception(evaluation_unit, subject, teacher, at=at):
        return
    raise DomainError(
        f"La ventana de captura de la unidad '{evaluation_unit.name}' esta cerrada y "
        f"ninguna autorizacion excepcional habilita al docente '{teacher}' en el curso "
        f"'{subject}'."
    )


def get_global_evaluation_config() -> EvaluationGlobalConfig:
    """Return the single institution-wide evaluation config, creating it if missing."""
    config = EvaluationGlobalConfig.objects.first()
    if config is None:
        config = EvaluationGlobalConfig.objects.create()
    return config


def update_global_evaluation_config(
    default_unit_count: int,
    actor=None,
) -> EvaluationGlobalConfig:
    """
    Update the global evaluation configuration (RF-EVC-005).

    This is the starting point for new cycles only; it never alters any
    cycle's own override.

    Args:
        default_unit_count: New default number of units for new cycles.
        actor: User performing the action (for audit trail).

    Raises:
        DomainError: If default_unit_count is not a positive integer.
    """
    if default_unit_count <= 0:
        raise DomainError("default_unit_count debe ser un entero positivo.")

    config = get_global_evaluation_config()
    config.default_unit_count = default_unit_count
    config.save(update_fields=["default_unit_count", "updated_at"])

    _audit(
        actor,
        "evaluation.global_config_updated",
        config,
        default_unit_count=default_unit_count,
    )

    return config


def get_effective_unit_count(academic_cycle: AcademicCycle) -> int:
    """
    Return the unit count that applies to a cycle: its own override if set,
    otherwise the global default (RF-EVC-005).
    """
    override = getattr(academic_cycle, "evaluation_config", None)
    if override is not None and override.unit_count is not None:
        return override.unit_count
    return get_global_evaluation_config().default_unit_count


def set_cycle_unit_count(
    academic_cycle: AcademicCycle,
    unit_count: int,
    actor=None,
) -> CycleEvaluationConfig:
    """
    Make a cycle depart from the global unit count (RF-EVC-005).

    Only the given cycle is affected; the global config and every other
    cycle's configuration remain unchanged.

    Args:
        academic_cycle: Cycle to override.
        unit_count: New unit count for this cycle only.
        actor: User performing the action (for audit trail).

    Raises:
        DomainError: If unit_count is not a positive integer.
    """
    if unit_count <= 0:
        raise DomainError("unit_count debe ser un entero positivo.")

    config, _ = CycleEvaluationConfig.objects.get_or_create(academic_cycle=academic_cycle)
    config.unit_count = unit_count
    config.save(update_fields=["unit_count", "updated_at"])

    _audit(
        actor,
        "evaluation.cycle_config_overridden",
        config,
        cycle_id=str(academic_cycle.public_id),
        unit_count=unit_count,
    )

    return config


def create_evaluation_unit(
    academic_cycle: AcademicCycle,
    number: int,
    name: str,
    starts_on: date,
    ends_on: date,
    capture_starts_on: date,
    capture_ends_on: date,
    actor=None,
) -> EvaluationUnit:
    """
    Create a new evaluation unit within a cycle.

    Validates:
    - starts_on <= ends_on (evaluation period)
    - capture_starts_on <= capture_ends_on (capture window)
    - no overlap with existing units in the same cycle

    Args:
        academic_cycle: The cycle this unit belongs to.
        number: Order within cycle (1, 2, 3, 4, ...).
        name: Display name.
        starts_on: First day of evaluation period.
        ends_on: Last day of evaluation period.
        capture_starts_on: Date when grade capture window opens (RF-EVC-002).
        capture_ends_on: Date when grade capture window closes (RF-EVC-002).
        actor: User performing the action (for audit trail).

    Returns:
        EvaluationUnit: The newly created unit.

    Raises:
        DomainError: If validation fails or overlap detected.
    """
    # Validate evaluation period dates
    if starts_on > ends_on:
        raise DomainError(
            f"La fecha de inicio de la unidad ({starts_on}) no puede ser posterior a la de "
            f"fin ({ends_on})."
        )

    # Validate capture window dates (RF-EVC-002)
    if capture_starts_on > capture_ends_on:
        raise DomainError(
            f"La fecha de inicio de la ventana de captura ({capture_starts_on}) no puede "
            f"ser posterior a la de fin ({capture_ends_on})."
        )

    # Create unit; DB constraint will reject overlap
    with unique_violation_as(_unit_conflicts(number=number)):
        unit = EvaluationUnit.objects.create(
            academic_cycle=academic_cycle,
            number=number,
            name=name,
            starts_on=starts_on,
            ends_on=ends_on,
            capture_starts_on=capture_starts_on,
            capture_ends_on=capture_ends_on,
            status=EvaluationUnit.UnitStatus.OPEN,
        )

    # Audit: record creation
    _audit(
        actor,
        "evaluation.unit_created",
        unit,
        cycle_id=str(academic_cycle.public_id),
        number=number,
        name=name,
        starts_on=str(starts_on),
        ends_on=str(ends_on),
        capture_starts_on=str(capture_starts_on),
        capture_ends_on=str(capture_ends_on),
    )

    return unit


def close_evaluation_unit(unit: EvaluationUnit, actor=None) -> EvaluationUnit:
    """
    Close an evaluation unit (RF-EVC-007).

    A closed unit's results are definitive: register_unit_grade rejects any
    further capture or correction for it unless an exceptional grant
    (RF-EVC-004) covers the teacher and subject. The transition itself is
    recorded in the bitacora with the responsible user and the moment.

    Args:
        unit: EvaluationUnit to close.
        actor: User performing the action (for audit trail).

    Returns:
        EvaluationUnit: The closed unit.

    Raises:
        DomainError: If the unit is already closed.
    """
    if unit.is_closed:
        raise DomainError(f"La unidad '{unit.name}' ya esta cerrada.")

    unit.status = EvaluationUnit.UnitStatus.CLOSED
    unit.save(update_fields=["status", "updated_at"])

    _audit(actor, "evaluation.unit_closed", unit, unit_id=str(unit.public_id))

    return unit


def register_unit_grade(
    enrolment: Enrolment,
    subject: Subject,
    evaluation_unit: EvaluationUnit,
    teacher: Person,
    value: int,
    actor=None,
) -> Grade:
    """
    Register the consolidated grade a teacher already computed for a student,
    subarea and unit (RF-CAL-001).

    The capture window must be open, or an active exceptional grant (RF-EVC-004)
    must cover this teacher and subject for the unit (validate_capture_allowed
    checks both). Calling this again for the same (enrolment, subject,
    evaluation_unit) updates the existing grade instead of creating a
    duplicate: it is the single consolidated value for that combination, not
    a new entry.

    Correcting an already-registered grade (RF-CAL-005) goes through this
    same path: validate_capture_allowed already rejects the correction once
    the capture window is closed unless an exceptional grant covers the
    teacher and subject. When the grade already existed, the audit event
    additionally carries `changes` with the value before and after, read via
    diff_fields before the row is mutated.

    Args:
        enrolment: Ties the grade to the student, section and cycle.
        subject: Subarea the grade belongs to.
        evaluation_unit: Unit the grade belongs to.
        teacher: Teacher capturing the grade (checked against the capture
            window and any exceptional grant).
        value: Consolidated grade value.
        actor: User performing the action (for audit trail).

    Returns:
        Grade: The registered (created or updated) grade.

    Raises:
        DomainError: If the value is outside the 0-100 scale (RF-CAL-002), if
            the enrolment and the unit belong to different academic cycles,
            or if capture is not allowed for this teacher, subject and unit
            right now.
    """
    if not GRADE_MIN_VALUE <= value <= GRADE_MAX_VALUE:
        raise DomainError(
            f"La nota debe estar entre {GRADE_MIN_VALUE} y {GRADE_MAX_VALUE} (se recibio {value})."
        )

    if evaluation_unit.academic_cycle_id != enrolment.academic_cycle_id:
        raise DomainError(
            "La unidad de evaluacion y la matricula pertenecen a ciclos escolares distintos."
        )

    validate_capture_allowed(evaluation_unit, subject, teacher)

    existing = Grade.objects.filter(
        enrolment=enrolment, subject=subject, evaluation_unit=evaluation_unit
    ).first()
    changes = diff_fields(existing, value=value) if existing else None

    grade, created = Grade.objects.update_or_create(
        enrolment=enrolment,
        subject=subject,
        evaluation_unit=evaluation_unit,
        defaults={"value": value},
    )

    _audit(
        actor,
        "evaluation.grade_registered" if created else "evaluation.grade_updated",
        grade,
        changes=changes,
        enrolment_id=str(enrolment.public_id),
        subject_id=str(subject.public_id),
        unit_id=str(evaluation_unit.public_id),
        teacher_id=str(teacher.public_id),
        value=value,
    )

    return grade


def get_current_average(enrolment: Enrolment, subject: Subject) -> dict:
    """
    Running average of a student's registered grades for a subarea (RF-CAL-003).

    A unit with no registered grade is "sin calificar", not zero: it is
    excluded from the average and only counted as pending. If nothing has
    been graded yet, ``average`` is None rather than 0, so callers never
    have to guess whether a 0 is a real grade or an absence of data.

    Args:
        enrolment: Ties the query to the student, section and cycle.
        subject: Subarea to average.

    Returns:
        dict with ``average`` (None if no unit is graded yet),
        ``graded_units``, ``pending_units`` and ``total_units`` for the
        enrolment's academic cycle.
    """
    total_units = EvaluationUnit.objects.filter(
        academic_cycle=enrolment.academic_cycle, is_active=True
    ).count()

    graded = Grade.objects.filter(
        enrolment=enrolment,
        subject=subject,
        evaluation_unit__academic_cycle=enrolment.academic_cycle,
        is_active=True,
    )
    graded_units = graded.count()
    average = graded.aggregate(average=Avg("value"))["average"]

    return {
        "average": average,
        "graded_units": graded_units,
        "pending_units": total_units - graded_units,
        "total_units": total_units,
    }


def get_final_subject_grade(enrolment: Enrolment, subject: Subject) -> dict:
    """
    Final grade of a subarea, as the average of its unit grades (RF-RES-001).

    While the cycle is open, this is the same running average as RF-CAL-003
    (get_current_average): it derives from whatever grades are registered
    right now and recalculates on every correction, so it stays correct with
    no extra bookkeeping. It is exposed under its own name and endpoint
    because "resultado" is its own bounded concept in the domain map, and
    later requirements (freezing the result once the cycle closes, the
    single-rounding-point rule, promotion) will need to diverge from the
    plain running average without touching RF-CAL-003's own contract.

    Returns:
        Same shape as get_current_average: ``average`` (None if no unit is
        graded yet), ``graded_units``, ``pending_units`` and ``total_units``.
    """
    return get_current_average(enrolment, subject)
