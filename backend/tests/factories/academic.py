import factory
from django.utils import timezone

from apps.academics.models import (
    AcademicCycle,
    Campus,
    CurriculumPlan,
    Grade,
    GradeOffering,
    Institution,
    Level,
    LevelSubject,
    Section,
    Shift,
    Subject,
    TeachingAssignment,
)
from tests.factories.people import PersonFactory


class InstitutionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Institution

    name = factory.Sequence(lambda n: f"Institution {n}")
    short_name = factory.Sequence(lambda n: f"INST{n}")


class AcademicCycleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AcademicCycle

    institution = factory.SubFactory(InstitutionFactory)
    name = factory.Sequence(lambda n: f"Cycle {n}")
    starts_on = factory.LazyFunction(timezone.localdate)
    ends_on = factory.LazyAttribute(lambda obj: obj.starts_on.replace(month=12, day=31))
    status = AcademicCycle.CycleStatus.ACTIVE


class CampusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Campus

    institution = factory.SubFactory(InstitutionFactory)
    name = factory.Sequence(lambda n: f"Campus {n}")
    code = factory.Sequence(lambda n: f"CMP{n}")
    address = ""
    is_main = False


class ShiftFactory(factory.django.DjangoModelFactory):
    """A shift always belongs to a campus (RF-EST-002)."""

    class Meta:
        model = Shift

    campus = factory.SubFactory(CampusFactory)
    name = factory.Sequence(lambda n: f"Shift {n}")
    code = factory.Sequence(lambda n: f"SH{n}")


class LevelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Level

    institution = factory.SubFactory(InstitutionFactory)
    name = factory.Sequence(lambda n: f"Level {n}")
    code = factory.Sequence(lambda n: f"LV{n}")
    sequence = factory.Sequence(lambda n: n + 1)


class GradeFactory(factory.django.DjangoModelFactory):
    """A grade always belongs to a level (RF-EST-001)."""

    class Meta:
        model = Grade

    class Params:
        institution = None

    level = factory.LazyAttribute(
        lambda obj: LevelFactory(institution=obj.institution) if obj.institution else LevelFactory()
    )
    name = factory.Sequence(lambda n: f"Grade {n}")
    code = factory.Sequence(lambda n: f"G{n}")
    sequence = factory.Sequence(lambda n: n + 1)


class SubjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subject

    institution = factory.SubFactory(InstitutionFactory)
    name = factory.Sequence(lambda n: f"Subject {n}")
    code = factory.Sequence(lambda n: f"SUB{n}")


class LevelSubjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LevelSubject

    level = factory.SubFactory(LevelFactory)
    subject = factory.LazyAttribute(lambda obj: SubjectFactory(institution=obj.level.institution))
    is_required = True
    weekly_hours = 4


class GradeOfferingFactory(factory.django.DjangoModelFactory):
    """Grade offered in a shift of a campus, for one cycle."""

    class Meta:
        model = GradeOffering

    academic_cycle = factory.SubFactory(AcademicCycleFactory)
    grade = factory.LazyAttribute(
        lambda obj: GradeFactory(institution=obj.academic_cycle.institution)
    )
    shift = factory.LazyAttribute(
        lambda obj: ShiftFactory(campus=CampusFactory(institution=obj.academic_cycle.institution))
    )


class SectionFactory(factory.django.DjangoModelFactory):
    """
    Sections hang from a GradeOffering. The ``academic_cycle``, ``grade`` and
    ``shift`` params exist so callers can keep expressing intent in domain terms
    without building the offering by hand.
    """

    class Meta:
        model = Section

    class Params:
        academic_cycle = None
        grade = None
        shift = None

    offering = factory.LazyAttribute(
        lambda obj: _build_offering(obj.academic_cycle, obj.grade, obj.shift)
    )
    name = factory.Sequence(lambda n: chr(65 + (n % 26)))
    capacity = 35


class CurriculumPlanFactory(factory.django.DjangoModelFactory):
    """A subject in the plan of a grade, for one cycle (RF-EST-005)."""

    class Meta:
        model = CurriculumPlan

    academic_cycle = factory.SubFactory(AcademicCycleFactory)
    grade = factory.LazyAttribute(
        lambda obj: GradeFactory(institution=obj.academic_cycle.institution)
    )
    subject = factory.LazyAttribute(
        lambda obj: SubjectFactory(institution=obj.academic_cycle.institution)
    )
    is_required = True


class TeachingAssignmentFactory(factory.django.DjangoModelFactory):
    """
    Teacher in front of a subject of a section. The cycle is taken from the
    section so the row can never point at two different cycles.
    """

    class Meta:
        model = TeachingAssignment

    section = factory.SubFactory(SectionFactory)
    academic_cycle = factory.LazyAttribute(lambda obj: obj.section.academic_cycle)
    subject = factory.LazyAttribute(
        lambda obj: SubjectFactory(institution=obj.section.academic_cycle.institution)
    )
    teacher = factory.SubFactory(PersonFactory)
    ends_on = None


def _build_offering(cycle, grade, shift):
    if cycle is None:
        if grade is not None:
            cycle = AcademicCycleFactory(institution=grade.level.institution)
        elif shift is not None:
            cycle = AcademicCycleFactory(institution=shift.campus.institution)
        else:
            cycle = AcademicCycleFactory()
    institution = cycle.institution
    grade = grade or GradeFactory(institution=institution)
    shift = shift or ShiftFactory(campus=CampusFactory(institution=institution))
    offering, _ = GradeOffering.objects.get_or_create(
        academic_cycle=cycle,
        grade=grade,
        shift=shift,
    )
    return offering
