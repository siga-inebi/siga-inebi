import uuid
from datetime import date

import pytest
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.people.models import Person
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.people import PersonFactory
from tests.factories.students import GuardianFactory, StudentFactory
from tests.factories.teachers import TeacherFactory

PERSON_FIELDS = (
    "first_name",
    "last_name",
    "email",
    "phone_number",
    "institutional_identifier",
    "cui",
    "birth_date",
    "sex",
    "nationality",
    "address",
    "department",
    "municipality",
)


@pytest.fixture
def logged_in_client(client):
    user = UserFactory(password="test-pass-123")
    assignment = RoleAssignmentFactory(
        user=user,
        role=RoleFactory(permissions=[PermissionFactory(codename="person_edit")]),
    )
    ScopeGrantFactory(assignment=assignment, module_key="identity")
    client.login(username=user.username, password="test-pass-123")
    client.user = user
    return client


@pytest.mark.api
@pytest.mark.django_db
def test_create_person(logged_in_client):
    payload = {
        "first_name": "Ana",
        "last_name": "Gomez",
        "email": "ana.gomez@example.test",
        "phone_number": "5551234567",
        "institutional_identifier": "INEBI-001",
    }

    response = logged_in_client.post(reverse("person-list"), payload)

    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Ana"
    assert data["is_active"] is True
    assert "id" not in data
    assert Person.objects.filter(public_id=data["public_id"]).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_create_person_requires_first_and_last_name(logged_in_client):
    response = logged_in_client.post(reverse("person-list"), {})

    assert response.status_code == 400
    detail = response.json()["error"]["detail"]
    assert "first_name" in detail
    assert "last_name" in detail


@pytest.mark.api
@pytest.mark.django_db
def test_list_people_is_paginated(logged_in_client):
    PersonFactory.create_batch(3)

    response = logged_in_client.get(reverse("person-list"))

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data
    assert data["count"] == Person.objects.count()


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_person(logged_in_client):
    person = PersonFactory()

    response = logged_in_client.get(reverse("person-detail", args=[person.public_id]))

    assert response.status_code == 200
    assert response.json()["public_id"] == str(person.public_id)


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_missing_person_returns_404(logged_in_client):
    response = logged_in_client.get(reverse("person-detail", args=[uuid.uuid4()]))

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_update_person(logged_in_client):
    person = PersonFactory(first_name="Old")

    response = logged_in_client.patch(
        reverse("person-detail", args=[person.public_id]),
        {"first_name": "New"},
        content_type="application/json",
    )

    assert response.status_code == 200
    person.refresh_from_db()
    assert person.first_name == "New"


@pytest.mark.api
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sex", "male"),
        ("nationality", "Salvadoreña"),
        ("address", "Calle de prueba 42"),
        ("department", "Quetzaltenango"),
        ("municipality", "Salcaja"),
    ],
)
def test_patch_person_persists_profile_field_without_changing_omitted_data(
    logged_in_client, field, value
):
    person = PersonFactory(
        cui="1234567890123",
        birth_date=date(2015, 3, 1),
        sex="female",
        nationality="Guatemalteca",
        address="Direccion anterior",
        department="Guatemala",
        municipality="Guatemala",
    )
    original = {name: getattr(person, name) for name in PERSON_FIELDS}
    url = reverse("person-detail", args=[person.public_id])

    response = logged_in_client.patch(url, {field: value}, content_type="application/json")

    assert response.status_code == 200
    person.refresh_from_db()
    assert {name: getattr(person, name) for name in original} == {**original, field: value}
    retrieved = logged_in_client.get(url).json()
    assert retrieved[field] == value
    assert "cui" not in retrieved
    assert "birth_date" not in retrieved
    event = AuditEvent.objects.get(action="people.person.updated")
    assert str(event.actor_id) == logged_in_client.session["_auth_user_id"]
    assert event.context["fields"] == [field]
    assert set(event.context) <= {"fields", "ip_address", "path", "user_agent"}


