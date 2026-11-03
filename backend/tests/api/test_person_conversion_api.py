from datetime import date

import pytest
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.people.models import Person
from apps.students.models import Guardian, Student
from apps.teachers.models import Teacher
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.people import PersonFactory


def grant(user, codename, module):
    assignment = RoleAssignmentFactory(
        user=user, role=RoleFactory(permissions=[PermissionFactory(codename=codename)])
    )
    ScopeGrantFactory(assignment=assignment, module_key=module)


@pytest.fixture
def editor(client):
    user = UserFactory()
    client.force_login(user)
    grant(user, "person_edit", "identity")
    grant(user, "student_edit_basic", "students")
    return client


def profile_payload(person, kind):
    payload = {
        "person_public_id": str(person.public_id),
        "person": {
            "first_name": person.first_name,
            "last_name": person.last_name,
            "cui": "1234567890123",
            "birth_date": "2001-05-20",
            "sex": "female",
            "nationality": "Guatemalteca",
            "phone_number": "55500000",
            "address": "Direccion de prueba",
            "department": "Guatemala",
            "municipality": "Guatemala",
        },
    }
    if kind == "teacher":
        payload.update(specialty="Matematica", position=Teacher.Position.DOCENTE_TITULADO)
    return payload


@pytest.mark.api
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("kind", "route", "model"),
    [
        ("student", "student-list", Student),
        ("teacher", "teacher-list", Teacher),
        ("guardian", "guardian-list", Guardian),
    ],
)
def test_conversion_reuses_person_and_audits_completion(editor, kind, route, model):
    person = PersonFactory(cui=None, birth_date=None, phone_number="")
    before = Person.objects.count()

    response = editor.post(
        reverse(route), profile_payload(person, kind), content_type="application/json"
    )

    assert response.status_code == 201, response.content
    assert Person.objects.count() == before
    assert model.objects.get(person=person).person_id == person.pk
    assert response.json()["person"]["public_id"] == str(person.public_id)
    person.refresh_from_db()
    assert person.birth_date == date(2001, 5, 20)
    assert person.cui == "1234567890123"
    assert AuditEvent.objects.filter(action="people.person.profile_completed").count() == 1

    duplicate = editor.post(
        reverse(route), profile_payload(person, kind), content_type="application/json"
    )
    assert duplicate.status_code == 400
    assert model.objects.filter(person=person).count() == 1
    assert AuditEvent.objects.filter(action="people.person.profile_completed").count() == 1


@pytest.mark.api
@pytest.mark.django_db
def test_conversion_can_use_existing_complete_person_without_reentering_data(editor):
    person = PersonFactory(
        cui="1234567890123",
        birth_date=date(2001, 5, 20),
        sex="female",
        nationality="Guatemalteca",
        phone_number="55500000",
        address="Direccion",
        department="Guatemala",
        municipality="Guatemala",
    )
    response = editor.post(
        reverse("guardian-list"),
        {"person_public_id": str(person.public_id)},
        content_type="application/json",
    )
    assert response.status_code == 201, response.content
    assert Guardian.objects.get(person=person)


@pytest.mark.api
@pytest.mark.django_db
def test_conversion_requires_person_edit_scope_and_leaves_person_untouched(client):
    user = UserFactory()
    client.force_login(user)
    person = PersonFactory(cui=None, birth_date=None)
    payload = profile_payload(person, "guardian")

    response = client.post(reverse("guardian-list"), payload, content_type="application/json")

    assert response.status_code == 403
    person.refresh_from_db()
    assert person.cui is None
    assert not Guardian.objects.filter(person=person).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_person_registry_search_and_profile_indicators_need_scoped_permission(editor):
    person = PersonFactory(first_name="Busqueda", last_name="Especial", cui="1234567890123")
    Guardian.objects.create(person=person)

    response = editor.get(reverse("person-list"), {"search": "Busqueda"})

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["profiles"] == {
        "student": False,
        "teacher": False,
        "guardian": True,
        "account": False,
    }
    assert "cui" not in response.json()["results"][0]
    assert "birth_date" not in response.json()["results"][0]
