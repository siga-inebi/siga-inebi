from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.db import models
from django.db.models import F, Func, Q, Value
from django.utils import timezone

from apps.common.models import TimeStampedModel


class Institution(TimeStampedModel):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Campus(TimeStampedModel):
    """
    Physical site of the institution ("sede"). Shifts, and therefore the whole
    grade offering, hang from a campus.
    """

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="campuses")
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30)
    address = models.CharField(max_length=255, blank=True)
    is_main = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "campuses"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"], name="unique_campus_code_per_institution"
            ),
            # Partial index: only one row per institution may carry is_main.
            models.UniqueConstraint(
                fields=["institution"],
                condition=Q(is_main=True),
                name="unique_main_campus_per_institution",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class AcademicCycle(TimeStampedModel):
    class CycleStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="academic_cycles"
    )
    year = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    starts_on = models.DateField()
    ends_on = models.DateField()
    status = models.CharField(max_length=20, choices=CycleStatus.choices, default=CycleStatus.DRAFT)

    class Meta:
        ordering = ["-year", "starts_on"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "name"], name="unique_cycle_name_per_institution"
            ),
            models.UniqueConstraint(
                fields=["institution", "year"], name="unique_cycle_year_per_institution"
            ),
            models.UniqueConstraint(
                fields=["institution"],
                condition=Q(status="active"),
                name="unique_active_cycle_per_institution",
            ),
            models.CheckConstraint(
                condition=Q(starts_on__lte=F("ends_on")),
                name="academic_cycle_valid_dates",
            ),
            ExclusionConstraint(
                name="academic_cycle_no_overlapping_dates",
                expressions=[
                    ("institution", RangeOperators.EQUAL),
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
        return self.name

    @property
    def is_closed(self):
        return self.status == self.CycleStatus.CLOSED

    @property
    def is_planning(self):
        return self.status == self.CycleStatus.DRAFT


class Shift(TimeStampedModel):
    """
    Working shift of a campus ("jornada"): matutina, vespertina, nocturna.
    The same code may exist in more than one campus.
    """

    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name="shifts")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)

    class Meta:
        ordering = ["campus__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["campus", "code"], name="unique_shift_code_per_campus")
        ]

    def __str__(self):
        return f"{self.name} - {self.campus.name}"

    @property
    def institution(self):
        return self.campus.institution


class Level(TimeStampedModel):
    """
    Educational level ("nivel"): preprimaria, primaria, basico, diversificado.
    ``sequence`` carries the pedagogical order and is unique per institution.
    """

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="levels")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    sequence = models.PositiveIntegerField()

    class Meta:
        ordering = ["sequence", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"], name="unique_level_code_per_institution"
            ),
            models.UniqueConstraint(
                fields=["institution", "sequence"],
                name="unique_level_sequence_per_institution",
            ),
            # Redundant on its own, but it is the target a Grade's composite
            # foreign key points at, which is what stops a grade from claiming
            # an institution its level does not belong to.
            models.UniqueConstraint(
                fields=["id", "institution"], name="unique_level_id_institution"
            ),
        ]

    def __str__(self):
        return self.name


class Grade(TimeStampedModel):
    """
    Grade inside a level ("grado"): primero primaria, segundo primaria.

    ``institution`` duplicates ``level.institution`` on purpose. A unique index
    cannot span a join, so without the column the institution-wide uniqueness of
    ``code`` could only be checked in Python, which two concurrent inserts can
    both pass. The copy cannot drift: it is derived in ``save`` and a composite
    foreign key on ``(level_id, institution_id)`` makes any disagreement with
    the level unrepresentable (migration 0004).
    """

    level = models.ForeignKey(Level, on_delete=models.PROTECT, related_name="grades")
    institution = models.ForeignKey(
        Institution, on_delete=models.CASCADE, related_name="grades", editable=False
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)
    sequence = models.PositiveIntegerField()

    class Meta:
        ordering = ["level__sequence", "sequence", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["level", "sequence"], name="unique_grade_sequence_per_level"
            ),
            models.UniqueConstraint(
                fields=["institution", "code"], name="unique_grade_code_per_institution"
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Derived on insert, never supplied by callers: the grade belongs
        # wherever its level belongs. Later saves skip the lookup; moving a
        # grade to a level of another institution would be rejected by the
        # composite foreign key rather than silently accepted.
        if self.institution_id is None and self.level_id is not None:
            self.institution_id = self.level.institution_id
        super().save(*args, **kwargs)


class Subject(TimeStampedModel):
    """Course or subarea ("curso"), taught in one or more levels."""

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50)
    levels = models.ManyToManyField(
        Level, through="LevelSubject", related_name="subjects", blank=True
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"], name="unique_subject_code_per_institution"
            )
        ]

    def __str__(self):
        return self.name


