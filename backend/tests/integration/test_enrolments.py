from datetime import date, timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.attendance import services as attendance_services
from apps.attendance.models import AttendanceEvent, StudentCredential
from apps.audit.models import AuditEvent
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment, EnrolmentDocumentRequirement, StudentMovement
from apps.enrolments.services import (
    active_enrolments,
    annul_student_movement,
    change_section,
    create_enrolment,
    enrolment_history,
    matriculate_student,
    record_student_movement,
    reenrol_student,
    section_occupancy,
    set_document_requirement,
    withdraw_student,
)
from apps.evaluation.models import Grade as EvaluationGrade
from tests.factories.academic import AcademicCycleFactory, SectionFactory, SubjectFactory
from tests.factories.attendance import AttendanceEventFactory
from tests.factories.evaluation import EvaluationUnitFactory
from tests.factories.identity import UserFactory
from tests.factories.students import StudentFactory


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_create_valid_enrolment():
    section = SectionFactory()
    student = StudentFactory()

    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    assert enrolment.status == enrolment.EnrolmentStatus.ACTIVE
    assert list(active_enrolments(student=student)) == [enrolment]


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_enrolment_history_preserves_cycle_records():
    student = StudentFactory()
    first_section = SectionFactory()
    second_section = SectionFactory()
    first = Enrolment.objects.create(
        student=student,
        academic_cycle=first_section.academic_cycle,
        grade=first_section.grade,
        section=first_section,
        effective_on=date(2025, 2, 1),
        status=Enrolment.EnrolmentStatus.COMPLETED,
    )
    second = create_enrolment(
        student=student,
        academic_cycle=second_section.academic_cycle,
        grade=second_section.grade,
        section=second_section,
        effective_on=date(2026, 2, 1),
    )

    assert list(enrolment_history(student=student)) == [second, first]


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_cannot_duplicate_incompatible_active_enrolment():
    section = SectionFactory()
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    with pytest.raises(DomainError, match="ya tiene una inscripcion activa"):
        create_enrolment(
            student=student,
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            section=section,
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_change_section_keeps_history():
    first_section = SectionFactory(name="A")
    second_section = SectionFactory(
        academic_cycle=first_section.academic_cycle,
        grade=first_section.grade,
        shift=first_section.shift,
        name="Replacement",
    )
    student = StudentFactory()
    enrolment = create_enrolment(
        student=student,
        academic_cycle=first_section.academic_cycle,
        grade=first_section.grade,
        section=first_section,
    )
    attendance = AttendanceEventFactory(
        student=student,
        shift=first_section.shift,
    )
    grade = EvaluationGrade.objects.create(
        enrolment=enrolment,
        subject=SubjectFactory(institution=first_section.academic_cycle.institution),
        evaluation_unit=EvaluationUnitFactory(academic_cycle=first_section.academic_cycle),
        value=85,
    )

    replacement = change_section(
        enrolment=enrolment,
        new_section=second_section,
        effective_on=timezone.localdate(),
    )

    enrolment.refresh_from_db()
    assert enrolment.status == enrolment.EnrolmentStatus.COMPLETED
    assert replacement.section_id == second_section.id
    assert student.enrolments.count() == 2
    assert StudentMovement.objects.filter(
        source_enrolment=enrolment,
        target_enrolment=replacement,
        movement_type=StudentMovement.MovementType.SECTION_CHANGE,
    ).exists()
    assert EvaluationGrade.objects.get(pk=grade.pk).enrolment_id == enrolment.pk
    assert attendance.student.attendance_events.filter(pk=attendance.pk).exists()


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_student_movement_shape_is_enforced_by_postgresql():
    section = SectionFactory()
    student = StudentFactory()
    enrolment = Enrolment.objects.create(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        effective_on=date(2026, 2, 1),
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        StudentMovement.objects.create(
            student=student,
            movement_type=StudentMovement.MovementType.TRANSFER_IN,
            source_enrolment=enrolment,
            effective_on=date(2026, 2, 1),
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_student_movement_keeps_effective_and_recorded_dates_separate():
    section = SectionFactory()
    student = StudentFactory()
    enrolment = Enrolment.objects.create(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        effective_on=date(2025, 1, 15),
        status=Enrolment.EnrolmentStatus.COMPLETED,
    )

    movement = record_student_movement(
        student=student,
        movement_type=StudentMovement.MovementType.TRANSFER_OUT,
        source_enrolment=enrolment,
        effective_on=date(2025, 10, 30),
    )

    assert movement.effective_on == date(2025, 10, 30)
    assert movement.created_at.date() != movement.effective_on


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_withdrawal_removes_student_from_active_source_without_deleting_history():
    section = SectionFactory()
    student = StudentFactory()
    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        effective_on=date(2026, 2, 1),
    )
    attendance = AttendanceEventFactory(student=student, shift=section.shift)

    movement = withdraw_student(
        enrolment=enrolment,
        reason="Retiro solicitado por responsable",
        effective_on=date(2026, 6, 1),
    )

    assert list(active_enrolments(student=student)) == []
    assert Enrolment.objects.filter(pk=enrolment.pk, status="withdrawn").exists()
    assert StudentMovement.objects.filter(pk=movement.pk, reason__gt="").exists()
    assert attendance.student.attendance_events.filter(pk=attendance.pk).exists()


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_withdrawal_revokes_credential_and_preserves_attendance_history():
    section = SectionFactory()
    student = StudentFactory()
    actor = UserFactory()
    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    credential = attendance_services.issue_credential(student=student)
    attendance = AttendanceEventFactory(student=student, shift=section.shift)

    movement = withdraw_student(
        enrolment=enrolment,
        reason="Cambio de residencia",
        actor=actor,
    )

    credential.refresh_from_db()
    assert credential.status == StudentCredential.Status.REVOKED
    assert credential.revocation_reason == "Cierre de permanencia"
    assert credential.revoked_by == actor
    assert credential.revoked_on_movement == movement
    assert AttendanceEvent.objects.filter(pk=attendance.pk).exists()
    assert AuditEvent.objects.filter(
        action="attendance.credential.revoked_on_permanence_close",
        actor=actor,
    ).exists()


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_credential_revocation_failure_rolls_back_withdrawal():
    section = SectionFactory()
    student = StudentFactory()
    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    attendance_services.issue_credential(student=student)

    with pytest.raises(DomainError, match="identificar quien autorizo"):
        withdraw_student(enrolment=enrolment, reason="Cambio de residencia", actor=None)

    enrolment.refresh_from_db()
    student.refresh_from_db()
    assert enrolment.status == Enrolment.EnrolmentStatus.ACTIVE
    assert student.status == student.StudentStatus.ACTIVE
    assert StudentMovement.objects.count() == 0
    assert StudentCredential.objects.filter(
        student=student,
        status=StudentCredential.Status.ACTIVE,
    ).exists()


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_postgresql_rejects_withdrawal_without_reason():
    section = SectionFactory()
    student = StudentFactory()
    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        StudentMovement.objects.create(
            student=student,
            movement_type=StudentMovement.MovementType.WITHDRAWAL,
            source_enrolment=enrolment,
            reason="",
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_closed_cycle_blocks_changes():
    cycle = AcademicCycleFactory(status="closed")
    section = SectionFactory(academic_cycle=cycle)
    student = StudentFactory()

    with pytest.raises(DomainError):
        create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_create_enrolment_rejects_section_from_another_cycle():
    section = SectionFactory()
    other_section = SectionFactory()
    student = StudentFactory()

    with pytest.raises(DomainError, match="seccion debe pertenecer al ciclo escolar"):
        create_enrolment(
            student=student,
            academic_cycle=section.academic_cycle,
            grade=other_section.grade,
            section=other_section,
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_create_enrolment_rejects_end_date_before_effective_date():
    section = SectionFactory()
    student = StudentFactory()

    with pytest.raises(DomainError, match="no puede ser anterior a su fecha de vigencia"):
        create_enrolment(
            student=student,
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            section=section,
            effective_on=timezone.localdate(),
            ends_on=timezone.localdate() - timedelta(days=1),
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_matriculation_crosses_student_and_academic_domains():
    section = SectionFactory()
    student = StudentFactory(status="pre_enrolled")

    enrolment = matriculate_student(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        shift=section.shift,
        section=section,
    )

    student.refresh_from_db()
    assert enrolment.student_id == student.id
    assert enrolment.section_id == section.id
    assert enrolment.section.shift.id == section.shift.id
    assert student.status == student.StudentStatus.ACTIVE


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_matriculation_blocks_full_section_and_preserves_student_status():
    section = SectionFactory(capacity=1)
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    student = StudentFactory(status="pre_enrolled")

    with pytest.raises(DomainError, match="alcanzo su cupo"):
        matriculate_student(
            student=student,
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            shift=section.shift,
            section=section,
        )

    student.refresh_from_db()
    assert student.status == student.StudentStatus.PRE_ENROLLED
    assert student.enrolments.count() == 0


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_section_occupancy_reflects_the_same_capacity_guard_used_at_matriculation():
    """
    RF-EST-008 vs RF-MAT-004: the read side (occupancy) and the write side
    (the capacity guard) must agree, since both read the same section state.
    """
    section = SectionFactory(capacity=2)
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    occupancy = section_occupancy(section=section).get()
    assert occupancy.capacity == 2
    assert occupancy.active_enrolment_count == 1
    assert occupancy.available_seats == 1

    # Fill the last seat.
    matriculate_student(
        student=StudentFactory(status="pre_enrolled"),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        shift=section.shift,
        section=section,
    )

    full = section_occupancy(section=section).get()
    assert full.active_enrolment_count == 2
    assert full.available_seats == 0

    # The write-side guard now agrees: the section is full.
    with pytest.raises(DomainError, match="alcanzo su cupo"):
        matriculate_student(
            student=StudentFactory(status="pre_enrolled"),
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            shift=section.shift,
            section=section,
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_reenrolment_crosses_student_and_academic_domains():
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

    current = reenrol_student(
        student=student,
        academic_cycle=target_cycle,
        grade=target_section.grade,
        shift=target_section.shift,
        section=target_section,
    )

    assert current.student_id == previous.student_id
    assert current.academic_cycle_id == target_cycle.id
    assert student.enrolments.count() == 2
    student.refresh_from_db()
    assert student.status == student.StudentStatus.ACTIVE


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_document_requirements_cross_enrolment_and_keep_delivery_state():
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    requirement = set_document_requirement(
        enrolment=enrolment,
        code="guardian-id",
        name="Guardian identity document",
        status=EnrolmentDocumentRequirement.DeliveryStatus.DELIVERED,
    )

    assert requirement.enrolment.student_id == enrolment.student_id
    assert requirement.is_required is True
    assert requirement.status == EnrolmentDocumentRequirement.DeliveryStatus.DELIVERED


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_annul_withdrawal_restores_credential_access_and_preserves_audit():
    section = SectionFactory()
    student = StudentFactory()
    actor = UserFactory()
    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    credential = attendance_services.issue_credential(student=student)
    movement = withdraw_student(
        enrolment=enrolment,
        reason="Registro equivocado",
        actor=actor,
    )

    annul_student_movement(
        movement=movement,
        reason="Se retiro al estudiante incorrecto",
        actor=actor,
    )

    credential.refresh_from_db()
    assert credential.status == StudentCredential.Status.ACTIVE
    assert credential.revocation_reason == ""
    assert credential.revoked_by is None
    assert AuditEvent.objects.filter(
        action="attendance.credential.revoked_on_permanence_close",
        actor=actor,
    ).exists()
    assert AuditEvent.objects.filter(
        action="attendance.credential.restored_on_permanence_reopen",
        actor=actor,
    ).exists()
