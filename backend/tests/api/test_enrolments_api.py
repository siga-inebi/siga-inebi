from datetime import date

import pytest
from django.test import Client
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.enrolments.models import Enrolment, EnrolmentDocumentRequirement, StudentMovement
from apps.enrolments.services import (
    create_enrolment,
    enrolment_history,
    record_student_movement,
)
from tests.factories.academic import AcademicCycleFactory, SectionFactory
from tests.factories.identity import PermissionFactory, RoleAssignmentFactory, RoleFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def _grant_enrolment_creation(user):
    permission = PermissionFactory(codename="enrollment_create")
    return RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))


def _payload(section, student):
    return {
        "student_id": str(student.public_id),
        "academic_cycle_id": str(section.academic_cycle.public_id),
        "grade_id": str(section.grade.public_id),
        "section_id": str(section.public_id),
        "effective_on": "2026-02-01",
        "ends_on": "2026-10-30",
    }


def _matriculation_payload(section, student):
    return {
        "student_id": str(student.public_id),
        "academic_cycle_id": str(section.academic_cycle.public_id),
        "grade_id": str(section.grade.public_id),
        "shift_id": str(section.shift.public_id),
        "section_id": str(section.public_id),
        "effective_on": "2026-02-01",
    }


def test_student_movement_history_is_paginated_and_exposes_both_dates(auth_client):
    section = SectionFactory()
    student = StudentFactory()
    enrolment = Enrolment.objects.create(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        effective_on=date(2026, 2, 1),
        status=Enrolment.EnrolmentStatus.COMPLETED,
    )
    movement = record_student_movement(
        student=student,
        movement_type=StudentMovement.MovementType.TRANSFER_OUT,
        source_enrolment=enrolment,
        effective_on=date(2026, 5, 10),
        actor=auth_client.user,
    )

    response = auth_client.get(
        reverse("student-movement-list"),
        {"student_id": str(student.public_id)},
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1
    result = response.json()["results"][0]
    assert result["public_id"] == str(movement.public_id)
    assert result["movement_type"] == "transfer_out"
    assert result["effective_on"] == "2026-05-10"
    assert result["created_at"]
    assert result["source_enrolment_id"] == str(enrolment.public_id)
    assert result["target_enrolment_id"] is None


def test_student_movement_history_requires_session_and_student(auth_client):
    assert Client().get(reverse("student-movement-list")).status_code == 403
    assert auth_client.get(reverse("student-movement-list")).status_code == 400


def test_section_change_endpoint_requires_permission_and_preserves_history(auth_client):
    source_section = SectionFactory(name="A")
    target_section = SectionFactory(
        academic_cycle=source_section.academic_cycle,
        grade=source_section.grade,
        shift=source_section.shift,
        name="B",
    )
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=source_section.academic_cycle,
        grade=source_section.grade,
        section=source_section,
        effective_on=date(2026, 2, 1),
    )
    url = reverse("enrolment-section-change", args=[enrolment.public_id])
    payload = {"new_section_id": str(target_section.public_id), "effective_on": "2026-04-15"}

    assert auth_client.post(url, payload, content_type="application/json").status_code == 403
    assert StudentMovement.objects.count() == 0

    _grant_enrolment_update(auth_client.user)
    response = auth_client.post(url, payload, content_type="application/json")

    assert response.status_code == 201
    assert response.json()["section_id"] == str(target_section.public_id)
    enrolment.refresh_from_db()
    assert enrolment.status == Enrolment.EnrolmentStatus.COMPLETED
    assert enrolment.ends_on == date(2026, 4, 15)
    assert StudentMovement.objects.filter(
        source_enrolment=enrolment,
        target_enrolment__public_id=response.json()["public_id"],
        movement_type=StudentMovement.MovementType.SECTION_CHANGE,
    ).exists()


