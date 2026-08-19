import pytest
from django.urls import reverse
from django.utils import timezone

from apps.people.models import Person
from apps.students.models import Guardian, StudentGuardianRelation
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.people import PersonFactory
from tests.factories.students import (
    GuardianFactory,
    StudentFactory,
    StudentGuardianRelationFactory,
)


@pytest.fixture
def logged_in_client(client):
    user = UserFactory(password="test-pass-123")
    client.login(username=user.username, password="test-pass-123")
    client.user = user
    return client


def _grant_student_permission(user, codename, student):
    permission = PermissionFactory(codename=codename)
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    return ScopeGrantFactory(assignment=assignment, student=student)


@pytest.mark.api
@pytest.mark.django_db
def test_create_guardian(logged_in_client):
    person_count = Person.objects.count()
    payload = {
        "person": {
            "first_name": "Rosa",
            "last_name": "Garcia",
            "email": "rosa.garcia@example.test",
            "phone_number": "55501234",
        },
    }

    response = logged_in_client.post(
        reverse("guardian-list"), payload, content_type="application/json"
    )

    assert response.status_code == 201
    data = response.json()
    assert data["is_active"] is True
    assert isinstance(data["person"], dict)
    assert data["person"]["first_name"] == "Rosa"
    assert data["person"]["last_name"] == "Garcia"
    assert Guardian.objects.filter(pk=data["id"]).exists()
    assert Person.objects.count() == person_count + 1


@pytest.mark.api
@pytest.mark.django_db
def test_list_guardians_is_paginated(logged_in_client):
    GuardianFactory.create_batch(3)

    response = logged_in_client.get(reverse("guardian-list"))

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data
    assert data["count"] == Guardian.objects.count()


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_guardian(logged_in_client):
    guardian = GuardianFactory()

    response = logged_in_client.get(reverse("guardian-detail", args=[guardian.pk]))

    assert response.status_code == 200
    assert response.json()["id"] == guardian.pk


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_missing_guardian_returns_404(logged_in_client):
    response = logged_in_client.get(reverse("guardian-detail", args=[999999]))

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_update_guardian_ignores_nested_person_changes(logged_in_client):
    guardian = GuardianFactory()
    other_person = PersonFactory()

    response = logged_in_client.patch(
        reverse("guardian-detail", args=[guardian.pk]),
        {"person": {"first_name": other_person.first_name}},
        content_type="application/json",
    )

    assert response.status_code == 200
    guardian.refresh_from_db()
    assert guardian.person_id != other_person.pk


@pytest.mark.api
@pytest.mark.django_db
def test_deactivate_guardian_via_delete_is_soft(logged_in_client):
    guardian = GuardianFactory()

    response = logged_in_client.delete(reverse("guardian-detail", args=[guardian.pk]))

    assert response.status_code == 204
    guardian.refresh_from_db()
    assert guardian.is_active is False
    assert Guardian.objects.filter(pk=guardian.pk).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_unauthenticated_request_to_guardian_list_is_rejected(client):
    response = client.get(reverse("guardian-list"))

    assert response.status_code == 403


