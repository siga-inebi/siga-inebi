"""
Domain services for evaluation.

RF-EVC-001: Estructura de unidades del ciclo

All invariants and business rules live here, never in views or serializers (AGENTS.md #8).

Unique constraints are delegated to the database and translated back into a
DomainError by unique_violation_as. Reading first and writing afterwards
would leave a window for two concurrent requests to both pass the check.
"""

from datetime import date

from apps.academics.models import AcademicCycle
from apps.audit.services import record_event
from apps.common.db import unique_violation_as
from apps.common.models import DomainError
from apps.evaluation.models import EvaluationUnit


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


def create_evaluation_unit(
    academic_cycle: AcademicCycle,
    number: int,
    name: str,
    starts_on: date,
    ends_on: date,
    actor=None,
) -> EvaluationUnit:
    """
    Create a new evaluation unit within a cycle.

    Validates:
    - starts_on <= ends_on
    - no overlap with existing units in the same cycle

    Args:
        academic_cycle: The cycle this unit belongs to.
        number: Order within cycle (1, 2, 3, 4, ...).
        name: Display name.
        starts_on: First day of evaluation period.
        ends_on: Last day of evaluation period.
        actor: User performing the action (for audit trail).

    Returns:
        EvaluationUnit: The newly created unit.

    Raises:
        DomainError: If validation fails or overlap detected.
    """
    # Validate date range
    if starts_on > ends_on:
        raise DomainError(
            f"Unit start date ({starts_on}) cannot be after end date ({ends_on})."
        )

    # Create unit; DB constraint will reject overlap
    with unique_violation_as(_unit_conflicts(number=number)):
        unit = EvaluationUnit.objects.create(
            academic_cycle=academic_cycle,
            number=number,
            name=name,
            starts_on=starts_on,
            ends_on=ends_on,
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
    )

    return unit
