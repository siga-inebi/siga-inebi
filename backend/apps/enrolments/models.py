from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import TimeStampedModel


class StudentMovementQuerySet(models.QuerySet):
    def delete(self):
        raise RuntimeError("Los movimientos estudiantiles no pueden eliminarse.")

    def update(self, **kwargs):
        raise RuntimeError("Los movimientos estudiantiles no pueden modificarse.")


class Enrolment(TimeStampedModel):
    class EnrolmentStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        WITHDRAWN = "withdrawn", "Withdrawn"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="enrolments",
    )
    academic_cycle = models.ForeignKey(
        "academics.AcademicCycle", on_delete=models.PROTECT, related_name="enrolments"
    )
    grade = models.ForeignKey(
        "academics.Grade", on_delete=models.PROTECT, related_name="enrolments"
    )
    section = models.ForeignKey(
        "academics.Section",
        on_delete=models.PROTECT,
        related_name="enrolments",
    )
    effective_on = models.DateField(default=timezone.localdate)
    ends_on = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=EnrolmentStatus.choices,
        default=EnrolmentStatus.ACTIVE,
    )

    class Meta:
        constraints = [
            # Una sola matricula activa por estudiante, en TODO el sistema y no
            # por ciclo: un estudiante esta cursando en un lugar a la vez. La
            # version por ciclo dejaba pasar un 2026 y un 2027 activos al mismo
            # tiempo, que es un expediente que dice dos cosas distintas sobre
            # donde esta la persona hoy. Reinscribir cierra el anterior.
            models.UniqueConstraint(
                fields=["student"],
                condition=Q(status="active"),
                name="unique_active_enrolment_per_student",
            ),
            # La misma seccion no se repite: repetir grado es volver a cursarlo
            # en OTRO ciclo, con otra seccion. Dos filas del mismo estudiante en
            # la misma seccion son un duplicado de captura, no un dato.
            models.UniqueConstraint(
                fields=["student", "section"],
                name="unique_enrolment_per_student_section",
            ),
            models.CheckConstraint(
                check=Q(ends_on__isnull=True) | Q(effective_on__lte=models.F("ends_on")),
                name="enrolment_valid_effective_dates",
            ),
        ]

    def __str__(self):
        return f"{self.student} - {self.academic_cycle.name}"


class EnrolmentDocumentRequirement(TimeStampedModel):
    class DeliveryStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        DELIVERED = "delivered", "Delivered"

    enrolment = models.ForeignKey(
        Enrolment, on_delete=models.PROTECT, related_name="document_requirements"
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=150)
    is_required = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING
    )

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["enrolment", "code"],
                name="unique_document_requirement_per_enrolment",
            )
        ]

    def __str__(self):
        return f"{self.enrolment} - {self.code}"

    def delete(self, *args, **kwargs):
        raise RuntimeError("Enrolment document requirements cannot be deleted.")


class StudentMovement(TimeStampedModel):
    class MovementType(models.TextChoices):
        SECTION_CHANGE = "section_change", "Cambio de seccion"
        TRANSFER_IN = "transfer_in", "Traslado de ingreso"
        TRANSFER_OUT = "transfer_out", "Traslado de egreso"
        WITHDRAWAL = "withdrawal", "Retiro"

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="movements",
    )
    movement_type = models.CharField(max_length=30, choices=MovementType.choices)
    effective_on = models.DateField(default=timezone.localdate)
    reason = models.TextField(blank=True, default="")
    source_enrolment = models.ForeignKey(
        Enrolment,
        on_delete=models.PROTECT,
        related_name="outgoing_movements",
        null=True,
        blank=True,
    )
    target_enrolment = models.ForeignKey(
        Enrolment,
        on_delete=models.PROTECT,
        related_name="incoming_movements",
        null=True,
        blank=True,
    )

    objects = StudentMovementQuerySet.as_manager()

    class Meta:
        ordering = ["-effective_on", "-created_at", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        movement_type="section_change",
                        source_enrolment__isnull=False,
                        target_enrolment__isnull=False,
                    )
                    | Q(
                        movement_type="transfer_in",
                        source_enrolment__isnull=True,
                        target_enrolment__isnull=False,
                    )
                    | Q(
                        movement_type="transfer_out",
                        source_enrolment__isnull=False,
                        target_enrolment__isnull=True,
                    )
                    | Q(
                        movement_type="withdrawal",
                        source_enrolment__isnull=False,
                        target_enrolment__isnull=True,
                    )
                ),
                name="student_movement_valid_enrolment_shape",
            ),
            models.CheckConstraint(
                condition=~Q(movement_type="withdrawal") | ~Q(reason=""),
                name="student_withdrawal_requires_reason",
            ),
            models.CheckConstraint(
                condition=(
                    Q(source_enrolment__isnull=True)
                    | Q(target_enrolment__isnull=True)
                    | ~Q(source_enrolment=models.F("target_enrolment"))
                ),
                name="student_movement_distinct_enrolments",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("Los movimientos estudiantiles no pueden modificarse.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Los movimientos estudiantiles no pueden eliminarse.")

    def __str__(self):
        return f"{self.student} - {self.get_movement_type_display()}"


class StudentMovementAnnulmentQuerySet(models.QuerySet):
    def delete(self):
        raise RuntimeError("Las anulaciones de movimientos no pueden eliminarse.")

    def update(self, **kwargs):
        raise RuntimeError("Las anulaciones de movimientos no pueden modificarse.")


class StudentMovementAnnulment(TimeStampedModel):
    objects = StudentMovementAnnulmentQuerySet.as_manager()

    movement = models.OneToOneField(
        StudentMovement,
        on_delete=models.PROTECT,
        related_name="annulment",
    )
    reason = models.TextField()
    annulled_by = models.ForeignKey(
        "identity.UserAccount",
        on_delete=models.PROTECT,
        related_name="student_movement_annulments",
    )

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(reason=""),
                name="student_movement_annulment_requires_reason",
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("Las anulaciones de movimientos no pueden modificarse.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Las anulaciones de movimientos no pueden eliminarse.")

    def __str__(self):
        return f"Anulacion de {self.movement_id}"