def test_student_withdrawal_endpoint_requires_permission_and_cause(auth_client):
    section = SectionFactory()
    student = StudentFactory()
    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        effective_on=date(2026, 2, 1),
    )
    url = reverse("student-withdrawal", args=[enrolment.public_id])
    payload = {"reason": "Cambio de residencia", "effective_on": "2026-05-20"}

    assert Client().post(url, payload, content_type="application/json").status_code == 403
    assert auth_client.post(url, payload, content_type="application/json").status_code == 403
    _grant_enrolment_update(auth_client.user)
    assert auth_client.post(url, {"reason": ""}, content_type="application/json").status_code == 400

    response = auth_client.post(url, payload, content_type="application/json")

    assert response.status_code == 201
    assert response.json()["movement_type"] == "withdrawal"
    assert response.json()["reason"] == "Cambio de residencia"
    enrolment.refresh_from_db()
    student.refresh_from_db()
    assert enrolment.status == Enrolment.EnrolmentStatus.WITHDRAWN
    assert student.status == student.StudentStatus.WITHDRAWN


def _reenrolment_payload(section, student):
    return {
        "student_id": str(student.public_id),
        "academic_cycle_id": str(section.academic_cycle.public_id),
        "grade_id": str(section.grade.public_id),
        "shift_id": str(section.shift.public_id),
        "section_id": str(section.public_id),
        "effective_on": "2027-02-01",
    }


