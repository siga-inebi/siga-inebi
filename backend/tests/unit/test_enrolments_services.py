from datetime import date

import pytest

from apps.common.models import DomainError
from apps.enrolments.models import Enrolment, EnrolmentDocumentRequirement
from apps.enrolments.services import (
    active_enrolments,
    change_section,
    create_enrolment,
    enrolment_history,
    matriculate_student,
    reenrol_student,
    section_occupancy,
    set_document_requirement,
)
from tests.factories.academic import AcademicCycleFactory, GradeFactory, SectionFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_create_enrolment_keeps_explicit_vigency_dates():
    section = SectionFactory()
    student = StudentFactory()

    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        effective_on=date(2026, 2, 1),
        ends_on=date(2026, 10, 30),
    )

    assert enrolment.effective_on == date(2026, 2, 1)
    assert enrolment.ends_on == date(2026, 10, 30)
    assert enrolment.status == enrolment.EnrolmentStatus.ACTIVE


def test_enrolment_history_includes_all_statuses_and_orders_latest_first():
    student = StudentFactory()
    newest_section = SectionFactory()
    older_section = SectionFactory()
    older = Enrolment.objects.create(
        student=student,
        academic_cycle=older_section.academic_cycle,
        grade=older_section.grade,
        section=older_section,
        effective_on=date(2025, 2, 1),
        status=Enrolment.EnrolmentStatus.COMPLETED,
    )
    newest = Enrolment.objects.create(
        student=student,
        academic_cycle=newest_section.academic_cycle,
        grade=newest_section.grade,
        section=newest_section,
        effective_on=date(2026, 2, 1),
        status=Enrolment.EnrolmentStatus.ACTIVE,
    )
    newest.is_active = False
    newest.save(update_fields=["is_active", "updated_at"])

    assert list(enrolment_history(student=student)) == [newest, older]


def test_create_enrolment_rejects_grade_not_owned_by_section():
    section = SectionFactory()
    foreign_grade = SectionFactory().grade

    with pytest.raises(DomainError, match="Section must belong to the grade"):
        create_enrolment(
            student=StudentFactory(),
            academic_cycle=section.academic_cycle,
            grade=foreign_grade,
            section=section,
        )


def test_create_enrolment_rejects_closed_cycle():
    cycle = AcademicCycleFactory(status="closed")
    section = SectionFactory(academic_cycle=cycle)

    with pytest.raises(DomainError, match="Closed academic cycles"):
        create_enrolment(
            student=StudentFactory(),
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )


def test_create_enrolment_rejects_full_section():
    section = SectionFactory(capacity=1)
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    with pytest.raises(DomainError, match="Section capacity has been reached"):
        create_enrolment(
            student=StudentFactory(),
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            section=section,
        )


def test_create_enrolment_ignores_completed_records_for_capacity():
    section = SectionFactory(capacity=1)
    Enrolment.objects.create(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        status=Enrolment.EnrolmentStatus.COMPLETED,
    )
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    assert enrolment.status == Enrolment.EnrolmentStatus.ACTIVE


def test_closed_cycle_rejects_section_change():
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    cycle = section.academic_cycle
    cycle.status = cycle.CycleStatus.CLOSED
    cycle.save(update_fields=["status", "updated_at"])

    with pytest.raises(DomainError, match="Closed academic cycles"):
        change_section(enrolment=enrolment, new_section=SectionFactory(academic_cycle=cycle))


def test_matriculate_student_activates_pre_enrolled_student_and_links_shift():
    section = SectionFactory()
    student = StudentFactory(status="pre_enrolled")

    enrolment = matriculate_student(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        shift=section.shift,
        section=section,
        effective_on=date(2026, 2, 1),
    )

    student.refresh_from_db()
    assert enrolment.student_id == student.id
    assert enrolment.section_id == section.id
    assert section.shift.id == enrolment.section.shift.id
    assert student.status == student.StudentStatus.ACTIVE


def test_matriculate_student_accepts_a_student_without_an_open_enrolment():
    """
    Ya no hace falta devolver el expediente a "preinscrito".

    Exigirlo obligaba a un paso previo por cada estudiante activo del ciclo
    anterior, y no protegia de nada: lo que se debe evitar es la matricula
    duplicada, y eso lo cubren los constraints.
    """
    section = SectionFactory()

    enrolment = matriculate_student(
        student=StudentFactory(status="active"),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        shift=section.shift,
        section=section,
    )

    assert enrolment.status == Enrolment.EnrolmentStatus.ACTIVE


