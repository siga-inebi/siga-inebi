from unittest.mock import patch

import pytest
from django.db import OperationalError
from django.urls import reverse


@pytest.mark.api
@pytest.mark.postgres
@pytest.mark.django_db
def test_health_endpoint(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.api
@pytest.mark.postgres
@pytest.mark.django_db
def test_database_health_endpoint(client):
    response = client.get(reverse("health-database"))
    assert response.status_code == 200
    assert response.json()["service"] == "database"


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
def test_database_health_surfaces_postgresql_failure(client):
    client.raise_request_exception = False
    with patch("config.api.views.connection.cursor", side_effect=OperationalError("db down")):
        response = client.get(reverse("health-database"))

    assert response.status_code == 500
