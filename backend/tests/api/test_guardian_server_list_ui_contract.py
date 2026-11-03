"""#632 G2: the guardian UI can traverse a filtered roster beyond 1,000 rows."""

import pytest
from django.urls import reverse

from apps.people.models import Person
from apps.students.models import Guardian
from tests.factories.students import GuardianFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_guardian_filtered_pagination_beyond_one_thousand(auth_client):
    people = Person.objects.bulk_create(
        [
            Person(first_name="EncargadoSintetico", last_name=f"Listado {index:04d}")
            for index in range(1001)
        ]
    )
    Guardian.objects.bulk_create([Guardian(person=person) for person in people])
    GuardianFactory(person__first_name="OtraPersona")
    GuardianFactory(person__first_name="EncargadoSintetico", is_active=False)
    params = {"search": "EncargadoSintetico", "page_size": 1000}
    first = auth_client.get(reverse("guardian-list"), params)
    assert first.status_code == 200
    data = first.json()
    assert data["count"] == 1001
    assert len(data["results"]) == 100
    assert data["results"][0]["person"]["last_name"] == "Listado 0000"
    assert "cui" not in data["results"][0]["person"]
    assert "birth_date" not in data["results"][0]["person"]
    last = auth_client.get(reverse("guardian-list"), {**params, "page": 11})
    assert last.status_code == 200
    assert last.json()["count"] == 1001
    assert [row["person"]["last_name"] for row in last.json()["results"]] == ["Listado 1000"]
    assert last.json()["next"] is None
    included = auth_client.get(reverse("guardian-list"), {**params, "include_inactive": "true"})
    assert included.json()["count"] == 1002


def test_guardian_page_disappearing_after_edit_can_restart_with_same_filter(auth_client):
    guardians = [GuardianFactory(person__first_name="FiltroG2") for _ in range(26)]
    params = {"search": "FiltroG2", "page": 2, "page_size": 25}
    assert auth_client.get(reverse("guardian-list"), params).status_code == 200
    person = guardians[-1].person
    person.first_name = "FueraDeFiltro"
    person.save(update_fields=["first_name"])
    assert auth_client.get(reverse("guardian-list"), params).status_code == 404
    restarted = auth_client.get(reverse("guardian-list"), {**params, "page": 1})
    assert restarted.status_code == 200
    assert restarted.json()["count"] == 25
    assert len(restarted.json()["results"]) == 25
