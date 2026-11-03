"""Filtros de nivel, grado y seccion del listado de estudiantes (RF-CRE-002).

La exportacion de carnes elige estudiantes por su matricula ACTIVA: estos
filtros no amplian el alcance, solo acotan lo que el actor ya puede ver.
"""

import pytest
from django.urls import reverse

from apps.enrolments.models import Enrolment
from apps.enrolments.services import create_enrolment
from tests.factories.academic import AcademicCycleFactory, GradeFactory, SectionFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.students import StudentFactory


@pytest.fixture
def logged_in_client(client):
    user = UserFactory(password="test-pass-123")
    client.login(username=user.username, password="test-pass-123")
    client.user = user
    return client


def _grant(user, **scope):
    assignment = RoleAssignmentFactory(
        user=user, role=RoleFactory(permissions=[PermissionFactory(codename="student_view_basic")])
    )
    ScopeGrantFactory(assignment=assignment, **scope)


def _enrol(student, section):
    return create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )


@pytest.fixture
def school():
    """Nivel 1 con dos grados (uno con dos secciones) y nivel 2 con uno."""
    cycle = AcademicCycleFactory()
    first = GradeFactory(institution=cycle.institution)
    second = GradeFactory(institution=cycle.institution, level=first.level)
    other_level = GradeFactory(institution=cycle.institution)
    sections = {
        "first_a": SectionFactory(academic_cycle=cycle, grade=first, name="A"),
        "first_b": SectionFactory(academic_cycle=cycle, grade=first, name="B"),
        "second": SectionFactory(academic_cycle=cycle, grade=second, name="A"),
        "other": SectionFactory(academic_cycle=cycle, grade=other_level, name="A"),
    }
    students = {name: StudentFactory() for name in sections}
    for name, section in sections.items():
        _enrol(students[name], section)
    # Matricula cerrada en first_a: ya no cuenta como alumno de esa seccion.
    withdrawn = StudentFactory()
    Enrolment.objects.filter(pk=_enrol(withdrawn, sections["first_a"]).pk).update(
        status=Enrolment.EnrolmentStatus.WITHDRAWN
    )
    students["withdrawn"] = withdrawn
    return {
        "level": first.level,
        "grade": first,
        "sections": sections,
        "students": students,
    }


def _codes(response):
    assert response.status_code == 200, response.content
    return sorted(row["student_code"] for row in response.json()["results"])


def _expected(school, *names):
    return sorted(school["students"][name].student_code for name in names)


@pytest.mark.api
@pytest.mark.django_db
def test_level_filter_lists_students_with_active_enrolment_in_the_level(logged_in_client, school):
    _grant(logged_in_client.user, module_key="students")

    response = logged_in_client.get(reverse("student-list"), {"level": school["level"].public_id})

    assert _codes(response) == _expected(school, "first_a", "first_b", "second")


@pytest.mark.api
@pytest.mark.django_db
def test_grade_filter_lists_each_student_once(logged_in_client, school):
    _grant(logged_in_client.user, module_key="students")

    response = logged_in_client.get(reverse("student-list"), {"grade": school["grade"].public_id})

    assert _codes(response) == _expected(school, "first_a", "first_b")
    assert response.json()["count"] == 2


@pytest.mark.api
@pytest.mark.django_db
def test_section_filter_ignores_closed_enrolments(logged_in_client, school):
    _grant(logged_in_client.user, module_key="students")

    response = logged_in_client.get(
        reverse("student-list"), {"section": school["sections"]["first_a"].public_id}
    )

    assert _codes(response) == _expected(school, "first_a")


@pytest.mark.api
@pytest.mark.django_db
def test_filters_combine_with_each_other_and_with_search(logged_in_client, school):
    _grant(logged_in_client.user, module_key="students")
    target = school["students"]["first_b"]

    combined = logged_in_client.get(
        reverse("student-list"),
        {
            "level": school["level"].public_id,
            "grade": school["grade"].public_id,
            "section": school["sections"]["first_b"].public_id,
        },
    )
    searched = logged_in_client.get(
        reverse("student-list"),
        {"level": school["level"].public_id, "search": target.student_code},
    )
    mismatched = logged_in_client.get(
        reverse("student-list"),
        {"level": school["level"].public_id, "section": school["sections"]["other"].public_id},
    )

    assert _codes(combined) == [target.student_code]
    assert _codes(searched) == [target.student_code]
    assert _codes(mismatched) == []


@pytest.mark.api
@pytest.mark.django_db
def test_filters_do_not_widen_the_actor_scope(logged_in_client, school):
    _grant(logged_in_client.user, section=school["sections"]["first_a"])

    response = logged_in_client.get(reverse("student-list"), {"level": school["level"].public_id})

    assert _codes(response) == _expected(school, "first_a")


@pytest.mark.api
@pytest.mark.django_db
def test_malformed_identifier_is_a_bad_request(logged_in_client):
    _grant(logged_in_client.user, module_key="students")

    response = logged_in_client.get(reverse("student-list"), {"grade": "not-a-uuid"})

    assert response.status_code == 400
