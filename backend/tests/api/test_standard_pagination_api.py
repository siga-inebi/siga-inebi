"""
docs/ux-ui.md 1.1: una sola convencion de paginacion para toda la API.

`StandardPagination` es la clase por defecto, asi que cualquier listado
paginado acepta `page_size` (antes se ignoraba en silencio), lo acota a 100 y
conserva el sobre `count/next/previous/results`.
"""

import pytest
from django.conf import settings
from django.urls import reverse

from apps.common.pagination import MAX_PAGE_SIZE, StandardPagination
from apps.people.models import Person

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def _people(count):
    Person.objects.bulk_create(
        Person(first_name=f"Nombre{index:03d}", last_name="Prueba") for index in range(count)
    )


def test_standard_pagination_is_the_project_default():
    assert (
        settings.REST_FRAMEWORK["DEFAULT_PAGINATION_CLASS"]
        == "apps.common.pagination.StandardPagination"
    )
    assert StandardPagination.page_size == 25
    assert StandardPagination.page_size_query_param == "page_size"
    assert StandardPagination.max_page_size == MAX_PAGE_SIZE == 100


def test_list_uses_default_page_size_and_standard_envelope(auth_client):
    _people(30)

    payload = auth_client.get(reverse("person-list")).json()

    assert set(payload) == {"count", "next", "previous", "results"}
    assert len(payload["results"]) == 25
    assert payload["count"] >= 30
    assert "page=2" in payload["next"]


def test_list_honours_page_size_parameter(auth_client):
    _people(30)

    payload = auth_client.get(reverse("person-list"), {"page_size": 10, "page": 2}).json()

    assert len(payload["results"]) == 10
    assert "page_size=10" in payload["next"]
    assert payload["previous"] is not None


def test_page_size_is_capped_at_the_maximum(auth_client):
    _people(MAX_PAGE_SIZE + 5)

    payload = auth_client.get(reverse("person-list"), {"page_size": 1000}).json()

    assert len(payload["results"]) == MAX_PAGE_SIZE
    assert payload["next"] is not None


def test_invalid_page_size_falls_back_to_default(auth_client):
    _people(30)

    payload = auth_client.get(reverse("person-list"), {"page_size": "abc"}).json()

    assert len(payload["results"]) == 25
