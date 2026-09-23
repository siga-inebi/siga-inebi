import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.migration
@pytest.mark.postgres
@pytest.mark.django_db(transaction=True)
def test_existing_classrooms_become_available_without_reactivation():
    before = [("academics", "0015_merge_0012_frozen_results_0014_merge_20260917_0931")]
    after = [("academics", "0016_classroom_service_status")]
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    try:
        executor.migrate(before)
        apps = executor.loader.project_state(before).apps
        institution = apps.get_model("academics", "Institution").objects.create(name="Demo")
        campus = apps.get_model("academics", "Campus").objects.create(
            institution=institution, name="Sede demo", code="DEMO"
        )
        Room = apps.get_model("academics", "Classroom")
        room = Room.objects.create(campus=campus, name="Historica", code="H", is_active=False)
        room_id = room.pk
        executor = MigrationExecutor(connection)
        executor.migrate(after)
        Room = executor.loader.project_state(after).apps.get_model("academics", "Classroom")
        migrated = Room.objects.get(pk=room_id)
        assert migrated.service_status == "available"
        assert migrated.is_active is False
        assert migrated.code == "H"
        assert migrated.campus_id == campus.pk
    finally:
        MigrationExecutor(connection).migrate(latest)
