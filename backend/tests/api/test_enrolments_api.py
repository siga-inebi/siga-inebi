import pytest
from django.urls import reverse

from apps.enrolments.models import Enrolment
from tests.factories.academic import AcademicCycleFactory, GradeFactory, SectionFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

MISSING_UUID = "00000000-0000-0000-0000-000000000000"


def _detail(response):
    return response.json()["error"]["detail"]


def _enrol(student, section):
    return {
        "student_id": str(student.public_id),
        "cycle_id": str(section.academic_cycle.public_id),
        "grade_id": str(section.grade.public_id),
        "section_id": str(section.public_id),
    }


@pytest.mark.security
def test_enrolment_endpoints_require_authentication(client):
    response = client.get(reverse("enrolment-list-create"))

    assert response.status_code in (401, 403)


def test_create_enrolment_returns_201(auth_client, institution):
    student = StudentFactory()
    cycle = AcademicCycleFactory(institution=institution)
    section = SectionFactory(academic_cycle=cycle)

    response = auth_client.post(
        reverse("enrolment-list-create"),
        _enrol(student, section),
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "active"
    assert body["student_code"] == student.student_code
    assert Enrolment.objects.filter(student=student, section=section).exists()


def test_create_enrolment_with_unknown_student_returns_400(auth_client, institution):
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))

    response = auth_client.post(
        reverse("enrolment-list-create"),
        {
            "student_id": MISSING_UUID,
            "cycle_id": str(section.academic_cycle.public_id),
            "grade_id": str(section.grade.public_id),
            "section_id": str(section.public_id),
        },
        content_type="application/json",
    )

    assert response.status_code == 400


def test_create_enrolment_over_capacity_returns_400(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution)
    section = SectionFactory(academic_cycle=cycle, capacity=1)
    auth_client.post(
        reverse("enrolment-list-create"),
        _enrol(StudentFactory(), section),
        content_type="application/json",
    )

    response = auth_client.post(
        reverse("enrolment-list-create"),
        _enrol(StudentFactory(), section),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "capacity" in str(_detail(response))


def test_list_enrolments_can_be_filtered_by_student_and_cycle(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution)
    section = SectionFactory(academic_cycle=cycle)
    student = StudentFactory()
    auth_client.post(
        reverse("enrolment-list-create"),
        _enrol(student, section),
        content_type="application/json",
    )
    auth_client.post(
        reverse("enrolment-list-create"),
        _enrol(StudentFactory(), section),
        content_type="application/json",
    )

    response = auth_client.get(
        reverse("enrolment-list-create"),
        {"student": str(student.public_id), "cycle": str(cycle.public_id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["student_code"] == student.student_code


def test_withdraw_enrolment(auth_client, institution):
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))
    student = StudentFactory()
    created = auth_client.post(
        reverse("enrolment-list-create"),
        _enrol(student, section),
        content_type="application/json",
    ).json()

    response = auth_client.post(
        reverse("enrolment-withdraw", args=[created["public_id"]]),
        {"reason": "traslado a otro colegio"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "withdrawn"


def test_withdraw_unknown_enrolment_returns_404(auth_client, institution):
    response = auth_client.post(
        reverse("enrolment-withdraw", args=[MISSING_UUID]),
        {"reason": "no existe"},
        content_type="application/json",
    )

    assert response.status_code == 404


def test_change_section_moves_the_student(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution)
    grade = GradeFactory()
    section = SectionFactory(academic_cycle=cycle, grade=grade)
    other_section = SectionFactory(academic_cycle=cycle, grade=grade)
    student = StudentFactory()
    created = auth_client.post(
        reverse("enrolment-list-create"),
        _enrol(student, section),
        content_type="application/json",
    ).json()

    response = auth_client.post(
        reverse("enrolment-change-section", args=[created["public_id"]]),
        {"new_section_id": str(other_section.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["section_name"] == other_section.name
    assert Enrolment.objects.get(public_id=created["public_id"]).status == "completed"


def test_reenrol_creates_a_new_enrolment_in_another_cycle(auth_client, institution):
    old_cycle = AcademicCycleFactory(institution=institution)
    old_section = SectionFactory(academic_cycle=old_cycle)
    student = StudentFactory()
    created = auth_client.post(
        reverse("enrolment-list-create"),
        _enrol(student, old_section),
        content_type="application/json",
    ).json()
    auth_client.post(
        reverse("enrolment-withdraw", args=[created["public_id"]]),
        {"reason": "fin de ciclo"},
        content_type="application/json",
    )

    new_cycle = AcademicCycleFactory(institution=institution)
    new_section = SectionFactory(academic_cycle=new_cycle)

    response = auth_client.post(
        reverse("enrolment-reenrol", args=[created["public_id"]]),
        {
            "new_cycle_id": str(new_cycle.public_id),
            "new_grade_id": str(new_section.grade.public_id),
            "new_section_id": str(new_section.public_id),
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["cycle_name"] == new_cycle.name
    assert response.json()["status"] == "active"


def test_reenrol_rejects_when_already_active_in_target_cycle(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution)
    section = SectionFactory(academic_cycle=cycle)
    other_section = SectionFactory(academic_cycle=cycle)
    student = StudentFactory()
    created = auth_client.post(
        reverse("enrolment-list-create"),
        _enrol(student, section),
        content_type="application/json",
    ).json()

    response = auth_client.post(
        reverse("enrolment-reenrol", args=[created["public_id"]]),
        {
            "new_cycle_id": str(cycle.public_id),
            "new_grade_id": str(other_section.grade.public_id),
            "new_section_id": str(other_section.public_id),
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "already enrolled" in str(_detail(response))
