import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from tests.factories.identity import UserFactory


@pytest.mark.api
@pytest.mark.postgres
@pytest.mark.django_db
def test_me_without_session_returns_anonymous_payload(client):
    response = client.get(reverse("auth-me"))

    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "user": None}


@pytest.mark.api
@pytest.mark.postgres
@pytest.mark.security
@pytest.mark.django_db
def test_login_and_logout_roundtrip(client):
    user = UserFactory(password="demo-pass-123")

    login_response = client.post(
        reverse("auth-login"),
        {"username": user.username, "password": "demo-pass-123"},
    )
    assert login_response.status_code == 200
    assert "password" not in login_response.json()

    me_response = client.get(reverse("auth-me"))
    assert me_response.status_code == 200
    assert me_response.json()["authenticated"] is True

    logout_response = client.post(reverse("auth-logout"))
    assert logout_response.status_code == 204

    me_after_logout = client.get(reverse("auth-me"))
    assert me_after_logout.status_code == 200
    assert me_after_logout.json()["authenticated"] is False


@pytest.mark.api
@pytest.mark.security
@pytest.mark.django_db
def test_inactive_user_cannot_login(client):
    user_model = get_user_model()
    user = UserFactory(password="demo-pass-123")
    user.is_active = False
    user.status = user_model.AccountStatus.DISABLED
    user.save(update_fields=["is_active", "status"])

    response = client.post(
        reverse("auth-login"),
        {"username": user.username, "password": "demo-pass-123"},
    )

    assert response.status_code == 400