@pytest.mark.api
@pytest.mark.django_db
def test_create_student_guardian_relation(logged_in_client):
    student = StudentFactory()
    guardian = GuardianFactory()
    _grant_student_permission(logged_in_client.user, "student_edit_basic", student)

    response = logged_in_client.post(
        reverse("student-guardian-relation-list"),
        {
            "student": student.pk,
            "guardian": guardian.pk,
            "relationship_label": "Madre",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["student"] == student.pk
    assert data["guardian"] == guardian.pk
    assert data["guardian_detail"]["id"] == guardian.pk
    assert data["guardian_detail"]["person"]["first_name"] == guardian.person.first_name
    assert data["relationship_label"] == "Madre"
    assert data["is_primary"] is True
    assert data["ends_at"] is None
    assert StudentGuardianRelation.objects.filter(pk=data["id"]).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_list_student_guardian_relations_is_paginated(logged_in_client):
    relations = StudentGuardianRelationFactory.create_batch(3)
    scope_grant = _grant_student_permission(
        logged_in_client.user,
        "student_view_basic",
        relations[0].student,
    )
    for relation in relations[1:]:
        ScopeGrantFactory(assignment=scope_grant.assignment, student=relation.student)

    response = logged_in_client.get(reverse("student-guardian-relation-list"))

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "count" in data
    assert data["count"] == StudentGuardianRelation.objects.count()
    assert data["results"][0]["guardian_detail"]["person"]["first_name"]


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_student_guardian_relation(logged_in_client):
    relation = StudentGuardianRelationFactory()
    _grant_student_permission(logged_in_client.user, "student_view_basic", relation.student)

    response = logged_in_client.get(reverse("student-guardian-relation-detail", args=[relation.pk]))

    assert response.status_code == 200
    assert response.json()["id"] == relation.pk


@pytest.mark.api
@pytest.mark.django_db
def test_retrieve_missing_student_guardian_relation_returns_404(logged_in_client):
    _grant_student_permission(logged_in_client.user, "student_view_basic", StudentFactory())

    response = logged_in_client.get(reverse("student-guardian-relation-detail", args=[999999]))

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.django_db
def test_direct_student_guardian_relation_update_is_not_available(logged_in_client):
    relation = StudentGuardianRelationFactory(relationship_label="Padre")

    response = logged_in_client.patch(
        reverse("student-guardian-relation-detail", args=[relation.pk]),
        {"relationship_label": "Tutor"},
        content_type="application/json",
    )

    assert response.status_code == 405
    relation.refresh_from_db()
    assert relation.relationship_label == "Padre"


@pytest.mark.api
@pytest.mark.django_db
def test_ending_primary_student_guardian_relation_requires_replacement(logged_in_client):
    relation = StudentGuardianRelationFactory(ends_at=None)
    _grant_student_permission(logged_in_client.user, "student_edit_basic", relation.student)

    response = logged_in_client.post(
        reverse("student-guardian-relation-end", args=[relation.pk]),
        content_type="application/json",
    )

    assert response.status_code == 400
    relation.refresh_from_db()
    assert relation.ends_at is None
    assert StudentGuardianRelation.objects.filter(pk=relation.pk).exists()


@pytest.mark.api
@pytest.mark.django_db
def test_end_student_guardian_relation_with_replacement(logged_in_client):
    relation = StudentGuardianRelationFactory(ends_at=None)
    replacement = StudentGuardianRelationFactory(
        student=relation.student,
        is_primary=False,
        ends_at=None,
    )
    _grant_student_permission(logged_in_client.user, "student_edit_basic", relation.student)

    response = logged_in_client.post(
        reverse("student-guardian-relation-end", args=[relation.pk]),
        {"replacement_relation": replacement.pk},
        content_type="application/json",
    )

    assert response.status_code == 200
    relation.refresh_from_db()
    replacement.refresh_from_db()
    assert relation.ends_at == timezone.localdate()
    assert relation.is_primary is False
    assert replacement.is_primary is True


@pytest.mark.api
@pytest.mark.django_db
def test_make_student_guardian_relation_primary(logged_in_client):
    current_primary = StudentGuardianRelationFactory(ends_at=None)
    relation = StudentGuardianRelationFactory(
        student=current_primary.student,
        is_primary=False,
        ends_at=None,
    )
    _grant_student_permission(logged_in_client.user, "student_edit_basic", relation.student)

    response = logged_in_client.post(
        reverse("student-guardian-relation-make-primary", args=[relation.pk]),
    )

    assert response.status_code == 200
    current_primary.refresh_from_db()
    relation.refresh_from_db()
    assert current_primary.is_primary is False
    assert relation.is_primary is True


@pytest.mark.api
@pytest.mark.django_db
def test_create_student_guardian_relation_missing_student_is_rejected(logged_in_client):
    guardian = GuardianFactory()

    response = logged_in_client.post(
        reverse("student-guardian-relation-list"),
        {
            "student": 999999,
            "guardian": guardian.pk,
            "relationship_label": "Madre",
        },
    )

    assert response.status_code == 400
    detail = response.json()["error"]["detail"]
    assert "student" in detail


@pytest.mark.api
@pytest.mark.django_db
def test_unauthenticated_request_to_relation_list_is_rejected(client):
    response = client.get(reverse("student-guardian-relation-list"))

    assert response.status_code == 403


@pytest.mark.api
@pytest.mark.django_db
def test_relation_list_and_detail_require_student_view_scope(logged_in_client):
    allowed_relation = StudentGuardianRelationFactory()
    denied_relation = StudentGuardianRelationFactory()

    assert logged_in_client.get(reverse("student-guardian-relation-list")).status_code == 403

    _grant_student_permission(
        logged_in_client.user,
        "student_view_basic",
        allowed_relation.student,
    )
    response = logged_in_client.get(reverse("student-guardian-relation-list"))

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["id"] == allowed_relation.pk
    assert (
        logged_in_client.get(
            reverse("student-guardian-relation-detail", args=[denied_relation.pk])
        ).status_code
        == 404
    )


@pytest.mark.api
@pytest.mark.django_db
def test_relation_mutations_require_student_edit_scope(logged_in_client):
    relation = StudentGuardianRelationFactory()
    guardian = GuardianFactory()

    create_response = logged_in_client.post(
        reverse("student-guardian-relation-list"),
        {
            "student": relation.student_id,
            "guardian": guardian.pk,
            "relationship_label": "Tutor",
        },
    )
    primary_response = logged_in_client.post(
        reverse("student-guardian-relation-make-primary", args=[relation.pk]),
    )
    end_response = logged_in_client.post(
        reverse("student-guardian-relation-end", args=[relation.pk]),
    )

    assert create_response.status_code == 403
    assert primary_response.status_code == 403
    assert end_response.status_code == 403
