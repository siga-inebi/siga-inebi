import factory
from django.utils import timezone

from apps.academics.models import AcademicCycle, Grade, Institution, Section, Shift


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


class ShiftFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Shift

    institution = factory.SubFactory(InstitutionFactory)
    name = factory.Sequence(lambda n: f"Shift {n}")
    code = factory.Sequence(lambda n: f"SH{n}")


class GradeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Grade

    institution = factory.SubFactory(InstitutionFactory)
    name = factory.Sequence(lambda n: f"Grade {n}")
    code = factory.Sequence(lambda n: f"G{n}")


class SectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Section

    academic_cycle = factory.SubFactory(AcademicCycleFactory)
    grade = factory.LazyAttribute(
        lambda obj: GradeFactory(institution=obj.academic_cycle.institution)
    )
    shift = factory.LazyAttribute(
        lambda obj: ShiftFactory(institution=obj.academic_cycle.institution)
    )
    name = factory.Sequence(lambda n: chr(65 + (n % 26)))
    capacity = 35
