"""#632: list filters run on the server before pagination and preserve scope."""

import pytest
from django.urls import reverse

from apps.students.models import Student
from apps.teachers.models import Teacher
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.people import PersonFactory
from tests.factories.students import GuardianFactory, StudentFactory
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

CATALOGUES = [
    ("person-list", PersonFactory),
    ("teacher-list", TeacherFactory),
    ("student-list", StudentFactory),
    ("guardian-list", GuardianFactory),
]


@pytest.fixture
def reader(auth_client):
    assignment = RoleAssignmentFactory(
        user=auth_client.user,
        role=RoleFactory(permissions=[PermissionFactory(codename="student_view_basic")]),
    )
    ScopeGrantFactory(assignment=assignment, module_key="students")
    return auth_client


def named(factory, **kwargs):
    prefix = "" if factory is PersonFactory else "person__"
    return factory(**{f"{prefix}{key}": value for key, value in kwargs.items()})


def response_id(row, factory):
    # Guardians retain their existing integer-only identifier contract.
    return str(row["id"] if factory is GuardianFactory else row["public_id"])


def instance_id(instance, factory):
    return str(instance.pk if factory is GuardianFactory else instance.public_id)


@pytest.mark.parametrize(("route", "factory"), CATALOGUES)
def test_active_default_and_explicit_inactive_opt_in(reader, route, factory):
    active = named(factory, first_name="FiltroDemo")
    inactive = named(factory, first_name="FiltroDemo")
    inactive.is_active = False
    inactive.save(update_fields=["is_active"])
    for value in (None, "false", "0"):
        params = {"search": "FiltroDemo"}
        if value is not None:
            params["include_inactive"] = value
        response = reader.get(reverse(route), params)
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response_id(response.json()["results"][0], factory) == instance_id(active, factory)
    for value in ("true", "1", "yes"):
        response = reader.get(reverse(route), {"search": "FiltroDemo", "include_inactive": value})
        assert response.status_code == 200
        assert {response_id(row, factory) for row in response.json()["results"]} == {
            instance_id(active, factory),
            instance_id(inactive, factory),
        }


@pytest.mark.parametrize(("route", "factory"), CATALOGUES)
def test_search_by_name_cui_and_code(reader, route, factory):
    match = named(factory, first_name="Zafiro", last_name="Demostracion", cui="9876543210123")
    named(factory, first_name="Otra", last_name="Persona")
    person = match if factory is PersonFactory else match.person
    terms = ["zafiro demostracion", "9876543210123"]
    if factory is PersonFactory:
        person.institutional_identifier = "DEMO-IDENTIDAD-632"
        person.save(update_fields=["institutional_identifier"])
        terms.append(person.institutional_identifier)
    elif factory is StudentFactory:
        terms.append(match.student_code)
    elif factory is TeacherFactory:
        terms.append(match.employee_code)
    for term in terms:
        response = reader.get(reverse(route), {"search": term})
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response_id(response.json()["results"][0], factory) == instance_id(match, factory)
    assert reader.get(reverse(route), {"search": "SinCoincidencia632"}).json()["count"] == 0


@pytest.mark.parametrize(("route", "factory"), CATALOGUES)
def test_filter_before_pagination_and_deterministic_name_ties(reader, route, factory):
    for _ in range(26):
        named(factory, first_name="Distractor", last_name="A")
    selected = [named(factory, first_name="Seleccion632", last_name="Z") for _ in range(26)]
    params = {"search": "Seleccion632"}
    first = reader.get(reverse(route), params).json()
    second = reader.get(reverse(route), {**params, "page": 2}).json()
    assert first["count"] == second["count"] == 26
    assert len(first["results"]) == 25
    assert len(second["results"]) == 1
    ids = [response_id(row, factory) for row in first["results"] + second["results"]]
    assert len(set(ids)) == 26
    assert set(ids) == {instance_id(row, factory) for row in selected}
    assert reader.get(reverse(route), params).json() == first
    assert "search=Seleccion632" in first["next"]


