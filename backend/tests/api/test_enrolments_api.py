from datetime import date

import pytest
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.enrolments.models import EnrolmentDocumentRequirement
from apps.enrolments.services import create_enrolment
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
    assert "end date cannot precede" in response.json()["error"]["detail"]


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
    assert "Section capacity has been reached" in response.json()["error"]["detail"]


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


def test_matriculate_student_rejects_active_student(auth_client):
    section = SectionFactory()
    _grant_enrolment_creation(auth_client.user)

    response = auth_client.post(
        reverse("matriculation-create"),
        _matriculation_payload(section, StudentFactory()),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "Only pre-enrolled students" in response.json()["error"]["detail"]


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
    assert "Section capacity has been reached" in response.json()["error"]["detail"]
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
    assert "selected shift" in response.json()["error"]["detail"]


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

    response = auth_client.post(
        reverse("reenrolment-create"),
        _reenrolment_payload(target_section, student),
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["student_id"] == str(student.public_id)
    assert student.enrolments.count() == 2
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
    assert response.json()[0]["status"] == EnrolmentDocumentRequirement.DeliveryStatus.DELIVERED


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
    student = StudentFactory()
    _grant_enrolment_creation(auth_client.user)

    response = auth_client.post(
        reverse("reenrolment-create"),
        _reenrolment_payload(section, student),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "no previous enrolment" in response.json()["error"]["detail"]
