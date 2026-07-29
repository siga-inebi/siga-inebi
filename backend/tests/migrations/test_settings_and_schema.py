import subprocess
import sys

import pytest

from apps.academics.models import AcademicCycle, Grade, Institution, Section, Shift


@pytest.mark.migration
@pytest.mark.postgres
@pytest.mark.django_db
def test_core_tables_available_after_migrations():
    institution = Institution.objects.create(name="INEBI")
    cycle = AcademicCycle.objects.create(
        institution=institution,
        name="2026",
        starts_on="2026-01-01",
        ends_on="2026-10-31",
        status="active",
    )
    shift = Shift.objects.create(institution=institution, name="Matutina", code="M")
    grade = Grade.objects.create(institution=institution, name="Primero", code="1")
    section = Section.objects.create(
        academic_cycle=cycle,
        grade=grade,
        shift=shift,
        name="A",
        capacity=35,
    )

    assert section.pk is not None


@pytest.mark.migration
def test_test_settings_reject_sqlite(monkeypatch):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os; "
            "os.environ['DJANGO_SETTINGS_MODULE']='config.settings.test'; "
            "os.environ['DATABASE_ENGINE']='sqlite'; "
            "import config.settings.test",
        ],
        capture_output=True,
        text=True,
        cwd=".",
    )

    assert result.returncode != 0
    assert "Test settings require DATABASE_ENGINE=postgresql." in result.stderr
