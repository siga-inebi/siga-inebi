import pytest
from django.urls import reverse

from apps.audit.models import AuditEvent
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.students import StudentFactory, StudentObservationFactory


@pytest.fixture
def client_user(client):
    user = UserFactory(password="test-pass-123")
    client.login(username=user.username, password="test-pass-123")
    return client, user


def grant(user, student, *codenames):
    permissions = [PermissionFactory(codename=codename) for codename in codenames]
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=permissions))
    ScopeGrantFactory(assignment=assignment, student=student)


@pytest.mark.api
@pytest.mark.django_db
def test_authorized_actor_creates_and_reads_audited_observation(client_user):
    client, user = client_user
    student = StudentFactory()
    grant(user, student, "student_view_sensitive", "student_edit_basic")
    url = reverse("student-observation-list-create", args=[student.public_id])

    response = client.post(url, {"description": "Seguimiento pedagogico"})
    assert response.status_code == 201
    assert response.json()["description"] == "Seguimiento pedagogico"
    assert response.json()["author"] == user.username

    response = client.get(url)
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert AuditEvent.objects.filter(action="students.observation.list_read").exists()


@pytest.mark.api
@pytest.mark.django_db
def test_basic_access_without_sensitive_permission_is_denied(client_user):
    client, user = client_user
    student = StudentFactory()
    grant(user, student, "student_view_basic", "student_edit_basic")
    url = reverse("student-observation-list-create", args=[student.public_id])

    assert client.get(url).status_code == 403
    assert client.post(url, {"description": "No debe guardarse"}).status_code == 403


@pytest.mark.api
@pytest.mark.django_db
def test_sensitive_permissions_without_student_scope_are_denied(client_user):
    client, user = client_user
    allowed_student = StudentFactory()
    denied_student = StudentFactory()
    grant(user, allowed_student, "student_view_sensitive", "student_edit_basic")
    url = reverse("student-observation-list-create", args=[denied_student.public_id])

    assert client.get(url).status_code == 403
    assert client.post(url, {"description": "No debe guardarse"}).status_code == 403


@pytest.mark.api
@pytest.mark.django_db
def test_reading_an_observation_detail_is_audited(client_user):
    """RNF-AUD-003: reading one observation, not just listing them, is audited too."""
    client, user = client_user
    observation = StudentObservationFactory()
    grant(user, observation.student, "student_view_sensitive", "student_edit_basic")

    response = client.get(reverse("student-observation-detail", args=[observation.public_id]))

    assert response.status_code == 200
    event = AuditEvent.objects.latest("created_at")
    assert event.action == "students.observation.detail_read"
    assert event.context["student_id"] == observation.student_id
    assert event.actor_id == user.id


@pytest.mark.api
@pytest.mark.django_db
def test_observation_soft_delete_requires_edit_and_preserves_history(client_user):
    client, user = client_user
    observation = StudentObservationFactory()
    grant(user, observation.student, "student_view_sensitive", "student_edit_basic")

    response = client.delete(reverse("student-observation-detail", args=[observation.public_id]))

    assert response.status_code == 204
    observation.refresh_from_db()
    assert observation.is_active is False
