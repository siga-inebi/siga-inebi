from django.db import transaction

from apps.audit.services import record_event
from apps.people.models import Person
from apps.teachers.models import Teacher


def create_teacher(*, person_data, employee_code, specialty, position, appointment_date=None, actor=None):
    with transaction.atomic():
        person = Person.objects.create(**person_data)
        teacher = Teacher.objects.create(
            person=person,
            employee_code=employee_code,
            specialty=specialty,
            position=position,
            appointment_date=appointment_date,
        )
        record_event(
            actor=actor,
            action="teachers.teacher.created",
            resource="Teacher",
            resource_identifier=str(teacher.pk),
            context={"employee_code": teacher.employee_code},
        )
    return teacher


def deactivate_teacher(*, teacher, actor=None):
    teacher.is_active = False
    teacher.save(update_fields=["is_active", "updated_at"])
    record_event(
        actor=actor,
        action="teachers.teacher.deactivated",
        resource="Teacher",
        resource_identifier=str(teacher.pk),
        context={"employee_code": teacher.employee_code},
    )
    return teacher
