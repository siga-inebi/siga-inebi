import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse


@pytest.mark.django_db
def test_health_endpoint(client):
    response = client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.django_db
def test_database_health_endpoint(client):
    response = client.get(reverse("health-database"))
    assert response.status_code == 200
    assert response.json()["service"] == "database"


@pytest.mark.django_db
def test_auth_me_requires_login(client):
    response = client.get(reverse("auth-me"))
    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "user": None}


@pytest.mark.django_db
def test_login_and_me(client):
    user_model = get_user_model()
    user = user_model.objects.create_user(username="demo", password="demo-pass")

    response = client.post(reverse("auth-login"), {"username": "demo", "password": "demo-pass"})
    assert response.status_code == 200
    assert response.json()["username"] == user.username

    me = client.get(reverse("auth-me"))
    assert me.status_code == 200
    assert me.json()["authenticated"] is True
    assert me.json()["user"]["username"] == "demo"
