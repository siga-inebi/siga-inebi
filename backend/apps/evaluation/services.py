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
RF-RES-002: Punto unico de redondeo
RF-RES-003: Aprobacion de la subarea

All invariants and business rules live here, never in views or serializers (AGENTS.md #8).

Unique constraints are delegated to the database and translated back into a
DomainError by unique_violation_as. Reading first and writing afterwards
would leave a window for two concurrent requests to both pass the check.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

from apps.academics.models import AcademicCycle, Section, Subject
from apps.audit.services import diff_fields, record_event
from apps.common.db import unique_violation_as
from apps.common.exceptions import DomainError
from apps.enrolments.models import Enrolment
from apps.evaluation import queries
from apps.evaluation.models import (
    GRADE_MAX_VALUE,
    GRADE_MIN_VALUE,
    CaptureExceptionGrant,
    CycleEvaluationConfig,
    EvaluationGlobalConfig,
    EvaluationUnit,
    Grade,
    RecoveryGrade,
)
from apps.people.models import Person

# RF-RES-003: minimum final grade for a subarea to be approved, per the
# Reglamento de Evaluacion de los Aprendizajes. Deliberately a Python
# constant, not a field on EvaluationGlobalConfig/CycleEvaluationConfig: the
# requirement is explicit that no institution may configure it away.
SUBJECT_APPROVAL_THRESHOLD = 60

# RF-RES-004: recovery eligibility thresholds, per the Reglamento de Evaluacion
# de los Aprendizajes. Python constants for the same reason as
# SUBJECT_APPROVAL_THRESHOLD: the requirement fixes them and no institution may
# configure them away. The failed-subarea limit is NOT a constant: it is derived
# per grade and cycle from the curriculum plan (see _failed_subject_limit).
RECOVERY_MIN_ATTENDANCE_PERCENTAGE = 80
RECOVERY_LARGE_PLAN_SUBJECT_COUNT = 9
RECOVERY_MAX_FAILED_SMALL_PLAN = 3
RECOVERY_MAX_FAILED_LARGE_PLAN = 4


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


def _round_half_up(value) -> int:
    """
    Round to the nearest integer, ties rounding up (RF-RES-002).

    Python's builtin ``round()`` uses banker's rounding (ties to even), not
    the "mitad hacia arriba" the requirement demands (59.5 -> 60, never 59
    or 58). ``Decimal`` is built from ``str(value)`` rather than from the
    float/Decimal directly: constructing a Decimal straight from a float
    would bake in its binary floating-point error before rounding even
    starts.
    """
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def get_final_subject_grade(enrolment: Enrolment, subject: Subject) -> dict:
    """
    Final grade of a subarea, as the average of its unit grades (RF-RES-001).

    While the cycle is open, this is the same running average as RF-CAL-003
    (get_current_average): it derives from whatever grades are registered
    right now and recalculates on every correction, so it stays correct with
    no extra bookkeeping. It is exposed under its own name and endpoint
    because "resultado" is its own bounded concept in the domain map, and
    later requirements (freezing the result once the cycle closes,
    promotion) will need to diverge from the plain running average without
    touching RF-CAL-003's own contract.

    RF-RES-002: rounding happens exactly once, here, on the final result --
    never on ``average`` (RF-CAL-003's own, unrounded, in-progress figure)
    and never a second time anywhere else. ``final_grade`` is the single
    number every other computation that needs "the" final grade (RF-RES-003's
    approval check, the boleta) must read, so the displayed value and the
    value compared against the approval threshold can never disagree.

    RF-RES-003: ``approved`` is derived from that same ``final_grade`` in
    this one place, against the fixed SUBJECT_APPROVAL_THRESHOLD -- never
    recomputed from a fresh average elsewhere, so it can't drift from what
    was shown to the user.

    RF-RES-005: when a recovery grade exists for this subarea, ``condition``
    is recomputed from it (``approved_by_recovery`` / ``failed``). ``approved``
    and ``final_grade`` still describe the original unit-average result and are
    left untouched -- the recovery is stored alongside, never replacing it, so
    the original stays consultable.

    Returns:
        Same shape as get_current_average (``average``, ``graded_units``,
        ``pending_units``, ``total_units``), plus ``final_grade`` (rounded
        final grade, int, or None if no unit is graded yet), ``approved``
        (bool, or None when ``final_grade`` is None), ``recovery_grade``
        (int recovery value, or None) and ``condition`` (``approved`` /
        ``approved_by_recovery`` / ``failed``, or None when nothing is graded).
    """
    result = get_current_average(enrolment, subject)
    average = result["average"]
    final_grade = _round_half_up(average) if average is not None else None
    result["final_grade"] = final_grade
    result["approved"] = (
        final_grade >= SUBJECT_APPROVAL_THRESHOLD if final_grade is not None else None
    )

    recovery = (
        RecoveryGrade.objects.filter(enrolment=enrolment, subject=subject, is_active=True)
        .order_by("-created_at")
        .first()
    )
    result["recovery_grade"] = recovery.value if recovery is not None else None
    result["condition"] = _subject_condition(result["approved"], result["recovery_grade"])
    return result


def _subject_condition(approved, recovery_grade):
    """
    A subarea's condition label (RF-RES-005).

    When a recovery grade exists it decides the condition on its own
    (``approved_by_recovery`` at or above SUBJECT_APPROVAL_THRESHOLD, otherwise
    ``failed``). With no recovery it mirrors ``approved`` (RF-RES-003), and is
    None while nothing has been graded.
    """
    if recovery_grade is not None:
        return "approved_by_recovery" if recovery_grade >= SUBJECT_APPROVAL_THRESHOLD else "failed"
    if approved is None:
        return None
    return "approved" if approved else "failed"


# --------------------------------------------------------------------------- #
# RF-RES-004 — Elegibilidad de recuperacion
# --------------------------------------------------------------------------- #


@dataclass
class RecoveryEligibility:
    """
    Outcome of the recovery-eligibility check for one enrolment (RF-RES-004).

    ``eligible`` is true only when ``reasons`` is empty. The raw numbers behind
    the decision travel alongside so a consumer can explain it without redoing
    the work.
    """

    enrolment_id: str
    eligible: bool
    reasons: list[str] = field(default_factory=list)
    attendance_percentage: float | None = None
    failed_subjects: int = 0
    total_subjects: int = 0
    failed_limit: int = 0
    recovery_already_used: bool = False


def _failed_subject_limit(total_subjects: int) -> int:
    """
    RF-RES-004: at most 3 failed subareas when the grade's plan has 9 or fewer,
    at most 4 when it has more than 9. Derived from the plan, never fixed.
    """
    if total_subjects <= RECOVERY_LARGE_PLAN_SUBJECT_COUNT:
        return RECOVERY_MAX_FAILED_SMALL_PLAN
    return RECOVERY_MAX_FAILED_LARGE_PLAN


def _cycle_attendance_percentage(enrolment: Enrolment) -> float | None:
    """
    Cycle attendance percentage for the enrolment's student (RF-JOR-009),
    resolved through ``attendance`` as a domain service -- the shift comes from
    the enrolment's section. Returns None when there is no attendance data yet
    or no active enrolment in that cycle and shift, which the caller treats as
    "does not meet the minimum".

    Imported inside the function on purpose: ``attendance`` is not a declared
    dependency of ``academic-evaluation`` in the domain map; this keeps the one
    cross-domain call explicit and out of module import time.
    """
    from apps.attendance.services import compute_attendance_percentage

    try:
        result = compute_attendance_percentage(
            student=enrolment.student, shift=enrolment.section.shift
        )
    except DomainError:
        return None
    return result.percentage


def assess_recovery_eligibility(enrolment: Enrolment) -> RecoveryEligibility:
    """
    Decide whether a student has the right to recovery evaluations (RF-RES-004).

    Three conditions, all evaluated together and none short-circuited, so every
    failing condition is reported:

    1. Cycle attendance is at least RECOVERY_MIN_ATTENDANCE_PERCENTAGE. A
       missing percentage counts as not meeting it.
    2. The number of failed subareas does not exceed the limit derived from the
       grade's curriculum plan for the cycle (_failed_subject_limit): 3 for a
       plan of 9 subareas or fewer, 4 for a larger one.
    3. The student has not already used their recovery opportunity this cycle
       (one per cycle): no RecoveryGrade row exists for the enrolment.

    Read-only: nothing is persisted or audited here.
    """
    reasons: list[str] = []

    percentage = _cycle_attendance_percentage(enrolment)
    if percentage is None:
        reasons.append(
            "No hay datos de asistencia del ciclo para verificar el minimo de "
            f"{RECOVERY_MIN_ATTENDANCE_PERCENTAGE}%."
        )
    elif percentage < RECOVERY_MIN_ATTENDANCE_PERCENTAGE:
        reasons.append(
            f"La asistencia del ciclo ({percentage}%) es menor al minimo de "
            f"{RECOVERY_MIN_ATTENDANCE_PERCENTAGE}%."
        )

    subjects = list(queries.curriculum_subjects(enrolment.academic_cycle, enrolment.grade))
    total_subjects = len(subjects)
    failed_subjects = sum(
        1
        for subject in subjects
        if get_final_subject_grade(enrolment, subject)["approved"] is False
    )
    failed_limit = _failed_subject_limit(total_subjects)
    if failed_subjects > failed_limit:
        reasons.append(
            f"Reprobo {failed_subjects} subareas y el maximo para recuperacion es "
            f"{failed_limit} (plan de estudios de {total_subjects} subareas)."
        )

    recovery_already_used = RecoveryGrade.objects.filter(
        enrolment=enrolment, is_active=True
    ).exists()
    if recovery_already_used:
        reasons.append("El estudiante ya utilizo su oportunidad de recuperacion en este ciclo.")

    return RecoveryEligibility(
        enrolment_id=str(enrolment.public_id),
        eligible=not reasons,
        reasons=reasons,
        attendance_percentage=percentage,
        failed_subjects=failed_subjects,
        total_subjects=total_subjects,
        failed_limit=failed_limit,
        recovery_already_used=recovery_already_used,
    )


# --------------------------------------------------------------------------- #
# RF-RES-005 — Registro de la nota de recuperacion
# --------------------------------------------------------------------------- #


def validate_cycle_recovery_window_open(academic_cycle: AcademicCycle, on_date=None) -> None:
    """
    Validate that the cycle has at least one evaluation unit whose recovery
    window is open on ``on_date`` (RF-EVC-003, lifted to cycle scope for
    RF-RES-005: a subarea's recovery is an end-of-cycle event, not tied to one
    unit, so any open recovery window in the cycle authorizes it).

    Raises:
        DomainError: when no unit of the cycle has an open recovery window.
    """
    on_date = on_date or timezone.localdate()
    has_open_window = EvaluationUnit.objects.filter(
        academic_cycle=academic_cycle,
        is_active=True,
        recovery_starts_on__lte=on_date,
        recovery_ends_on__gte=on_date,
    ).exists()
    if not has_open_window:
        raise DomainError(
            "El ciclo no tiene ninguna ventana de recuperacion abierta en esta fecha."
        )


def register_recovery_grade(
    enrolment: Enrolment,
    subject: Subject,
    value: int,
    actor=None,
) -> RecoveryGrade:
    """
    Register the recovery grade for one failed subarea (RF-RES-005).

    Allowed only when the student is eligible (RF-RES-004), the subarea's
    current condition is failed, and the cycle's recovery window is open. The
    recovery is stored alongside the original final grade (snapshot in
    ``original_final_grade``), never replacing it, and the subarea's condition
    is recomputed from it by get_final_subject_grade.

    A rejected attempt on a non-eligible student is audited
    (``evaluation.recovery_grade_rejected``) before the DomainError is raised,
    so the trail records who tried and why it was refused.

    Raises:
        DomainError: value outside 0-100; student not eligible; subarea not in
            a failed condition; or no recovery window open in the cycle.
    """
    if not GRADE_MIN_VALUE <= value <= GRADE_MAX_VALUE:
        raise DomainError(
            f"La nota de recuperacion debe estar entre {GRADE_MIN_VALUE} y "
            f"{GRADE_MAX_VALUE} (se recibio {value})."
        )

    eligibility = assess_recovery_eligibility(enrolment)
    if not eligibility.eligible:
        record_event(
            actor=actor,
            action="evaluation.recovery_grade_rejected",
            resource="RecoveryGrade",
            context={
                "enrolment_id": str(enrolment.public_id),
                "subject_id": str(subject.public_id),
                "reasons": eligibility.reasons,
            },
        )
        raise DomainError(
            "El estudiante no tiene derecho a recuperacion: " + " ".join(eligibility.reasons)
        )

    final = get_final_subject_grade(enrolment, subject)
    if final["approved"] is not False:
        raise DomainError(
            f"Solo se puede registrar recuperacion de una subarea reprobada; la "
            f"subarea '{subject}' no esta reprobada."
        )

    validate_cycle_recovery_window_open(enrolment.academic_cycle)

    conflicts = {
        "unique_recovery_grade_per_enrolment_subject": (
            f"Ya existe una nota de recuperacion para '{subject}' en esta matricula."
        )
    }
    with unique_violation_as(conflicts):
        recovery = RecoveryGrade.objects.create(
            enrolment=enrolment,
            subject=subject,
            value=value,
            original_final_grade=final["final_grade"],
        )

    _audit(
        actor,
        "evaluation.recovery_grade_registered",
        recovery,
        enrolment_id=str(enrolment.public_id),
        subject_id=str(subject.public_id),
        value=value,
        original_final_grade=final["final_grade"],
    )

    return recovery


# --------------------------------------------------------------------------- #
# RF-CAL-008 — Seguimiento de notas pendientes
# --------------------------------------------------------------------------- #


def build_capture_progress_report(evaluation_unit: EvaluationUnit, on_date=None) -> dict:
    """
    Capture-progress snapshot for an evaluation unit (RF-CAL-008).

    Per section and subarea of the cycle's curriculum plan: how many grades are
    already in and how many are still pending, with the responsible teacher, so
    Direccion and coordinators can see what is missing while the window is open.

    ``window_open`` is false once the capture window has passed or the unit is
    closed; the rows are still returned in that case, so the same view also
    shows what was left uncaptured after the fact.
    """
    rows = queries.capture_progress_rows(evaluation_unit=evaluation_unit)
    total_students = sum(row["students_total"] for row in rows)
    graded_students = sum(row["students_graded"] for row in rows)
    return {
        "unit_public_id": str(evaluation_unit.public_id),
        "unit_name": evaluation_unit.name,
        "window_open": (
            evaluation_unit.is_capture_window_open(on_date) and not evaluation_unit.is_closed
        ),
        "overall_progress_pct": (
            round(graded_students / total_students * 100, 2) if total_students else None
        ),
        "rows": rows,
    }


# --------------------------------------------------------------------------- #
# RF-CAL-004 — Carga masiva desde archivo
# --------------------------------------------------------------------------- #


@dataclass
class BulkGradeResult:
    """
    Outcome of a bulk grade upload (RF-CAL-004). ``created`` is 0 whenever
    ``errors`` is non-empty: the file is all-or-nothing, so a single invalid
    row means nothing is written.
    """

    created: int = 0
    errors: list[dict] = field(default_factory=list)


def bulk_register_unit_grades(
    *,
    evaluation_unit: EvaluationUnit,
    section: Section,
    subject: Subject,
    teacher: Person,
    rows: list[dict],
    actor=None,
) -> BulkGradeResult:
    """
    Register unit grades in bulk from a parsed file (RF-CAL-004).

    ``rows`` is already parsed into ``[{"student_code": str, "value": str}]``;
    parsing the file itself is transport, not a domain rule. Every row is
    validated before anything is written: the student must have an active
    enrolment in ``section``, ``value`` must be an integer in the 0-100 scale
    (RF-CAL-002), and no ``student_code`` may repeat in the file. The unit must
    admit capture for this teacher and subject right now (validate_capture_allowed,
    RF-EVC-002/004) -- a file-level condition, checked once up front.

    If any row fails, nothing is written and the returned result carries
    ``errors`` (``[{"row": int, "field": str, "message": str}]``, 1-based row
    numbers). Otherwise every grade is written inside one transaction, reusing
    register_unit_grade so each grade keeps its own audit entry, plus a
    ``evaluation.grades_bulk_registered`` summary event.

    Raises:
        DomainError: only for the file-level capture check; per-row problems
            come back in ``errors``.
    """
    validate_capture_allowed(evaluation_unit, subject, teacher)

    errors: list[dict] = []
    resolved: list[tuple] = []
    seen_codes: set[str] = set()

    for index, row in enumerate(rows, start=1):
        student_code = (row.get("student_code") or "").strip()
        raw_value = (row.get("value") or "").strip()

        if not student_code:
            errors.append({"row": index, "field": "student_code", "message": "codigo vacio"})
            continue
        if student_code in seen_codes:
            errors.append(
                {
                    "row": index,
                    "field": "student_code",
                    "message": f"fila duplicada para el estudiante '{student_code}'",
                }
            )
            continue
        seen_codes.add(student_code)

        try:
            value = int(raw_value)
        except ValueError:
            errors.append(
                {"row": index, "field": "value", "message": f"valor no numerico: '{raw_value}'"}
            )
            continue
        if not GRADE_MIN_VALUE <= value <= GRADE_MAX_VALUE:
            errors.append(
                {
                    "row": index,
                    "field": "value",
                    "message": (
                        f"la nota debe estar entre {GRADE_MIN_VALUE} y {GRADE_MAX_VALUE} "
                        f"(se recibio {value})"
                    ),
                }
            )
            continue

        enrolment = queries.active_enrolment_in_section(section=section, student_code=student_code)
        if enrolment is None:
            errors.append(
                {
                    "row": index,
                    "field": "student_code",
                    "message": (
                        f"el estudiante '{student_code}' no tiene matricula activa en la "
                        f"seccion indicada"
                    ),
                }
            )
            continue

        resolved.append((enrolment, value))

    if errors:
        record_event(
            actor=actor,
            action="evaluation.grades_bulk_rejected",
            resource="Grade",
            context={
                "unit_id": str(evaluation_unit.public_id),
                "subject_id": str(subject.public_id),
                "section_id": str(section.public_id),
                "row_count": len(rows),
                "error_count": len(errors),
            },
        )
        return BulkGradeResult(created=0, errors=errors)

    with transaction.atomic():
        for enrolment, value in resolved:
            register_unit_grade(
                enrolment=enrolment,
                subject=subject,
                evaluation_unit=evaluation_unit,
                teacher=teacher,
                value=value,
                actor=actor,
            )

    record_event(
        actor=actor,
        action="evaluation.grades_bulk_registered",
        resource="Grade",
        context={
            "unit_id": str(evaluation_unit.public_id),
            "subject_id": str(subject.public_id),
            "section_id": str(section.public_id),
            "created": len(resolved),
        },
    )
    return BulkGradeResult(created=len(resolved), errors=[])
