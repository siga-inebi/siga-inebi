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
    """
    The probe reports the outage as 503 with a readable body. It used to let the
    driver error escape, which produced an unhandled 500 and an HTML debug page
    that no monitoring system can parse.
    """
    with patch("config.api.views.connection.cursor", side_effect=OperationalError("db down")):
        response = client.get(reverse("health-database"))

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "service": "database"}


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
def test_database_health_failure_never_leaks_an_html_error_page(client):
    """A debug page would expose the traceback and settings of the running app."""
    with patch("config.api.views.connection.cursor", side_effect=OperationalError("secret dsn")):
        response = client.get(reverse("health-database"))

    assert response["Content-Type"].startswith("application/json")
    assert b"secret dsn" not in response.content
    assert b"Traceback" not in response.content
