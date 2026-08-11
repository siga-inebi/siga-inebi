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
