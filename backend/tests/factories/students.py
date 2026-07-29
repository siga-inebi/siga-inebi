import factory
from django.utils import timezone

from apps.students.models import Guardian, Student, StudentGuardianRelation
from tests.factories.people import PersonFactory


class StudentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Student

    person = factory.SubFactory(PersonFactory)
    student_code = factory.Sequence(lambda n: f"STU-{n:04d}")
    status = Student.StudentStatus.ACTIVE


class GuardianFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Guardian

    person = factory.SubFactory(PersonFactory)


class StudentGuardianRelationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentGuardianRelation

    student = factory.SubFactory(StudentFactory)
    guardian = factory.SubFactory(GuardianFactory)
    relationship_label = "Padre"
    is_primary = True
    starts_at = factory.LazyFunction(timezone.localdate)
    ends_at = None
