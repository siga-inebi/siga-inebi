"""#632 T2/T4: server list and canonical positions for the teachers UI."""

import pytest
from django.test import Client
from django.urls import path, reverse
from drf_spectacular.generators import SchemaGenerator

from apps.people.models import Person
from apps.teachers.api.views import TeacherPositionListView
from apps.teachers.models import Teacher
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_position_catalogue_schema_matches_the_unpaginated_response():
    schema = SchemaGenerator(
        patterns=[path("positions/", TeacherPositionListView.as_view())]
    ).get_schema(request=None, public=True)
    operation = schema["paths"]["/positions/"]["get"]
    assert not operation.get("parameters")
    response = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert response["type"] == "array"
    assert response["items"]["$ref"].endswith("/TeacherPosition")


def test_position_catalogue_matches_model_and_needs_no_teacher_rows(auth_client):
    assert not Teacher.objects.exists()
    response = auth_client.get(reverse("teacher-position-list"))
    assert response.status_code == 200
    assert response.json() == [
        {"value": value, "label": label} for value, label in Teacher.Position.choices
    ]
    assert not Teacher.objects.exists()


def test_position_catalogue_rejects_anonymous_reads_and_authenticated_writes(auth_client):
    url = reverse("teacher-position-list")
    assert Client().get(url).status_code == 403
    assert auth_client.post(url, {"value": "Otro puesto"}).status_code == 405


def test_code_and_position_filters_before_pagination_beyond_one_thousand(auth_client):
    people = Person.objects.bulk_create(
        [
            Person(first_name="DocenteSintetico", last_name=f"Prueba {index:04d}")
            for index in range(1001)
        ]
    )
    Teacher.objects.bulk_create(
        [
            Teacher(
                person=person,
                employee_code=f"T2-DEMO-{index:04d}",
                specialty="Especialidad de prueba",
                position=Teacher.Position.DOCENTE_TITULADO,
            )
            for index, person in enumerate(people)
        ]
    )
    TeacherFactory(employee_code="T2-DEMO-OTRO", position=Teacher.Position.ADMINISTRATIVO)
    TeacherFactory(
        employee_code="T2-DEMO-DESACTIVADO",
        position=Teacher.Position.DOCENTE_TITULADO,
        is_active=False,
    )
    params = {
        "search": "T2-DEMO",
        "position": Teacher.Position.DOCENTE_TITULADO,
        "page_size": 1000,
    }
    first = auth_client.get(reverse("teacher-list"), params)
    assert first.status_code == 200
    data = first.json()
    assert data["count"] == 1001
    assert len(data["results"]) == 100
    assert data["results"][0]["employee_code"] == "T2-DEMO-0000"
    assert "cui" not in data["results"][0]["person"]
    assert "birth_date" not in data["results"][0]["person"]
    last = auth_client.get(reverse("teacher-list"), {**params, "page": 11})
    assert last.status_code == 200
    assert last.json()["count"] == 1001
    assert [row["employee_code"] for row in last.json()["results"]] == ["T2-DEMO-1000"]
    assert last.json()["next"] is None
    included = auth_client.get(reverse("teacher-list"), {**params, "include_inactive": "true"})
    assert included.json()["count"] == 1002
