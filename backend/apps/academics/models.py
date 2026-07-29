from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class Institution(TimeStampedModel):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class AcademicCycle(TimeStampedModel):
    class CycleStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="academic_cycles"
    )
    name = models.CharField(max_length=100)
    starts_on = models.DateField()
    ends_on = models.DateField()
    status = models.CharField(max_length=20, choices=CycleStatus.choices, default=CycleStatus.DRAFT)

    class Meta:
        unique_together = [("institution", "name")]


class Shift(TimeStampedModel):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="shifts")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)

    class Meta:
        unique_together = [("institution", "code")]


class Grade(TimeStampedModel):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="grades")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)

    class Meta:
        unique_together = [("institution", "code")]


class Section(TimeStampedModel):
    academic_cycle = models.ForeignKey(
        AcademicCycle, on_delete=models.CASCADE, related_name="sections"
    )
    grade = models.ForeignKey(Grade, on_delete=models.PROTECT, related_name="sections")
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name="sections")
    name = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("academic_cycle", "grade", "name")]


class Subject(TimeStampedModel):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50)

    class Meta:
        unique_together = [("institution", "code")]


class CurriculumPlan(TimeStampedModel):
    academic_cycle = models.ForeignKey(
        AcademicCycle, on_delete=models.CASCADE, related_name="curriculum_plans"
    )
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="curriculum_plans")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="curriculum_plans")
    is_required = models.BooleanField(default=True)

    class Meta:
        unique_together = [("academic_cycle", "grade", "subject")]


class TeachingAssignment(TimeStampedModel):
    academic_cycle = models.ForeignKey(
        AcademicCycle, on_delete=models.CASCADE, related_name="teaching_assignments"
    )
    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="teaching_assignments"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="teaching_assignments"
    )
    teacher = models.ForeignKey(
        "people.Person",
        on_delete=models.PROTECT,
        related_name="teaching_assignments",
    )
    starts_on = models.DateField(default=timezone.localdate)
    ends_on = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [("academic_cycle", "section", "subject", "teacher", "starts_on")]
