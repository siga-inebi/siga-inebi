import subprocess
import sys

import pytest

from apps.academics.models import (
    AcademicCycle,
    Campus,
    Grade,
    GradeOffering,
    Institution,
    Level,
    Section,
    Shift,
)


@pytest.mark.migration
@pytest.mark.postgres
@pytest.mark.django_db
def test_core_tables_available_after_migrations():
    institution = Institution.objects.create(name="INEBI")
    cycle = AcademicCycle.objects.create(
        institution=institution,
        year=2026,
        name="2026",
        starts_on="2026-01-01",
        ends_on="2026-10-31",
        status="active",
    )
    campus = Campus.objects.create(institution=institution, name="Sede Central", code="CENTRAL")
    shift = Shift.objects.create(campus=campus, name="Matutina", code="M")
    level = Level.objects.create(institution=institution, name="Basico", code="BAS", sequence=3)
    grade = Grade.objects.create(level=level, name="Primero", code="1", sequence=1)
    offering = GradeOffering.objects.create(
        academic_cycle=cycle,
        shift=shift,
        grade=grade,
    )
    section = Section.objects.create(offering=offering, name="A", capacity=35)

    assert section.pk is not None
    assert section.campus == campus
    assert section.level == level


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
