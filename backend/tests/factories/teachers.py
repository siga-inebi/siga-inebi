import factory

from apps.teachers.models import Teacher
from tests.factories.people import PersonFactory


class TeacherFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Teacher

    person = factory.SubFactory(PersonFactory)
    employee_code = factory.Sequence(lambda n: f"EMP-{n:04d}")
    specialty = "Matematica"
    position = Teacher.Position.DOCENTE_TITULADO