class LevelSubject(TimeStampedModel):
    """Subject offered at a level, with its curricular metadata."""

    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="level_subjects")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="level_subjects")
    is_required = models.BooleanField(default=True)
    weekly_hours = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["level__sequence", "subject__name"]
        constraints = [
            models.UniqueConstraint(fields=["level", "subject"], name="unique_subject_per_level")
        ]

    def __str__(self):
        return f"{self.subject.name} @ {self.level.name}"


class GradeOffering(TimeStampedModel):
    """
    A grade actually offered in a shift of a campus, for one cycle. This is the
    catalogue node enrolments are assigned to, and it is rebuilt per cycle
    (RF-EST-013).
    """

    academic_cycle = models.ForeignKey(
        AcademicCycle, on_delete=models.CASCADE, related_name="grade_offerings"
    )
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name="grade_offerings")
    grade = models.ForeignKey(Grade, on_delete=models.PROTECT, related_name="offerings")

    class Meta:
        ordering = ["shift__campus__name", "grade__level__sequence", "grade__sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_cycle", "shift", "grade"],
                name="unique_grade_offering_per_cycle_shift",
            )
        ]

    def __str__(self):
        return f"{self.grade.name} - {self.shift.name} ({self.academic_cycle.name})"

    @property
    def campus(self):
        return self.shift.campus

    @property
    def level(self):
        return self.grade.level

    @property
    def institution(self):
        return self.academic_cycle.institution


class Section(TimeStampedModel):
    """Concrete group of students inside a grade offering."""

    offering = models.ForeignKey(GradeOffering, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=50)
    capacity = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["offering__grade__level__sequence", "offering__grade__sequence", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["offering", "name"], name="unique_section_name_per_offering"
            )
        ]

    def __str__(self):
        return f"{self.offering.grade.name} {self.name}"

    @property
    def academic_cycle(self):
        return self.offering.academic_cycle

    @property
    def grade(self):
        return self.offering.grade

    @property
    def shift(self):
        return self.offering.shift

    @property
    def campus(self):
        return self.offering.campus

    @property
    def level(self):
        return self.offering.grade.level

    @property
    def active_enrolment_count(self):
        """Occupancy (RF-EST-008). Uses the ``_active_enrolments`` annotation if present."""
        annotated = getattr(self, "_active_enrolments", None)
        if annotated is not None:
            return annotated
        return self.enrolments.filter(status="active").count()

    @property
    def available_seats(self):
        """Remaining seats, or ``None`` when the section is uncapped."""
        if self.capacity == 0:
            return None
        return max(0, self.capacity - self.active_enrolment_count)


class CurriculumPlan(TimeStampedModel):
    """Per-cycle study plan for a grade (RF-EST-005)."""

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
        constraints = [
            models.CheckConstraint(
                check=Q(ends_on__isnull=True) | Q(starts_on__lte=F("ends_on")),
                name="teaching_assignment_valid_dates",
            ),
            ExclusionConstraint(
                name="teaching_assignment_no_overlapping_period",
                expressions=[
                    ("academic_cycle", RangeOperators.EQUAL),
                    ("section", RangeOperators.EQUAL),
                    ("subject", RangeOperators.EQUAL),
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
