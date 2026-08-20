"""
Evaluation domain models.

RF-EVC-001: Estructura de unidades del ciclo
- Each AcademicCycle has one or more EvaluationUnits.
- Units define periods within the cycle where grades are captured and finalized.
- Units must not overlap; validation enforced at database level.
RF-EVC-004: Brecha excepcional autorizada
- CaptureExceptionGrant authorizes one teacher, for one subject, in one unit, to
  capture grades outside the unit's capture window, for a determined term.
RF-EVC-005: Configuracion global heredable
- EvaluationGlobalConfig is the single, institution-wide starting point for new
  cycles. CycleEvaluationConfig lets one cycle override it without touching the
  global config or any other cycle.
RF-CAL-001: Registro de la nota de unidad
- Grade is the single consolidated value a teacher already computed for one
  student (via Enrolment), one subject (subarea) and one evaluation unit. The
  system does not derive it from activities; it only stores what arrives.
"""

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.db import models
from django.db.models import F, Func, Q, Value
from django.utils import timezone

from apps.common.models import TimeStampedModel

# RF-CAL-002: admitted grade scale, shared by the model constraint and by the
# service/serializer validation so the three layers can't drift apart.
GRADE_MIN_VALUE = 0
GRADE_MAX_VALUE = 100


class EvaluationUnit(TimeStampedModel):
    """
    Evaluation period within an academic cycle.

    Each unit is a timeframe (e.g., trimester, quarter, semester) where grades
    are captured, closed, or reopened for amendments.

    RF-EVC-001: Unit structure (starts_on, ends_on, status).
    RF-EVC-002: Capture window (capture_starts_on, capture_ends_on) is independent
                of the evaluation period, controlling when grades may be entered.
    RF-EVC-003: Recovery window (recovery_starts_on, recovery_ends_on) is optional
                and independent of the capture window, controlling when recovery
                grades may be entered.

    Invariants:
    - Units within the same cycle must not overlap in time.
    - starts_on must be <= ends_on.
    - capture_starts_on must be <= capture_ends_on.
    - recovery_starts_on and recovery_ends_on are either both set or both null,
      and recovery_starts_on must be <= recovery_ends_on when set.
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
    number = models.PositiveSmallIntegerField(help_text="Order within the cycle: 1, 2, 3, 4, etc.")
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
    recovery_starts_on = models.DateField(
        null=True,
        blank=True,
        help_text="Date when the recovery window opens. Optional; unset until configured.",
    )
    recovery_ends_on = models.DateField(
        null=True,
        blank=True,
        help_text="Date when the recovery window closes. Optional; unset until configured.",
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
            # Recovery window: either both dates set with a valid range, or both unset.
            models.CheckConstraint(
                condition=(
                    Q(recovery_starts_on__isnull=True, recovery_ends_on__isnull=True)
                    | Q(
                        recovery_starts_on__isnull=False,
                        recovery_ends_on__isnull=False,
                        recovery_starts_on__lte=F("recovery_ends_on"),
                    )
                ),
                name="evaluation_unit_valid_recovery_dates",
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

    def is_recovery_window_open(self, on_date=None):
        """
        Check if the recovery window is open on a given date.

        Args:
            on_date: Date to check (default: today).

        Returns:
            True if a recovery window is configured and
            recovery_starts_on <= on_date <= recovery_ends_on, False otherwise.
        """
        if self.recovery_starts_on is None or self.recovery_ends_on is None:
            return False
        if on_date is None:
            on_date = timezone.localdate()
        return self.recovery_starts_on <= on_date <= self.recovery_ends_on


class CaptureExceptionGrant(TimeStampedModel):
    """
    Exceptional, time-boxed authorization to capture grades outside a unit's
    capture window (RF-EVC-004).

    Scoped to exactly one teacher, one subject and one unit. Validity is
    computed from ``expires_at``, so the grant lapses on its own without any
    closing action.
    """

    evaluation_unit = models.ForeignKey(
        EvaluationUnit,
        on_delete=models.CASCADE,
        related_name="capture_exceptions",
        help_text="Unit this exceptional capture grant applies to.",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.PROTECT,
        related_name="capture_exceptions",
        help_text="Subarea the grant is scoped to.",
    )
    teacher = models.ForeignKey(
        "people.Person",
        on_delete=models.PROTECT,
        related_name="capture_exceptions",
        help_text="Teacher authorized to capture grades during the grant.",
    )
    reason = models.TextField(help_text="Justification required to grant the exception.")
    expires_at = models.DateTimeField(help_text="Moment the grant lapses automatically.")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Exception for {self.teacher} / {self.subject} ({self.evaluation_unit})"

    def is_valid(self, at=None):
        """
        Check if the grant is currently in effect.

        Args:
            at: Instant to check (default: now).

        Returns:
            True if the grant is active and has not expired, False otherwise.
        """
        if not self.is_active:
            return False
        if at is None:
            at = timezone.now()
        return at <= self.expires_at


class EvaluationGlobalConfig(TimeStampedModel):
    """
    Institution-wide evaluation configuration (RF-EVC-005).

    Single row, enforced by the unique ``singleton_key``. Serves as the
    starting point for new cycles; a cycle may override it via
    ``CycleEvaluationConfig`` without changing this row.
    """

    singleton_key = models.BooleanField(default=True, unique=True, editable=False)
    default_unit_count = models.PositiveSmallIntegerField(
        default=4,
        help_text="Default number of evaluation units suggested for new cycles.",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(default_unit_count__gt=0),
                name="evaluation_global_config_positive_unit_count",
            ),
        ]

    def __str__(self):
        return f"Global evaluation config (default_unit_count={self.default_unit_count})"


class CycleEvaluationConfig(TimeStampedModel):
    """
    Per-cycle override of the global evaluation configuration (RF-EVC-005).

    ``unit_count`` of ``None`` means the cycle has not departed from the
    global default; editing it here never alters the global config nor any
    other cycle's override.
    """

    academic_cycle = models.OneToOneField(
        "academics.AcademicCycle",
        on_delete=models.CASCADE,
        related_name="evaluation_config",
        help_text="Cycle this configuration override belongs to.",
    )
    unit_count = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Cycle-specific unit count override. Null inherits the global default.",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(unit_count__isnull=True) | Q(unit_count__gt=0),
                name="cycle_evaluation_config_positive_unit_count",
            ),
        ]

    def __str__(self):
        return f"Evaluation config override for {self.academic_cycle.name}"


class Grade(TimeStampedModel):
    """
    Consolidated grade for one student, subarea and evaluation unit (RF-CAL-001).

    The grade arrives already computed by the teacher; this model does not
    derive it from underlying activities. Decomposing a unit grade into
    activities in a later phase must be possible without migrating grades
    already registered here, so the schema deliberately stays a single value
    per (enrolment, subject, evaluation_unit).

    "Sin calificar" (RF-CAL-003) is represented by the absence of a row for a
    given combination, not by a null value: a registered value of zero and a
    combination with no row must stay distinguishable.

    RF-CAL-002: the grade is expressed on a 0-100 scale, enforced at the
    database level so no write path can bypass it.
    """

    enrolment = models.ForeignKey(
        "enrolments.Enrolment",
        on_delete=models.PROTECT,
        related_name="grades",
        help_text="Ties the grade to the student, the section and the cycle.",
    )
    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.PROTECT,
        related_name="grades",
        help_text="Subarea the grade belongs to.",
    )
    evaluation_unit = models.ForeignKey(
        EvaluationUnit,
        on_delete=models.PROTECT,
        related_name="grades",
        help_text="Unit the grade belongs to.",
    )
    value = models.PositiveSmallIntegerField(help_text="Consolidated grade for the unit.")

    class Meta:
        ordering = ["evaluation_unit", "subject"]
        constraints = [
            models.UniqueConstraint(
                fields=["enrolment", "subject", "evaluation_unit"],
                name="unique_grade_per_enrolment_subject_unit",
            ),
            models.CheckConstraint(
                condition=Q(value__gte=GRADE_MIN_VALUE) & Q(value__lte=GRADE_MAX_VALUE),
                name="grade_value_within_scale",
            ),
        ]

    def __str__(self):
        return f"{self.enrolment} / {self.subject} / {self.evaluation_unit}: {self.value}"