@pytest.mark.api
@pytest.mark.django_db
@pytest.mark.parametrize(
    ("factory", "route"),
    [
        (StudentFactory, "student-detail"),
        (TeacherFactory, "teacher-detail"),
        (GuardianFactory, "guardian-detail"),
    ],
)
def test_edited_person_profile_is_returned_by_community_detail(auth_client, factory, route):
    profile = factory()
    assignment = RoleAssignmentFactory(
        user=auth_client.user,
        role=RoleFactory(permissions=[PermissionFactory(codename="person_edit")]),
    )
    ScopeGrantFactory(assignment=assignment, module_key="identity")
    if factory is StudentFactory:
        permission = PermissionFactory(codename="student_view_basic")
        assignment = RoleAssignmentFactory(
            user=auth_client.user, role=RoleFactory(permissions=[permission])
        )
        ScopeGrantFactory(assignment=assignment, student=profile)
    changes = {
        "sex": "male",
        "nationality": "Salvadoreña",
        "address": "Calle de prueba 42",
        "department": "Quetzaltenango",
        "municipality": "Salcaja",
    }

    updated = auth_client.patch(
        reverse("person-detail", args=[profile.person.public_id]),
        changes,
        content_type="application/json",
    )
    assert updated.status_code == 200
    response = auth_client.get(reverse(route, args=[profile.pk]))

    assert response.status_code == 200
    person_data = response.json()["person"]
    assert {name: person_data[name] for name in changes} == changes
    assert "cui" not in person_data
    assert "birth_date" not in person_data


@pytest.mark.api
@pytest.mark.django_db
def test_anonymous_person_profile_patch_is_rejected_without_changes(client):
    person = PersonFactory(address="Direccion anterior")

    response = client.patch(
        reverse("person-detail", args=[person.public_id]),
        {"address": "Direccion nueva"},
        content_type="application/json",
    )

    assert response.status_code == 403
    person.refresh_from_db()
    assert person.address == "Direccion anterior"
    assert not AuditEvent.objects.filter(action="people.person.updated").exists()


@pytest.mark.api
@pytest.mark.django_db
def test_invalid_profile_patch_does_not_save_other_fields(logged_in_client):
    person = PersonFactory(sex="female", address="Direccion anterior")

    response = logged_in_client.patch(
        reverse("person-detail", args=[person.public_id]),
        {"sex": "invalid", "address": "Direccion nueva"},
        content_type="application/json",
    )

    assert response.status_code == 400
    person.refresh_from_db()
    assert person.sex == "female"
    assert person.address == "Direccion anterior"
    assert not AuditEvent.objects.filter(action="people.person.updated").exists()


@pytest.mark.api
@pytest.mark.django_db
def test_deactivate_person_via_delete_is_soft(logged_in_client):
    person = PersonFactory()

    response = logged_in_client.delete(reverse("person-detail", args=[person.public_id]))

    assert response.status_code == 204
    person.refresh_from_db()
    assert person.is_active is False
    assert Person.objects.filter(pk=person.pk).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_unauthenticated_request_is_rejected(client):
    response = client.get(reverse("person-list"))

    assert response.status_code == 403


@pytest.mark.api
@pytest.mark.django_db
def test_create_person_never_exposes_birth_date(logged_in_client):
    payload = {
        "first_name": "Ana",
        "last_name": "Gomez",
        "birth_date": "2015-03-01",
    }

    response = logged_in_client.post(reverse("person-list"), payload)

    assert response.status_code == 201
    data = response.json()
    assert "birth_date" not in data
    assert data["is_minor"] is True
    person = Person.objects.get(public_id=data["public_id"])
    assert person.birth_date == date(2015, 3, 1)


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_person_never_exposes_birth_date(logged_in_client):
    person = PersonFactory(birth_date=date(1990, 1, 1))

    response = logged_in_client.get(reverse("person-detail", args=[person.public_id]))

    assert response.status_code == 200
    data = response.json()
    assert "birth_date" not in data
    assert data["is_minor"] is False
