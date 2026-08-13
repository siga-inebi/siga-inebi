"""
Domain services for evaluation.

RF-EVC-001: Estructura de unidades del ciclo
RF-EVC-002: Ventana de captura de notas
RF-EVC-003: Ventana de recuperacion
RF-EVC-004: Brecha excepcional autorizada

All invariants and business rules live here, never in views or serializers (AGENTS.md #8).

Unique constraints are delegated to the database and translated back into a
DomainError by unique_violation_as. Reading first and writing afterwards
would leave a window for two concurrent requests to both pass the check.
"""

from datetime import date, datetime

from django.utils import timezone

from apps.academics.models import AcademicCycle, Subject
from apps.audit.services import record_event
from apps.common.db import unique_violation_as
from apps.common.models import DomainError
from apps.evaluation.models import CaptureExceptionGrant, EvaluationUnit
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


def _audit(actor, action, instance, **context):
    """Record audit event for domain service action."""
    record_event(
        actor=actor,
        action=action,
        resource=type(instance).__name__,
        resource_identifier=str(instance.pk),
        context=context,
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
            f"Grade capture window is closed for unit '{unit.name}'. "
            f"Window: {unit.capture_starts_on} to {unit.capture_ends_on}."
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
        raise DomainError(
            f"No recovery window has been configured for unit '{unit.name}'."
        )
    if not unit.is_recovery_window_open(on_date):
        raise DomainError(
            f"Recovery window is closed for unit '{unit.name}'. "
            f"Window: {unit.recovery_starts_on} to {unit.recovery_ends_on}."
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
            f"Recovery window start date ({recovery_starts_on}) cannot be after "
            f"end date ({recovery_ends_on})."
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
        raise DomainError("A reason is required to grant a capture exception.")
    if expires_at <= timezone.now():
        raise DomainError("Capture exception expiration must be in the future.")

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
    because the capture window is open (RF-EVC-002) or because an active
    exceptional grant authorizes it (RF-EVC-004).

    Args:
        evaluation_unit: Unit the grade belongs to.
        subject: Subarea of the grade.
        teacher: Teacher attempting to capture the grade.
        on_datetime: Instant to validate against (default: now).

    Raises:
        DomainError: If the window is closed and no active grant covers it.
    """
    at = on_datetime or timezone.now()
    if evaluation_unit.is_capture_window_open(at.date()):
        return
    if has_active_capture_exception(evaluation_unit, subject, teacher, at=at):
        return
    raise DomainError(
        f"Grade capture window is closed for unit '{evaluation_unit.name}' and no "
        f"exceptional grant authorizes teacher '{teacher}' for subject '{subject}'."
    )


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
            f"Unit start date ({starts_on}) cannot be after end date ({ends_on})."
        )

    # Validate capture window dates (RF-EVC-002)
    if capture_starts_on > capture_ends_on:
        raise DomainError(
            f"Capture window start date ({capture_starts_on}) cannot be after "
            f"end date ({capture_ends_on})."
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
