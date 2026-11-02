import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.academics.models import AcademicCycle, Institution
from apps.identity.atomic_permissions import ATOMIC_PERMISSION_CODENAMES
from apps.identity.models import Role
from apps.people.models import Person


@pytest.mark.integration
@pytest.mark.django_db
def test_create_initial_admin_provisions_only_the_user():
    call_command(
        "create_initial_admin",
        username="root",
        email="root@example.test",
        password="initial-pass-123",
    )

    user = get_user_model().objects.get(username="root")
    assert user.is_superuser and user.is_staff
    assert user.status == user.AccountStatus.ACTIVE
    assert user.check_password("initial-pass-123") is True
    assert user.person.email == "root@example.test"

    # La base queda vacia de datos institucionales: solo la persona y la cuenta.
    assert Institution.objects.count() == 0
    assert AcademicCycle.objects.count() == 0
    assert Person.objects.count() == 1


@pytest.mark.integration
@pytest.mark.django_db
def test_create_initial_admin_is_idempotent_and_rotates_password():
    args = {"username": "root", "email": "root@example.test"}
    call_command("create_initial_admin", **args, password="first-pass")
    call_command("create_initial_admin", **args, password="second-pass")

    user = get_user_model().objects.get(username="root")
    assert user.check_password("first-pass") is False
    assert user.check_password("second-pass") is True
    assert get_user_model().objects.count() == 1
    assert Role.objects.filter(slug="system-administrator").count() == 1


@pytest.mark.integration
@pytest.mark.django_db
def test_create_initial_admin_role_covers_every_atomic_permission():
    call_command(
        "create_initial_admin",
        username="root",
        email="root@example.test",
        password="initial-pass-123",
    )

    admin = get_user_model().objects.get(username="root")
    missing = [
        codename
        for codename in ATOMIC_PERMISSION_CODENAMES
        if not admin.has_atomic_permission(codename)
    ]
    assert missing == []


@pytest.mark.integration
@pytest.mark.django_db
def test_create_initial_admin_requires_username_email_and_password():
    with pytest.raises(CommandError):
        call_command("create_initial_admin", username="", email="", password="")