def test_create_enrolment_returns_public_references_and_audits(auth_client):
    section = SectionFactory()
    student = StudentFactory()
    _grant_enrolment_creation(auth_client.user)

    response = auth_client.post(
        reverse("enrolment-list-create"),
        _payload(section, student),
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["student_id"] == str(student.public_id)
    assert body["academic_cycle_id"] == str(section.academic_cycle.public_id)
    assert body["grade_id"] == str(section.grade.public_id)
    assert body["section_id"] == str(section.public_id)
    assert body["effective_on"] == "2026-02-01"
    assert body["ends_on"] == "2026-10-30"
    assert AuditEvent.objects.filter(action="enrolments.enrolment.created").exists()


def test_active_enrolment_list_exposes_only_current_records(auth_client):
    section = SectionFactory()
    student = StudentFactory()
    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    response = auth_client.get(reverse("active-enrolment-list"))

    assert response.status_code == 200
    assert response.json()["results"][0]["public_id"] == str(enrolment.public_id)


def test_active_enrolment_list_filters_by_student(auth_client):
    section = SectionFactory()
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    response = auth_client.get(
        reverse("active-enrolment-list"), {"student_id": str(student.public_id)}
    )

    assert response.status_code == 200
    assert len(response.json()["results"]) == 1
    assert response.json()["results"][0]["student_id"] == str(student.public_id)


def test_active_enrolment_list_requires_authentication(client):
    response = client.get(reverse("active-enrolment-list"))

    assert response.status_code in (401, 403)


def test_section_occupancy_api_reports_capacity_and_seats(auth_client):
    section = SectionFactory(capacity=2)
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    response = auth_client.get(
        reverse("section-occupancy-list"),
        {"academic_cycle_id": str(section.academic_cycle.public_id)},
    )

    assert response.status_code == 200
    body = response.json()["results"]
    assert len(body) == 1
    assert body[0]["public_id"] == str(section.public_id)
    assert body[0]["capacity"] == 2
    assert body[0]["occupied_seats"] == 1
    assert body[0]["available_seats"] == 1


def test_section_occupancy_api_filters_by_section(auth_client):
    section = SectionFactory()
    SectionFactory()  # a different section, should not show up

    response = auth_client.get(
        reverse("section-occupancy-list"), {"section_id": str(section.public_id)}
    )

    assert response.status_code == 200
    body = response.json()["results"]
    assert len(body) == 1
    assert body[0]["public_id"] == str(section.public_id)


def test_section_occupancy_api_requires_authentication(client):
    response = client.get(reverse("section-occupancy-list"))

    assert response.status_code in (401, 403)


def test_enrolment_history_returns_all_student_records(auth_client):
    student = StudentFactory()
    section = SectionFactory()
    first = enrolment_history(student=student)
    assert list(first) == []
    older = Enrolment.objects.create(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        status=Enrolment.EnrolmentStatus.COMPLETED,
    )

    response = auth_client.get(
        reverse("enrolment-history-list"), {"student_id": str(student.public_id)}
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["public_id"] == str(older.public_id)
    assert response.json()["results"][0]["status"] == "completed"


def test_enrolment_history_requires_authentication(client):
    response = client.get(
        reverse("enrolment-history-list"),
        {"student_id": "00000000-0000-0000-0000-000000000000"},
    )

    assert response.status_code in (401, 403)


def test_create_enrolment_requires_domain_permission(auth_client):
    section = SectionFactory()
    response = auth_client.post(
        reverse("enrolment-list-create"),
        _payload(section, StudentFactory()),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_enrolment_rejects_invalid_vigency_dates(auth_client):
    section = SectionFactory()
    _grant_enrolment_creation(auth_client.user)
    payload = _payload(section, StudentFactory())
    payload["ends_on"] = date(2026, 1, 31).isoformat()

    response = auth_client.post(
        reverse("enrolment-list-create"), payload, content_type="application/json"
    )

    assert response.status_code == 400
    assert "no puede ser anterior a su fecha de vigencia" in response.json()["error"]["detail"]


def test_create_enrolment_rejects_full_section(auth_client):
    section = SectionFactory(capacity=1)
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    _grant_enrolment_creation(auth_client.user)

    response = auth_client.post(
        reverse("enrolment-list-create"),
        _payload(section, StudentFactory()),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "alcanzo su cupo" in response.json()["error"]["detail"]


def test_matriculate_student_returns_academic_assignment_and_activates_student(auth_client):
    section = SectionFactory()
    student = StudentFactory(status="pre_enrolled")
    _grant_enrolment_creation(auth_client.user)

    response = auth_client.post(
        reverse("matriculation-create"),
        _matriculation_payload(section, student),
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["student_id"] == str(student.public_id)
    assert body["academic_cycle_id"] == str(section.academic_cycle.public_id)
    assert body["grade_id"] == str(section.grade.public_id)
    assert body["shift_id"] == str(section.shift.public_id)
    assert body["section_id"] == str(section.public_id)
    student.refresh_from_db()
    assert student.status == student.StudentStatus.ACTIVE
    assert AuditEvent.objects.filter(action="enrolments.student.matriculated").exists()


def test_matriculate_student_requires_domain_permission(auth_client):
    section = SectionFactory()

    response = auth_client.post(
        reverse("matriculation-create"),
        _matriculation_payload(section, StudentFactory(status="pre_enrolled")),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_matriculate_student_rejects_a_second_active_enrolment(auth_client):
    """
    El rechazo pasa a ser por duplicado, no por el estado del expediente.

    Antes bastaba con que el estudiante no estuviera "preinscrito"; ahora lo que
    se rechaza es tener dos matriculas activas a la vez.
    """
    section = SectionFactory()
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    _grant_enrolment_creation(auth_client.user)

    response = auth_client.post(
        reverse("matriculation-create"),
        _matriculation_payload(section, student),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "ya tiene una inscripcion activa" in response.json()["error"]["detail"]


def test_matriculate_student_rejects_full_section(auth_client):
    section = SectionFactory(capacity=1)
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    student = StudentFactory(status="pre_enrolled")
    _grant_enrolment_creation(auth_client.user)

    response = auth_client.post(
        reverse("matriculation-create"),
        _matriculation_payload(section, student),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "alcanzo su cupo" in response.json()["error"]["detail"]
    student.refresh_from_db()
    assert student.status == student.StudentStatus.PRE_ENROLLED


def test_matriculate_student_rejects_shift_not_assigned_to_section(auth_client):
    section = SectionFactory()
    wrong_shift = SectionFactory().shift
    _grant_enrolment_creation(auth_client.user)
    payload = _matriculation_payload(section, StudentFactory(status="pre_enrolled"))
    payload["shift_id"] = str(wrong_shift.public_id)

    response = auth_client.post(
        reverse("matriculation-create"),
        payload,
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "jornada seleccionada" in response.json()["error"]["detail"]


def test_reenrolment_reuses_student_record_and_audits_source(auth_client):
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
    _grant_enrolment_creation(auth_client.user)
    auth_client.post(
        reverse("enrolment-list-create"),
        _payload(previous_section, student),
        content_type="application/json",
    )
    student.status = student.StudentStatus.PRE_ENROLLED
    student.save(update_fields=["status", "updated_at"])

    response = auth_client.post(
        reverse("reenrolment-create"),
        _reenrolment_payload(target_section, student),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["student_id"] == str(student.public_id)
    assert student.enrolments.count() == 2
    student.refresh_from_db()
    assert student.status == student.StudentStatus.ACTIVE
    assert AuditEvent.objects.filter(action="enrolments.student.reenrolled").exists()


def test_reenrolment_requires_domain_permission(auth_client):
    section = SectionFactory(name="A")

    response = auth_client.post(
        reverse("reenrolment-create"),
        _reenrolment_payload(section, StudentFactory()),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_document_requirement_registers_and_updates_status(auth_client):
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    _grant_enrolment_creation(auth_client.user)
    url = reverse("enrolment-document-requirement-list-create", args=[enrolment.public_id])

    response = auth_client.post(
        url, {"code": "id-card", "name": "Identity card"}, content_type="application/json"
    )
    assert response.status_code == 200
    assert response.json()["status"] == EnrolmentDocumentRequirement.DeliveryStatus.PENDING

    response = auth_client.post(
        url,
        {"code": "id-card", "name": "Identity card", "status": "delivered"},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["code"] == "ID-CARD"
    assert response.json()["status"] == EnrolmentDocumentRequirement.DeliveryStatus.DELIVERED
    assert AuditEvent.objects.filter(action="enrolments.document_requirement.updated").exists()

    response = auth_client.get(url)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["status"] == EnrolmentDocumentRequirement.DeliveryStatus.DELIVERED


def test_document_requirement_requires_domain_permission(auth_client):
    section = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    response = auth_client.post(
        reverse("enrolment-document-requirement-list-create", args=[enrolment.public_id]),
        {"code": "id-card", "name": "Identity card"},
        content_type="application/json",
    )

    assert response.status_code == 403


def test_reenrolment_requires_previous_enrolment(auth_client):
    section = SectionFactory(name="A")
    student = StudentFactory(status="pre_enrolled")
    _grant_enrolment_creation(auth_client.user)

    response = auth_client.post(
        reverse("reenrolment-create"),
        _reenrolment_payload(section, student),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "no tiene matricula previa" in response.json()["error"]["detail"]


def _grant_enrolment_update(user):
    permission = PermissionFactory(codename="enrollment_update")
    return RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))


def _enrolment_for_documents():
    section = SectionFactory()
    return create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )


def test_document_requirement_list_uses_shared_pagination_envelope(auth_client):
    enrolment = _enrolment_for_documents()
    _grant_enrolment_creation(auth_client.user)
    url = reverse("enrolment-document-requirement-list-create", args=[enrolment.public_id])
    auth_client.post(
        url, {"code": "id-card", "name": "Identity card"}, content_type="application/json"
    )
    auth_client.post(
        url, {"code": "birth-cert", "name": "Birth certificate"}, content_type="application/json"
    )

    response = auth_client.get(url)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert [item["code"] for item in body["results"]] == ["BIRTH-CERT", "ID-CARD"]


def test_document_requirement_partial_update_keeps_delivery_state(auth_client):
    enrolment = _enrolment_for_documents()
    _grant_enrolment_creation(auth_client.user)
    url = reverse("enrolment-document-requirement-list-create", args=[enrolment.public_id])
    auth_client.post(
        url,
        {"code": "id-card", "name": "Identity card", "status": "delivered"},
        content_type="application/json",
    )

    response = auth_client.post(
        url, {"code": "id-card", "name": "Identity card (DPI)"}, content_type="application/json"
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Identity card (DPI)"
    assert response.json()["status"] == EnrolmentDocumentRequirement.DeliveryStatus.DELIVERED


def test_document_requirement_accepts_enrolment_update_permission(auth_client):
    enrolment = _enrolment_for_documents()
    _grant_enrolment_update(auth_client.user)
    url = reverse("enrolment-document-requirement-list-create", args=[enrolment.public_id])

    response = auth_client.post(
        url,
        {"code": "id-card", "name": "Identity card", "status": "delivered"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert auth_client.get(url).json()["count"] == 1
