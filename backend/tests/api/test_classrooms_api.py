import pytest
from django.urls import reverse

from apps.academics.models import Classroom
from tests.factories.academic import CampusFactory, ClassroomFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def _items(response):
    return response.json()["results"]


def test_classroom_crud_keeps_code_and_campus_immutable(auth_client, institution):
    campus = CampusFactory(institution=institution, code="CENTRAL")

    created = auth_client.post(
        reverse("classroom-list-create"),
        {
            "campus_id": str(campus.public_id),
            "name": "Laboratorio de ciencias",
            "code": "lab-01",
            "location": "Edificio A",
            "capacity": 28,
        },
        content_type="application/json",
    )

    assert created.status_code == 201
    body = created.json()
    assert body["code"] == "LAB-01"
    assert body["campus"]["public_id"] == str(campus.public_id)

    updated = auth_client.patch(
        reverse("classroom-detail", args=[body["public_id"]]),
        {"name": "Laboratorio de ciencias naturales", "capacity": 30},
        content_type="application/json",
    )

    assert updated.status_code == 200
    assert updated.json()["code"] == "LAB-01"
    assert updated.json()["campus"]["public_id"] == str(campus.public_id)
    assert updated.json()["capacity"] == 30


def test_classroom_code_is_unique_per_campus(auth_client, institution):
    campus = CampusFactory(institution=institution)
    ClassroomFactory(campus=campus, code="A-101")

    duplicate = auth_client.post(
        reverse("classroom-list-create"),
        {"campus_id": str(campus.public_id), "name": "Otra aula", "code": "a-101"},
        content_type="application/json",
    )

    assert duplicate.status_code == 400
    assert "ya existe" in duplicate.json()["error"]["detail"]


def test_classroom_history_is_preserved_by_logical_deactivation(auth_client, institution):
    campus = CampusFactory(institution=institution)
    active = ClassroomFactory(campus=campus, code="A-101")
    inactive = ClassroomFactory(campus=campus, code="A-102")

    deleted = auth_client.delete(reverse("classroom-detail", args=[inactive.public_id]))
    default_list = auth_client.get(reverse("classroom-list-create"))
    history_list = auth_client.get(reverse("classroom-list-create"), {"include_inactive": "true"})

    assert deleted.status_code == 204
    assert [row["public_id"] for row in _items(default_list)] == [str(active.public_id)]
    assert {row["public_id"] for row in _items(history_list)} == {
        str(active.public_id),
        str(inactive.public_id),
    }
    inactive.refresh_from_db()
    assert inactive.is_active is False
    assert Classroom.objects.filter(pk=inactive.pk).exists()


def test_classroom_of_another_institution_is_not_exposed(auth_client, institution):
    foreign = ClassroomFactory()

    response = auth_client.get(reverse("classroom-detail", args=[foreign.public_id]))

    assert response.status_code == 404
