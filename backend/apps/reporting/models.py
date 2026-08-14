from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class AbsenceThresholdParameters(TimeStampedModel):
    """
    Configurable "ausencias frecuentes" threshold for a jornada
    (``academics.Shift``) within an academic cycle (RF-JOR-007).

    Versioned the same way as ``attendance.JornadaParameters``: a change
    never mutates an existing row, it creates a new one effective from a
    given date, so evaluations of days already elapsed keep using the
    threshold that was in force when they happened.
    """

    shift = models.ForeignKey(
        "academics.Shift", on_delete=models.PROTECT, related_name="absence_threshold_parameters"
    )
    academic_cycle = models.ForeignKey(
        "academics.AcademicCycle",
        on_delete=models.PROTECT,
        related_name="absence_threshold_parameters",
    )
    max_absences = models.PositiveIntegerField()
    lookback_days = models.PositiveIntegerField()
    effective_from = models.DateField()

    class Meta:
        ordering = ["-effective_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["shift", "academic_cycle", "effective_from"],
                name="unique_absence_threshold_parameters_effective_from",
            )
        ]
        indexes = [
            models.Index(
                fields=["shift", "academic_cycle", "effective_from"],
                name="reporting_threshold_lookup_idx",
            )
        ]

    def __str__(self):
        return f"{self.shift} ({self.academic_cycle}) from {self.effective_from}"


class Alert(TimeStampedModel):
    """
    A generated attendance alert for RF-JOR-007's alert surface. Two of the
    four alert types (``permanencia_sin_cierre``, ``inconsistencia``) are
    detected by ``apps.attendance`` and only *projected* here through
    ``source_attendance_alert`` — this app never re-derives that detection
    logic (domain-map's "no tablas acopladas sin API interna clara"
    boundary). The other two (``ausente_sin_registro``,
    ``frecuencia_ausencias``) are detected here directly, from read-only
    queries against ``apps.attendance``.

    Alerts are append-only like their ``attendance`` counterparts: a
    reevaluation raises a new one rather than mutating a prior alert, and a
    resolved condition deactivates the alert (``is_active=False``) instead
    of deleting it.
    """

    class AlertType(models.TextChoices):
        ABSENCE_NOT_REGISTERED = "ausente_sin_registro", "Ausencia no registrada"
        PERMANENCIA_SIN_CIERRE = "permanencia_sin_cierre", "Permanencia sin cierre"
        FREQUENT_ABSENCES = "frecuencia_ausencias", "Ausencias frecuentes"
        INCONSISTENCIA = "inconsistencia", "Inconsistencia entre fuentes"

    class TargetRole(models.TextChoices):
        CONTROL_POINT = "control_point", "Personal del punto de control"
        SECTION_COORDINATOR = "section_coordinator", "Coordinador de aula"

    alert_type = models.CharField(max_length=30, choices=AlertType.choices)
    student = models.ForeignKey(
        "students.Student", on_delete=models.PROTECT, related_name="reporting_alerts"
    )
    shift = models.ForeignKey(
        "academics.Shift", on_delete=models.PROTECT, related_name="reporting_alerts"
    )
    section = models.ForeignKey(
        "academics.Section",
        on_delete=models.PROTECT,
        related_name="reporting_alerts",
        null=True,
        blank=True,
    )
    event_date = models.DateField()
    target_roles = models.JSONField(default=list)
    context = models.JSONField(default=dict)
    source_attendance_alert = models.ForeignKey(
        "attendance.AttendanceAlert",
        on_delete=models.PROTECT,
        related_name="reporting_alerts",
        null=True,
        blank=True,
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="acknowledged_reporting_alerts",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # An evaluation run is idempotent: it must not raise a second
            # active alert of the same type for the same student and day.
            # Enforced here rather than by the service's read-before-write,
            # which two concurrent evaluations can both pass.
            models.UniqueConstraint(
                fields=["student", "shift", "event_date", "alert_type"],
                condition=models.Q(is_active=True),
                name="unique_active_alert_per_student_day_type",
            )
        ]
        indexes = [
            models.Index(
                fields=["student", "shift", "event_date", "alert_type"],
                name="reporting_alert_lookup_idx",
            )
        ]

    def __str__(self):
        return f"{self.alert_type} ({self.student}, {self.event_date})"
