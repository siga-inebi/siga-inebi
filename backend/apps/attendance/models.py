from django.db import models
from django.db.models import Q

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


class ControlPoint(TimeStampedModel):
    """
    A physical checkpoint (turnstile, gate, entrance) where scans happen
    (RF-ASI-002). Just enough for an ``AttendanceEvent`` to reference where
    it was captured, plus which movement types it admits (RF-ASI-005) --
    both default to allowed so existing points keep working unconfigured.
    """

    campus = models.ForeignKey(
        "academics.Campus", on_delete=models.PROTECT, related_name="control_points"
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    allows_entry = models.BooleanField(default=True)
    allows_exit = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["campus", "code"], name="unique_control_point_code_per_campus"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.campus})"


class ManualRegistrationReason(TimeStampedModel):
    """
    A configurable reason a manual attendance registration can cite
    (RF-ASI-012). Deliberately minimal, same pattern as ``ControlPoint``:
    just enough for an ``AttendanceEvent`` to reference why it was recorded
    without a scan. Retiring one (``is_active=False``) never touches events
    that already cite it (AGENTS.md #12).
    """

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.name


class CaptureBatch(TimeStampedModel):
    """
    RF-ASI-009: an operator's in-progress group of scanned movements, kept
    open across sessions and devices so nothing already captured is lost if
    the operator's session drops before they confirm. Each movement is
    already a real, immutable ``AttendanceEvent`` the instant it's scanned
    (RF-ASI-002) -- this row only tracks whether the group is still being
    accumulated or has been confirmed closed, so recovery is just reading
    rows that were already durably saved, from any device.
    """

    class Status(models.TextChoices):
        OPEN = "open", "Abierto"
        CONFIRMED = "confirmed", "Confirmado"

    operator = models.ForeignKey(
        "identity.UserAccount", on_delete=models.PROTECT, related_name="capture_batches"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["operator"],
                condition=Q(status="open"),
                name="unique_open_capture_batch_per_operator",
            )
        ]

    def __str__(self):
        return f"Lote de {self.operator} ({self.status})"


class AttendanceEventQuerySet(models.QuerySet):
    """
    ``QuerySet.delete()``/``update()`` run a direct SQL statement and never
    call the model's own ``delete()``/``save()`` overrides below, so the
    instance-level guard on its own would not stop a bulk
    ``AttendanceEvent.objects.filter(...).delete()`` (RNF-AUD-001, same gap
    class already closed for ``apps.audit.models.AuditEvent`` in RF-BIT-005).
    """

    def delete(self):
        raise RuntimeError("Attendance events cannot be deleted.")

    def update(self, **kwargs):
        raise RuntimeError("Attendance events cannot be modified.")


