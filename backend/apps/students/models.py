from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class Student(TimeStampedModel):
    class StudentStatus(models.TextChoices):
        PRE_ENROLLED = "pre_enrolled", "Pre-enrolled"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        WITHDRAWN = "withdrawn", "Withdrawn"

    person = models.OneToOneField(
        "people.Person",
        on_delete=models.PROTECT,
        related_name="student_profile",
    )
    student_code = models.CharField(max_length=50, unique=True)
    status = models.CharField(
        max_length=20,
        choices=StudentStatus.choices,
        default=StudentStatus.PRE_ENROLLED,
    )
    photo_path = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.student_code


class Guardian(TimeStampedModel):
    person = models.OneToOneField(
        "people.Person",
        on_delete=models.PROTECT,
        related_name="guardian_profile",
    )

    def __str__(self):
        return str(self.person)


class StudentGuardianRelation(TimeStampedModel):
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="guardian_relations"
    )
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.PROTECT,
        related_name="student_relations",
    )
    relationship_label = models.CharField(max_length=100)
    is_primary = models.BooleanField(default=False)
    starts_at = models.DateField(default=timezone.localdate)
    ends_at = models.DateField(null=True, blank=True)


class EmergencyContact(TimeStampedModel):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="emergency_contacts",
    )
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=30)
    relationship_label = models.CharField(max_length=100)