def test_matriculate_student_rejects_a_second_active_enrolment():
    """Una sola matricula activa por estudiante, aunque el ciclo sea otro."""
    first_section = SectionFactory()
    other_cycle = AcademicCycleFactory(
        institution=first_section.academic_cycle.institution,
        year=2027,
        name="Ciclo 2027",
        starts_on=date(2027, 1, 15),
        ends_on=date(2027, 10, 29),
        status="draft",
    )
    second_section = SectionFactory(
        academic_cycle=other_cycle,
        grade=first_section.grade,
        shift=first_section.shift,
        name="B",
    )
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=first_section.academic_cycle,
        grade=first_section.grade,
        section=first_section,
    )

    with pytest.raises(DomainError, match="already has an active enrolment"):
        matriculate_student(
            student=student,
            academic_cycle=other_cycle,
            grade=second_section.grade,
            shift=second_section.shift,
            section=second_section,
        )


def test_matriculate_student_rejects_repeating_the_same_section():
    """Repetir es cursar de nuevo en OTRO ciclo, con otra seccion."""
    section = SectionFactory()
    student = StudentFactory()
    first = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    first.status = Enrolment.EnrolmentStatus.WITHDRAWN
    first.save(update_fields=["status", "updated_at"])

    with pytest.raises(DomainError, match="already enrolled in this section"):
        matriculate_student(
            student=student,
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            shift=section.shift,
            section=section,
        )


def test_matriculate_student_rejects_an_archived_student():
    """La baja del expediente no es una regla de duplicados; sigue vigente."""
    section = SectionFactory()

    with pytest.raises(DomainError, match="Inactive students"):
        matriculate_student(
            student=StudentFactory(is_active=False),
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            shift=section.shift,
            section=section,
        )


def test_matriculate_student_rejects_shift_not_assigned_to_section():
    section = SectionFactory()
    wrong_shift = SectionFactory().shift

    with pytest.raises(DomainError, match="selected shift"):
        matriculate_student(
            student=StudentFactory(status="pre_enrolled"),
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            shift=wrong_shift,
            section=section,
        )


def test_change_section_rejects_full_target_section_without_closing_current_enrolment():
    current_section = SectionFactory()
    target_section = SectionFactory(
        academic_cycle=current_section.academic_cycle,
        grade=current_section.grade,
        shift=current_section.shift,
        capacity=1,
    )
    current_enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=current_section.academic_cycle,
        grade=current_section.grade,
        section=current_section,
    )
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=target_section.academic_cycle,
        grade=target_section.grade,
        section=target_section,
    )

    with pytest.raises(DomainError, match="Section capacity has been reached"):
        change_section(enrolment=current_enrolment, new_section=target_section)

    current_enrolment.refresh_from_db()
    assert current_enrolment.status == Enrolment.EnrolmentStatus.ACTIVE


def test_reenrol_student_reuses_student_record_and_previous_enrolment():
    previous_section = SectionFactory(name="A")
    target_cycle = AcademicCycleFactory(
        institution=previous_section.academic_cycle.institution,
        starts_on=date(2027, 1, 1),
        ends_on=date(2027, 12, 31),
        status="draft",
    )
    target_section = SectionFactory(
        academic_cycle=target_cycle,
        grade=previous_section.grade,
        shift=previous_section.shift,
        name="B",
    )
    student = StudentFactory()
    previous = create_enrolment(
        student=student,
        academic_cycle=previous_section.academic_cycle,
        grade=previous_section.grade,
        section=previous_section,
    )
    student.status = student.StudentStatus.PRE_ENROLLED
    student.save(update_fields=["status", "updated_at"])

    enrolment = reenrol_student(
        student=student,
        academic_cycle=target_cycle,
        grade=target_section.grade,
        shift=target_section.shift,
        section=target_section,
    )

    assert enrolment.student_id == student.id
    assert enrolment.academic_cycle_id == target_cycle.id
    assert student.enrolments.filter(pk=previous.pk).exists()
    student.refresh_from_db()
    assert student.status == student.StudentStatus.ACTIVE


def test_reenrol_student_requires_previous_enrolment():
    section = SectionFactory(name="A")

    with pytest.raises(DomainError, match="no previous enrolment"):
        reenrol_student(
            student=StudentFactory(status="pre_enrolled"),
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            shift=section.shift,
            section=section,
        )


def test_reenrol_student_closes_the_previous_active_enrolment():
    """
    Reinscribir cierra el ciclo anterior en la misma transaccion.

    Es lo que hace usable la regla de "una sola activa": sin esto habria que
    pasar antes por una pantalla de cierre para cada estudiante que sigue.
    """
    previous_section = SectionFactory(name="A")
    target_cycle = AcademicCycleFactory(
        institution=previous_section.academic_cycle.institution,
        year=2027,
        name="Ciclo 2027",
        starts_on=date(2027, 1, 15),
        ends_on=date(2027, 10, 29),
        status="draft",
    )
    target_section = SectionFactory(
        academic_cycle=target_cycle,
        grade=previous_section.grade,
        shift=previous_section.shift,
        name="B",
    )
    student = StudentFactory(status="active")
    previous = create_enrolment(
        student=student,
        academic_cycle=previous_section.academic_cycle,
        grade=previous_section.grade,
        section=previous_section,
        effective_on=date(2026, 1, 15),
    )

    enrolment = reenrol_student(
        student=student,
        academic_cycle=target_cycle,
        grade=target_section.grade,
        shift=target_section.shift,
        section=target_section,
        effective_on=date(2027, 1, 15),
    )

    previous.refresh_from_db()
    assert previous.status == Enrolment.EnrolmentStatus.COMPLETED
    assert previous.ends_on == date(2027, 1, 15)
    assert enrolment.status == Enrolment.EnrolmentStatus.ACTIVE


