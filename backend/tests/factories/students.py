import factory
from django.utils import timezone

from apps.students.models import EmergencyContact, Guardian, Student, StudentGuardianRelation
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
    # False by default: unique_primary_guardian_per_student allows only one
    # open is_primary=True relation per student, so a batch of relations for
    # the same student would raise a raw IntegrityError unless the caller
    # opts in explicitly with StudentGuardianRelationFactory(is_primary=True).
    is_primary = False
    starts_at = factory.LazyFunction(timezone.localdate)
    ends_at = None


class EmergencyContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EmergencyContact

    student = factory.SubFactory(StudentFactory)
    name = factory.Sequence(lambda n: f"Contact {n}")
    phone_number = "555-0100"
    relationship_label = "Tia"
