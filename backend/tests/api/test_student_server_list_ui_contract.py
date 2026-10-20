"""#632 E3/E10: existing API contract consumed by the paginated student UI."""

import pytest
from django.urls import reverse

from apps.people.models import Person
from apps.students.models import Student
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def grant_reader(client, **scope):
    assignment = RoleAssignmentFactory(
        user=client.user,
        role=RoleFactory(permissions=[PermissionFactory(codename="student_view_basic")]),
    )
    ScopeGrantFactory(assignment=assignment, **scope)


def test_filtered_roster_beyond_one_thousand_and_server_page_size_limit(auth_client):
    grant_reader(auth_client, module_key="students")
    people = Person.objects.bulk_create(
        [Person(first_name="ListadoDemo", last_name=f"Prueba {index:04d}") for index in range(1001)]
    )
    Student.objects.bulk_create(
        [
            Student(person=person, student_code=f"DEMO-632-{index:04d}", status="active")
            for index, person in enumerate(people)
        ]
    )
    StudentFactory(student_code="DEMO-632-EXCLUIDO", status="pre_enrolled")
    StudentFactory(student_code="DEMO-632-DESACTIVADO", status="active", is_active=False)
    params = {"search": "DEMO-632", "status": "active", "page_size": 1000}
    first = auth_client.get(reverse("student-list"), params)
    assert first.status_code == 200
    data = first.json()
    assert data["count"] == 1001
    assert len(data["results"]) == 100
    assert data["results"][0]["student_code"] == "DEMO-632-0000"
    assert "search=DEMO-632" in data["next"]
    last = auth_client.get(reverse("student-list"), {**params, "page": 11})
    assert last.status_code == 200
    assert last.json()["count"] == 1001
    assert [row["student_code"] for row in last.json()["results"]] == ["DEMO-632-1000"]
    assert last.json()["next"] is None
    included = auth_client.get(reverse("student-list"), {**params, "include_inactive": "true"})
    assert included.json()["count"] == 1002


def test_code_status_and_inactive_filters_keep_scope_and_private_fields(auth_client):
    allowed = StudentFactory(student_code="DEMO-632-ALLOWED", status="inactive", is_active=False)
    StudentFactory(student_code="DEMO-632-HIDDEN", status="inactive", is_active=False)
    grant_reader(auth_client, student=allowed)
    params = {"search": "DEMO-632", "status": "inactive", "page_size": 50}
    assert auth_client.get(reverse("student-list"), params).json()["count"] == 0
    response = auth_client.get(reverse("student-list"), {**params, "include_inactive": "true"})
    assert response.status_code == 200
    assert response.json()["count"] == 1
    row = response.json()["results"][0]
    assert row["public_id"] == str(allowed.public_id)
    assert "cui" not in row["person"]
    assert "birth_date" not in row["person"]