@pytest.mark.parametrize(("route", "factory"), CATALOGUES)
@pytest.mark.parametrize("value", ["", "not-a-boolean"])
def test_invalid_inactive_parameter_returns_400(reader, route, factory, value):
    response = reader.get(reverse(route), {"include_inactive": value})
    assert response.status_code == 400
    assert "include_inactive" in response.json()["error"]["detail"]


@pytest.mark.parametrize(("route", "factory"), CATALOGUES)
def test_anonymous_cannot_search(client, route, factory):
    assert (
        client.get(reverse(route), {"search": "Demo", "include_inactive": "true"}).status_code
        == 403
    )


@pytest.mark.parametrize("status", Student.StudentStatus.values)
def test_student_status_is_independent_of_logical_deactivation(reader, status):
    selected = StudentFactory(status=status)
    StudentFactory(status=next(value for value in Student.StudentStatus.values if value != status))
    response = reader.get(reverse("student-list"), {"status": status})
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["public_id"] == str(selected.public_id)
    selected.is_active = False
    selected.save(update_fields=["is_active"])
    assert reader.get(reverse("student-list"), {"status": status}).json()["count"] == 0
    assert (
        reader.get(reverse("student-list"), {"status": status, "include_inactive": "true"}).json()[
            "count"
        ]
        == 1
    )


def test_teacher_position_combines_with_search_and_activity(reader):
    teacher = named(TeacherFactory, first_name="PuestoDemo")
    named(TeacherFactory, first_name="PuestoDemo")
    teacher.position = Teacher.Position.ADMINISTRATIVO
    teacher.save(update_fields=["position"])
    response = reader.get(
        reverse("teacher-list"),
        {"position": Teacher.Position.ADMINISTRATIVO, "search": "PuestoDemo"},
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["public_id"] == str(teacher.public_id)


@pytest.mark.parametrize(
    ("route", "param"), [("student-list", "status"), ("teacher-list", "position")]
)
@pytest.mark.parametrize("value", ["", "unknown"])
def test_invalid_domain_filter_returns_400(reader, route, param, value):
    response = reader.get(reverse(route), {param: value})
    assert response.status_code == 400
    assert param in response.json()["error"]["detail"]


def test_student_search_does_not_expand_scope(auth_client):
    allowed = named(StudentFactory, first_name="Alcance632")
    hidden = named(StudentFactory, first_name="Alcance632")
    hidden.is_active = False
    hidden.save(update_fields=["is_active"])
    assignment = RoleAssignmentFactory(
        user=auth_client.user,
        role=RoleFactory(permissions=[PermissionFactory(codename="student_view_basic")]),
    )
    ScopeGrantFactory(assignment=assignment, student=allowed)
    response = auth_client.get(
        reverse("student-list"),
        {"search": "Alcance632", "include_inactive": "true", "status": allowed.status},
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["public_id"] == str(allowed.public_id)
    assert (
        auth_client.get(
            reverse("student-list"), {"search": hidden.student_code, "include_inactive": "true"}
        ).json()["count"]
        == 0
    )


def test_student_search_requires_permission_and_scope(auth_client):
    url = reverse("student-list")
    assert auth_client.get(url, {"include_inactive": "true"}).status_code == 403
    RoleAssignmentFactory(
        user=auth_client.user,
        role=RoleFactory(permissions=[PermissionFactory(codename="student_view_basic")]),
        identity_scope=False,
    )
    assert auth_client.get(url, {"include_inactive": "true"}).status_code == 403


@pytest.mark.parametrize(("route", "factory"), CATALOGUES)
def test_inactive_detail_remains_available(reader, route, factory):
    instance = factory(is_active=False)
    detail = route.replace("-list", "-detail")
    identifier = instance.public_id if factory is PersonFactory else instance.pk
    response = reader.get(reverse(detail, args=[identifier]))
    assert response.status_code == 200
    assert response.json()["is_active"] is False