def test_set_document_requirement_records_and_updates_delivery_status():
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    requirement = set_document_requirement(
        enrolment=enrolment, code="birth-cert", name="Birth certificate"
    )
    updated = set_document_requirement(
        enrolment=enrolment,
        code="birth-cert",
        name="Birth certificate",
        status=EnrolmentDocumentRequirement.DeliveryStatus.DELIVERED,
    )

    assert requirement.pk == updated.pk
    assert updated.code == "BIRTH-CERT"
    assert updated.status == EnrolmentDocumentRequirement.DeliveryStatus.DELIVERED
    assert enrolment.document_requirements.count() == 1


def test_set_document_requirement_rejects_blank_code():
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    with pytest.raises(DomainError, match="Document code cannot be empty"):
        set_document_requirement(enrolment=enrolment, code="  ", name="Birth certificate")


def test_set_document_requirement_preserves_delivery_state_on_partial_update():
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    set_document_requirement(
        enrolment=enrolment,
        code="id-card",
        name="Identity card",
        status=EnrolmentDocumentRequirement.DeliveryStatus.DELIVERED,
        is_required=False,
    )

    corrected = set_document_requirement(
        enrolment=enrolment, code="id-card", name="Identity card (DPI)"
    )

    assert corrected.name == "Identity card (DPI)"
    assert corrected.status == EnrolmentDocumentRequirement.DeliveryStatus.DELIVERED
    assert corrected.is_required is False


def test_set_document_requirement_rejects_closed_cycle():
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    cycle = enrolment.academic_cycle
    cycle.status = "closed"
    cycle.save(update_fields=["status"])

    with pytest.raises(DomainError, match="Closed academic cycles"):
        set_document_requirement(enrolment=enrolment, code="id-card", name="Identity card")


def test_set_document_requirement_revives_deactivated_row():
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    requirement = set_document_requirement(
        enrolment=enrolment, code="id-card", name="Identity card"
    )
    requirement.is_active = False
    requirement.save(update_fields=["is_active"])

    revived = set_document_requirement(enrolment=enrolment, code="id-card", name="Identity card")

    assert revived.pk == requirement.pk
    assert revived.is_active is True


def test_active_enrolments_excludes_historical_and_inactive_records():
    section = SectionFactory()
    active_student = StudentFactory()
    historical_student = StudentFactory()
    inactive_student = StudentFactory()
    active = create_enrolment(
        student=active_student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    Enrolment.objects.create(
        student=historical_student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        status=Enrolment.EnrolmentStatus.COMPLETED,
    )
    inactive = create_enrolment(
        student=inactive_student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    inactive.is_active = False
    inactive.save(update_fields=["is_active", "updated_at"])

    assert list(active_enrolments()) == [active]


def test_section_occupancy_reports_capacity_and_used_seats():
    section = SectionFactory(capacity=2)
    Enrolment.objects.create(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        status=Enrolment.EnrolmentStatus.ACTIVE,
    )
    Enrolment.objects.create(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        status=Enrolment.EnrolmentStatus.WITHDRAWN,
    )

    result = section_occupancy(section=section).get()

    assert result.capacity == 2
    assert result.active_enrolment_count == 1
    assert result.available_seats == 1


def test_section_occupancy_uncapped_section_has_no_available_seats_limit():
    section = SectionFactory(capacity=0)
    Enrolment.objects.create(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        status=Enrolment.EnrolmentStatus.ACTIVE,
    )

    result = section_occupancy(section=section).get()

    assert result.available_seats is None


def test_section_occupancy_full_section_has_zero_available_seats():
    section = SectionFactory(capacity=1)
    Enrolment.objects.create(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        status=Enrolment.EnrolmentStatus.ACTIVE,
    )

    result = section_occupancy(section=section).get()

    assert result.available_seats == 0


def test_section_occupancy_filters_by_cycle_and_grade():
    cycle = AcademicCycleFactory()
    grade = GradeFactory(institution=cycle.institution)
    matching = SectionFactory(academic_cycle=cycle, grade=grade)
    SectionFactory()  # unrelated cycle and grade

    result = list(section_occupancy(academic_cycle=cycle, grade=grade))

    assert result == [matching]


def test_section_occupancy_excludes_inactive_sections_unless_requested():
    active_section = SectionFactory()
    inactive_section = SectionFactory(is_active=False)

    default_result = list(section_occupancy())
    assert active_section in default_result
    assert inactive_section not in default_result

    with_inactive = list(section_occupancy(include_inactive=True))
    assert inactive_section in with_inactive