class AttendanceEvent(TimeStampedModel):
    """
    A single movement record for a student in a jornada (RF-JOR-002/003):
    ``student`` + ``shift`` + ``event_date`` identify "la misma jornada".

    Events are never deleted or overwritten, even when a later event
    supersedes them for precedence purposes (AGENTS.md #12) — a superseded
    event stays stored and queryable. RNF-AUD-001: corrections must add a new
    row (see ``resolve_prevailing_event``'s precedence rule and
    ``record_scan_movement``'s duplicate rejection, both of which already
    never touch an existing row) rather than editing this one, so both the
    instance and the queryset reject any attempt to do so after creation.
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
    control_point = models.ForeignKey(
        ControlPoint,
        on_delete=models.PROTECT,
        related_name="attendance_events",
        null=True,
        blank=True,
    )
    operator = models.ForeignKey(
        "identity.UserAccount",
        on_delete=models.PROTECT,
        related_name="attendance_events_operated",
        null=True,
        blank=True,
    )
    manual_reason = models.ForeignKey(
        ManualRegistrationReason,
        on_delete=models.PROTECT,
        related_name="attendance_events",
        null=True,
        blank=True,
    )
    client_event_id = models.CharField(max_length=100, blank=True, default="")
    batch_id = models.CharField(max_length=100, blank=True, default="")
    capture_batch = models.ForeignKey(
        CaptureBatch,
        on_delete=models.PROTECT,
        related_name="events",
        null=True,
        blank=True,
    )

    objects = AttendanceEventQuerySet.as_manager()

    class Meta:
        ordering = ["-captured_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["client_event_id"],
                condition=~Q(client_event_id=""),
                name="unique_attendance_event_client_event_id",
            )
        ]
        indexes = [
            models.Index(
                fields=["student", "shift", "event_date", "movement_type"],
                name="attendance_event_prec_idx",
            )
        ]

    def __str__(self):
        return f"{self.student} {self.movement_type} ({self.origin}) {self.captured_at}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("Attendance events cannot be modified.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Attendance events cannot be deleted.")


class AttendanceAlert(TimeStampedModel):
    """
    A generated attendance alert (RF-JOR-004/RF-JOR-005), e.g. a student who
    entered but never registered an exit, or conflicting events for the same
    jornada. Alerts are append-only: they are never edited or removed, and a
    later reevaluation simply raises a new one.

    ``target_roles`` and ``section`` describe who the alert is meant for
    without enforcing delivery: routing an alert to actual people is a
    ``reporting-notifications`` concern, not this domain's.
    """

    class AlertType(models.TextChoices):
        PERMANENCIA_SIN_CIERRE = "permanencia_sin_cierre", "Permanencia sin cierre"
        INCONSISTENCIA = "inconsistencia", "Inconsistencia entre fuentes"

    class TargetRole(models.TextChoices):
        CONTROL_POINT = "control_point", "Personal del punto de control"
        SECTION_COORDINATOR = "section_coordinator", "Coordinador de aula"

    alert_type = models.CharField(max_length=30, choices=AlertType.choices)
    student = models.ForeignKey(
        "students.Student", on_delete=models.PROTECT, related_name="attendance_alerts"
    )
    shift = models.ForeignKey(
        "academics.Shift", on_delete=models.PROTECT, related_name="attendance_alerts"
    )
    section = models.ForeignKey(
        "academics.Section",
        on_delete=models.PROTECT,
        related_name="attendance_alerts",
        null=True,
        blank=True,
    )
    event_date = models.DateField()
    target_roles = models.JSONField(default=list)
    context = models.JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["student", "shift", "event_date", "alert_type"],
                name="attendance_alert_lookup_idx",
            )
        ]

    def __str__(self):
        return f"{self.alert_type} ({self.student}, {self.event_date})"


class DayStatus(models.TextChoices):
    """
    Derived daily attendance status (RF-JOR-002). Not a model field: this is
    the shared vocabulary ``services.derive_day_status`` returns and the API
    serializes, computed fresh each time rather than persisted.
    """

    PRESENT = "presente", "Presente"
    LATE = "tarde", "Tarde"
    ABSENT_PENDING_JUSTIFICATION = "ausente_pendiente_justificar", "Ausente pendiente de justificar"


class RecalculationReason(models.TextChoices):
    """
    Why ``services.recalculate_day`` re-evaluated a day (RF-JOR-006). Not a
    model field: a vocabulary shared by the audit trail and
    ``DayRecalculationResult``. ``JUSTIFICATION_RESOLVED`` is not wired to
    any code path yet — it's the value a future asistencia-justificaciones
    app should pass once that domain exists.
    """

    LATE_EVENT = "late_event", "Evento con fecha anterior"
    PARAMETERS_CHANGED = "parameters_changed", "Cambio de parametros de jornada"
    JUSTIFICATION_RESOLVED = "justification_resolved", "Resolucion de justificacion"


class StudentCredential(TimeStampedModel):
    """
    A student's QR credential (RF-CRE-001).

    ``opaque_identifier`` is the whole QR payload. It is generated randomly and
    is not derived from ``student_code``, the national ID, or any other personal
    data, so scanning the printed code with an off-the-shelf reader yields a
    meaningless string instead of identifying its bearer.

    Credentials are never deleted or rewritten: reposition (RF-CRE-004) issues a
    new row and revocation (RF-CRE-003) flips ``status`` on the old one, so the
    student's credential history stays queryable (AGENTS.md #12).
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Vigente"
        REVOKED = "revoked", "Revocada"

    student = models.ForeignKey(
        "students.Student", on_delete=models.PROTECT, related_name="credentials"
    )
    opaque_identifier = models.CharField(max_length=64)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    issued_at = models.DateTimeField()
    revocation_reason = models.CharField(max_length=255, blank=True, default="")
    revoked_by = models.ForeignKey(
        "identity.UserAccount",
        on_delete=models.PROTECT,
        related_name="credentials_revoked",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-issued_at"]
        constraints = [
            # Named explicitly rather than declared with ``unique=True`` so the
            # services can map the violation back to a message by name.
            models.UniqueConstraint(
                fields=["opaque_identifier"],
                name="unique_credential_opaque_identifier",
            ),
            models.UniqueConstraint(
                fields=["student"],
                condition=Q(status="active", is_active=True),
                name="unique_active_student_credential",
            ),
        ]
        indexes = [
            models.Index(fields=["student", "status"], name="attendance_cred_student_idx"),
        ]

    def __str__(self):
        return f"{self.student} ({self.status})"
