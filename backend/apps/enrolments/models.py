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
            )
        ]

    def __str__(self):
        return f"{self.student} - {self.academic_cycle.name}"
