import os

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.academics.models import Campus, Grade, Institution, Level
from apps.identity.atomic_permissions import ATOMIC_PERMISSION_CODENAMES
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
@pytest.mark.django_db
def test_seed_uses_example_file_defaults_when_env_missing(monkeypatch):
    monkeypatch.delenv("DEMO_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("DEMO_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("DEMO_ADMIN_PASSWORD", raising=False)

    call_command("seed_demo_data")

    user = get_user_model().objects.get(username="admin")
    assert user.email == "admin@admin.com"
    assert user.check_password("admin") is True


@pytest.mark.integration
@pytest.mark.django_db
def test_seed_admin_holds_every_atomic_permission_in_the_catalog(monkeypatch):
    """
    El administrador sembrado debe poder ejercer todo el catalogo atomico.
    is_superuser no basta: has_atomic_permission solo mira asignaciones de rol,
    asi que un permiso ausente del rol deja la funcion inaccesible en la demo
    (por ejemplo, escanear exige attendance_scan y attendance_record_entry).
    """
    monkeypatch.setenv("DEMO_ADMIN_USERNAME", "seed-admin")
    monkeypatch.setenv("DEMO_ADMIN_EMAIL", "seed-admin@example.test")
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", "seed-pass-123")

    call_command("seed_demo_data")

    admin = get_user_model().objects.get(username="seed-admin")
    missing = [
        codename
        for codename in ATOMIC_PERMISSION_CODENAMES
        if not admin.has_atomic_permission(codename)
    ]
    assert missing == []


@pytest.mark.integration
@pytest.mark.django_db
def test_seed_reuses_existing_main_campus():
    institution = Institution.objects.create(name="Instituto Demo SIGA-INEBI")
    Campus.objects.create(
        institution=institution,
        name="Sede migrada",
        code="LEGACY",
        is_main=True,
    )

    call_command("seed_demo_data")

    assert Campus.objects.filter(institution=institution, code="CENTRAL").exists() is True
    assert Campus.objects.filter(institution=institution, is_main=True).count() == 1


@pytest.mark.integration
@pytest.mark.django_db
def test_seed_reuses_existing_grade_codes_from_legacy_level():
    institution = Institution.objects.create(name="Instituto Demo SIGA-INEBI")
    legacy_level = Level.objects.create(
        institution=institution,
        name="Nivel migrado",
        code="LEGACY",
        sequence=1,
    )
    Grade.objects.create(
        level=legacy_level,
        name="Grado heredado",
        code="B1",
        sequence=99,
    )

    call_command("seed_demo_data")

    level = Level.objects.get(institution=institution, code="BAS")
    grade = Grade.objects.get(institution=institution, code="B1")

    assert Grade.objects.filter(institution=institution, code="B1").count() == 1
    assert grade.level_id == level.id
    assert grade.sequence == 1
    assert grade.name == "Primero Basico"


@pytest.mark.integration
@pytest.mark.security
def test_seed_command_has_no_hardcoded_demo_password():
    with open("apps/identity/management/commands/seed_demo_data.py", encoding="utf-8") as handle:
        contents = handle.read()

    assert "DEMO_ADMIN_PASSWORD" in contents
    assert "admin123" not in contents
