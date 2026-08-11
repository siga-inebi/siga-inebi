from django.db import models

from apps.common.models import TimeStampedModel


class JornadaParameters(TimeStampedModel):
    """
    Configurable parameters for a jornada (``academics.Shift``) within an
    academic cycle (RF-JOR-001).

    A change never mutates an existing row: it creates a new one effective
    from a given date, so days already elapsed keep evaluating against the
    parameters that were in force when they happened (AGENTS.md #12).
    """

    shift = models.ForeignKey(
        "academics.Shift", on_delete=models.PROTECT, related_name="jornada_parameters"
    )
    academic_cycle = models.ForeignKey(
        "academics.AcademicCycle", on_delete=models.PROTECT, related_name="jornada_parameters"
    )
    entry_limit_time = models.TimeField()
    tolerance_minutes = models.PositiveIntegerField()
    closing_time = models.TimeField()
    duplicate_suppression_minutes = models.PositiveIntegerField()
    school_days = models.JSONField(default=list)
    effective_from = models.DateField()

    class Meta:
        ordering = ["-effective_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["shift", "academic_cycle", "effective_from"],
                name="unique_jornada_parameters_effective_from",
            )
        ]
        indexes = [
            models.Index(
                fields=["shift", "academic_cycle", "effective_from"],
                name="attendance_params_lookup_idx",
            )
        ]

    def __str__(self):
        return f"{self.shift} ({self.academic_cycle}) from {self.effective_from}"


class AttendanceEvent(TimeStampedModel):
    """
    A single movement record for a student in a jornada (RF-JOR-002/003):
    ``student`` + ``shift`` + ``event_date`` identify "la misma jornada".

    Events are never deleted or overwritten, even when a later event
    supersedes them for precedence purposes (AGENTS.md #12) — a superseded
    event stays stored and queryable.
    """

    class MovementType(models.TextChoices):
        ENTRY = "entry", "Ingreso"
        EXIT = "exit", "Egreso"

    class Origin(models.TextChoices):
        SCAN = "scan", "Escaneo"
        MANUAL = "manual", "Manual"
        DECLARED = "declared", "Declarado"

    class Transmission(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        BATCH = "batch", "Lote"

    student = models.ForeignKey(
        "students.Student", on_delete=models.PROTECT, related_name="attendance_events"
    )
    shift = models.ForeignKey(
        "academics.Shift", on_delete=models.PROTECT, related_name="attendance_events"
    )
    event_date = models.DateField()
    movement_type = models.CharField(max_length=10, choices=MovementType.choices)
    origin = models.CharField(max_length=10, choices=Origin.choices)
    transmission = models.CharField(
        max_length=12, choices=Transmission.choices, default=Transmission.INDIVIDUAL
    )
    captured_at = models.DateTimeField()

    class Meta:
        ordering = ["-captured_at"]
        indexes = [
            models.Index(
                fields=["student", "shift", "event_date", "movement_type"],
                name="attendance_event_prec_idx",
            )
        ]

    def __str__(self):
        return f"{self.student} {self.movement_type} ({self.origin}) {self.captured_at}"


class DayStatus(models.TextChoices):
    """
    Derived daily attendance status (RF-JOR-002). Not a model field: this is
    the shared vocabulary ``services.derive_day_status`` returns and the API
    serializes, computed fresh each time rather than persisted.
    """

    PRESENT = "presente", "Presente"
    LATE = "tarde", "Tarde"
    ABSENT_PENDING_JUSTIFICATION = "ausente_pendiente_justificar", "Ausente pendiente de justificar"
