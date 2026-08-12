"""
Evaluation domain models.

RF-EVC-001: Estructura de unidades del ciclo
- Each AcademicCycle has one or more EvaluationUnits.
- Units define periods within the cycle where grades are captured and finalized.
- Units must not overlap; validation enforced at database level.
"""

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.db import models
from django.db.models import F, Func, Q, Value
from django.utils import timezone

from apps.common.models import TimeStampedModel


class EvaluationUnit(TimeStampedModel):
    """
    Evaluation period within an academic cycle.

    Each unit is a timeframe (e.g., trimester, quarter, semester) where grades
    are captured, closed, or reopened for amendments.

    RF-EVC-001: Unit structure (starts_on, ends_on, status).
    RF-EVC-002: Capture window (capture_starts_on, capture_ends_on) is independent
                of the evaluation period, controlling when grades may be entered.

    Invariants:
    - Units within the same cycle must not overlap in time.
    - starts_on must be <= ends_on.
    - capture_starts_on must be <= capture_ends_on.
    - Hard constraint at DB level to prevent race conditions (AGENTS.md #9).

    Soft delete: use is_active (inherited from TimeStampedModel).
    """

    class UnitStatus(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    academic_cycle = models.ForeignKey(
        "academics.AcademicCycle",
        on_delete=models.CASCADE,
        related_name="evaluation_units",
        help_text="Cycle this evaluation unit belongs to.",
    )
    number = models.PositiveSmallIntegerField(
        help_text="Order within the cycle: 1, 2, 3, 4, etc."
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name: 'Unit 1', 'First Trimester', etc.",
    )
    starts_on = models.DateField(help_text="First day of evaluation period.")
    ends_on = models.DateField(help_text="Last day of evaluation period.")
    status = models.CharField(
        max_length=20,
        choices=UnitStatus.choices,
        default=UnitStatus.OPEN,
        help_text="OPEN: accepts grade capture; CLOSED: no capture unless authorized breach.",
    )
    capture_starts_on = models.DateField(
        help_text="Date when grade capture window opens (independent of evaluation dates).",
    )
    capture_ends_on = models.DateField(
        help_text="Date when grade capture window closes; after this, no capture is allowed.",
    )

    class Meta:
        ordering = ["academic_cycle", "number"]
        constraints = [
            # Same cycle cannot have duplicate unit numbers.
            models.UniqueConstraint(
                fields=["academic_cycle", "number"],
                name="unique_unit_number_per_cycle",
            ),
            # Dates must be valid.
            models.CheckConstraint(
                condition=Q(starts_on__lte=F("ends_on")),
                name="evaluation_unit_valid_dates",
            ),
            # Capture window dates must be valid.
            models.CheckConstraint(
                condition=Q(capture_starts_on__lte=F("capture_ends_on")),
                name="evaluation_unit_valid_capture_dates",
            ),
            # Units within the same cycle must not overlap (PostgreSQL-specific).
            # Similar to academic_cycle_no_overlapping_dates constraint.
            ExclusionConstraint(
                name="evaluation_unit_no_overlapping_dates",
                expressions=[
                    ("academic_cycle", RangeOperators.EQUAL),
                    (
                        Func(
                            F("starts_on"),
                            F("ends_on"),
                            Value("[]"),
                            function="DATERANGE",
                            output_field=DateRangeField(),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.academic_cycle.name})"

    @property
    def is_closed(self):
        return self.status == self.UnitStatus.CLOSED

    def is_capture_window_open(self, on_date=None):
        """
        Check if the capture window is open on a given date.

        Args:
            on_date: Date to check (default: today).

        Returns:
            True if capture_starts_on <= on_date <= capture_ends_on, False otherwise.
        """
        if on_date is None:
            on_date = timezone.localdate()
        return self.capture_starts_on <= on_date <= self.capture_ends_on
