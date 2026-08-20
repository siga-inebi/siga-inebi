from django.db import transaction

from apps.audit.services import record_event
from apps.common.codes import create_with_generated_code, next_sequential_code
from apps.common.db import unique_violation_as
from apps.people.models import Person
from apps.teachers.models import Teacher

# Serie del codigo de empleado: "DOC-007".
#
# Es institucional y sin anio: un docente conserva su codigo entre ciclos, a
# diferencia del codigo de estudiante, que se emite por cohorte.
EMPLOYEE_CODE_PREFIX = "DOC"
EMPLOYEE_CODE_WIDTH = 3
EMPLOYEE_CODE_CONSTRAINT = "teachers_teacher_employee_code_key"


def next_employee_code():
    """Siguiente codigo de empleado libre."""
    return next_sequential_code(
        queryset=Teacher.objects.all(),
        field="employee_code",
        prefix=EMPLOYEE_CODE_PREFIX,
        width=EMPLOYEE_CODE_WIDTH,
    )


def create_teacher(
    *,
    person_data,
    employee_code=None,
    specialty,
    position,
    appointment_date=None,
    actor=None,
):
    """
    Register a teaching or administrative staff member.

    ``employee_code`` es opcional: sin el se genera el siguiente de la serie. Se
    sigue aceptando uno explicito porque el establecimiento puede venir de una
    numeracion previa que ya figura en contratos y planillas.
    """
    supplied = (employee_code or "").strip()

    def build(code):
        person = Person.objects.create(**person_data)
        return Teacher.objects.create(
            person=person,
            employee_code=code,
            specialty=specialty,
            position=position,
            appointment_date=appointment_date,
        )

    with transaction.atomic():
        if supplied:
            with unique_violation_as(
                {EMPLOYEE_CODE_CONSTRAINT: (f"Employee code '{supplied}' is already registered.")}
            ):
                teacher = build(supplied)
        else:
            teacher = create_with_generated_code(
                build=build,
                generate=next_employee_code,
                constraint=EMPLOYEE_CODE_CONSTRAINT,
            )
        record_event(
            actor=actor,
            action="teachers.teacher.created",
            resource="Teacher",
            resource_identifier=str(teacher.pk),
            context={"employee_code": teacher.employee_code, "generated": not supplied},
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
