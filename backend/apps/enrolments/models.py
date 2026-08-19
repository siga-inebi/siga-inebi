from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import TimeStampedModel


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
            models.UniqueConstraint(
                fields=["student", "academic_cycle"],
                condition=Q(status="active"),
                name="unique_active_enrolment_per_student_cycle",
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
