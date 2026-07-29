import os

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.academics.models import Institution
from apps.identity.models import Role


@pytest.mark.integration
@pytest.mark.django_db
def test_seed_idempotent_and_uses_env_password(settings):
    os.environ["DEMO_ADMIN_USERNAME"] = "seed-admin"
    os.environ["DEMO_ADMIN_EMAIL"] = "seed-admin@example.test"
    os.environ["DEMO_ADMIN_PASSWORD"] = "seed-pass-123"

    call_command("seed_demo_data")
    call_command("seed_demo_data")

    assert Institution.objects.count() == 1
    assert Role.objects.filter(slug="system-administrator").count() == 1
    user = get_user_model().objects.get(username="seed-admin")
    assert user.check_password("seed-pass-123") is True


@pytest.mark.integration
@pytest.mark.security
def test_seed_command_has_no_hardcoded_demo_password():
    with open("apps/identity/management/commands/seed_demo_data.py", encoding="utf-8") as handle:
        contents = handle.read()

    assert "DEMO_ADMIN_PASSWORD" in contents
    assert "admin123" not in contents
