import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


def migrate_to(target):
    executor = MigrationExecutor(connection)
    executor.migrate(target)
    return executor.loader.project_state(target).apps


@pytest.mark.migration
@pytest.mark.postgres
@pytest.mark.django_db(transaction=True)
def test_academics_0002_backfills_legacy_catalogue_links():
    old_apps = migrate_to([("academics", "0001_initial")])

    Institution = old_apps.get_model("academics", "Institution")
    AcademicCycle = old_apps.get_model("academics", "AcademicCycle")
    Shift = old_apps.get_model("academics", "Shift")
    Grade = old_apps.get_model("academics", "Grade")
    Section = old_apps.get_model("academics", "Section")

    institution = Institution.objects.create(name="INEBI")
    cycle = AcademicCycle.objects.create(
        institution_id=institution.pk,
        name="2026",
        starts_on="2026-01-01",
        ends_on="2026-10-31",
        status="active",
    )
    shift = Shift.objects.create(
        institution_id=institution.pk,
        name="Matutina",
        code="M",
    )
    grade = Grade.objects.create(
        institution_id=institution.pk,
        name="Primero",
        code="1",
    )
    Section.objects.create(
        academic_cycle_id=cycle.pk,
        grade_id=grade.pk,
        shift_id=shift.pk,
        name="A",
        capacity=35,
    )

    new_apps = migrate_to([("academics", "0002_academic_catalogue")])

    Campus = new_apps.get_model("academics", "Campus")
    Shift = new_apps.get_model("academics", "Shift")
    Level = new_apps.get_model("academics", "Level")
    Grade = new_apps.get_model("academics", "Grade")
    GradeOffering = new_apps.get_model("academics", "GradeOffering")
    Section = new_apps.get_model("academics", "Section")

    campus = Campus.objects.get(institution_id=institution.pk, code="LEGACY")
    level = Level.objects.get(institution_id=institution.pk, code="LEGACY")
    shift = Shift.objects.get(code="M")
    grade = Grade.objects.get(code="1")
    section = Section.objects.get(name="A")
    offering = GradeOffering.objects.get(pk=section.offering_id)

    assert campus.is_main is True
    assert shift.campus_id == campus.pk
    assert grade.level_id == level.pk
    assert grade.sequence == 1
    assert offering.academic_cycle_id == cycle.pk
    assert offering.shift_id == shift.pk
    assert offering.grade_id == grade.pk
