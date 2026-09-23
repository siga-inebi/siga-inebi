"""
RNF-RES-001 y RNF-RES-002: respaldo independiente, restauracion y metas de
recuperacion.

Escenarios derivados de los criterios (la fuente no trae ninguno):

RNF-RES-001
1. Camino feliz: cada pila se respalda y se restaura por su cuenta, y el
   contenido vuelve intacto.
2. Independencia: ningun manifiesto ni script de una pila menciona a la otra, y
   restaurar una sola funciona con la otra ausente.
3. Integridad: un artefacto alterado se rechaza antes de restaurar nada.

RNF-RES-002
4. Camino feliz: con respaldos frescos en las dos pilas, la comprobacion pasa.
5. Incumplimiento: un respaldo mas viejo que el RPO, o inexistente, falla con
   codigo distinto de cero.
6. Rechazo por autorizacion: el estado de los respaldos no se lee sin
   `platform.monitor`.

El respaldo de la base usa `pg_dump`, que necesita un cliente de la misma
version mayor que el servidor; la imagen del backend lo trae fijado (RNF-RES-001,
`backend/Dockerfile`). Donde no lo haya, esas pruebas se omiten en vez de fallar
por el entorno.
"""

import json
import os
import shutil
import subprocess
from datetime import timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.test import override_settings
from django.utils import timezone

from apps.common.backups import DATABASE_STACK, FILES_STACK, backup_health, latest_manifest

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

SCRIPTS = Path(settings.BACKUP_SCRIPTS_DIR)


def _run(script, *, env=None, args=()):
    merged = {**os.environ, **(env or {})}
    return subprocess.run(  # noqa: S603 - rutas fijas del repositorio, sin shell
        ["sh", str(SCRIPTS / script), *args],
        capture_output=True,
        text=True,
        env=merged,
        check=False,
    )


def _database_env(tmp_path):
    database = connection.settings_dict
    return {
        "BACKUP_ROOT": str(tmp_path),
        "DATABASE_NAME": database["NAME"],
        "DATABASE_USER": database["USER"],
        "DATABASE_HOST": database["HOST"] or "localhost",
        "DATABASE_PORT": str(database["PORT"] or 5432),
        "PGPASSWORD": database["PASSWORD"],
    }


def _write_manifest(directory, *, stack, artifact_name, age_hours, contents=b"x"):
    directory.mkdir(parents=True, exist_ok=True)
    artifact = directory / artifact_name
    artifact.write_bytes(contents)
    created_at = timezone.now() - timedelta(hours=age_hours)
    manifest = directory / f"{artifact_name.split('.')[0]}.manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "kind": stack,
                "artifact": artifact_name,
                "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "size_bytes": artifact.stat().st_size,
                "sha256": "0" * 64,
            }
        )
    )
    return manifest


# --------------------------------------------------------------------------- #
# RNF-RES-001
# --------------------------------------------------------------------------- #


def test_file_stack_backs_up_and_restores_on_its_own(tmp_path):
    media = tmp_path / "media"
    (media / "documents").mkdir(parents=True)
    (media / "documents" / "acta.pdf").write_bytes(b"contenido original")

    backup = _run(
        "backup-files.sh", env={"BACKUP_ROOT": str(tmp_path / "backups"), "MEDIA_ROOT": str(media)}
    )

    assert backup.returncode == 0, backup.stderr

    # Se pierde el almacenamiento entero, no un archivo: es el caso que el
    # respaldo existe para cubrir.
    shutil.rmtree(media)
    target = tmp_path / "media-restaurado"

    restore = _run(
        "restore-files.sh",
        env={"BACKUP_ROOT": str(tmp_path / "backups"), "MEDIA_ROOT": str(target)},
    )

    assert restore.returncode == 0, restore.stderr
    assert (target / "documents" / "acta.pdf").read_bytes() == b"contenido original"


def test_file_backup_manifest_describes_only_its_own_stack(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    (media / "acta.pdf").write_bytes(b"x")

    _run("backup-files.sh", env={"BACKUP_ROOT": str(tmp_path), "MEDIA_ROOT": str(media)})

    manifest = json.loads(next((tmp_path / "files").glob("*.manifest.json")).read_text())

    assert manifest["kind"] == "files"
    # La independencia de RNF-RES-001 tiene que ser verificable en el artefacto,
    # no solo en la intencion: un manifiesto que nombrara a la otra pila haria
    # que restaurar una sola fuera una apuesta.
    assert "database" not in json.dumps(manifest).lower()
    assert manifest["sha256"] and manifest["size_bytes"] > 0


def test_restoring_files_does_not_need_the_database_backup(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    (media / "acta.pdf").write_bytes(b"contenido")

    _run("backup-files.sh", env={"BACKUP_ROOT": str(tmp_path), "MEDIA_ROOT": str(media)})

    assert not (tmp_path / "database").exists()

    restore = _run(
        "restore-files.sh",
        env={"BACKUP_ROOT": str(tmp_path), "MEDIA_ROOT": str(tmp_path / "destino")},
    )

    assert restore.returncode == 0, restore.stderr


def test_a_tampered_backup_is_refused_before_restoring_anything(tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    (media / "acta.pdf").write_bytes(b"contenido")

    _run("backup-files.sh", env={"BACKUP_ROOT": str(tmp_path), "MEDIA_ROOT": str(media)})

    artifact = next((tmp_path / "files").glob("*.tar.gz"))
    artifact.write_bytes(b"archivo alterado")
    target = tmp_path / "destino"

    restore = _run(
        "restore-files.sh", env={"BACKUP_ROOT": str(tmp_path), "MEDIA_ROOT": str(target)}
    )

    assert restore.returncode != 0
    assert "checksum" in restore.stderr
    # Nada se escribio en el destino: el rechazo es previo, no a medio camino.
    assert not target.exists() or not any(target.iterdir())


@pytest.mark.postgres
def test_database_stack_backs_up_and_restores_on_its_own(tmp_path):
    if shutil.which("pg_dump") is None or shutil.which("pg_restore") is None:
        pytest.skip("pg_dump/pg_restore no disponibles en este host")

    env = _database_env(tmp_path)
    backup = _run("backup-database.sh", env=env)

    if backup.returncode != 0 and "version de PostgreSQL incompatible" in backup.stderr:
        pytest.skip("cliente de PostgreSQL de otra version mayor que el servidor")

    assert backup.returncode == 0, backup.stderr

    manifest = json.loads(next((tmp_path / "database").glob("*.manifest.json")).read_text())

    assert manifest["kind"] == "database"
    assert manifest["format"] == "custom"
    assert "files" not in manifest
    assert manifest["database_name"] == env["DATABASE_NAME"]

    # Restaurar sobre la misma base de pruebas: vuelve al mismo estado, que es
    # lo que prueba que el dump es restaurable y no solo que se escribio.
    restore = _run("restore-database.sh", env=env)

    assert restore.returncode == 0, restore.stderr


@pytest.mark.postgres
def test_database_backup_does_not_produce_a_file_artifact(tmp_path):
    if shutil.which("pg_dump") is None:
        pytest.skip("pg_dump no disponible en este host")

    backup = _run("backup-database.sh", env=_database_env(tmp_path))

    if backup.returncode != 0 and "version de PostgreSQL incompatible" in backup.stderr:
        pytest.skip("cliente de PostgreSQL de otra version mayor que el servidor")

    assert backup.returncode == 0, backup.stderr
    assert not (tmp_path / "files").exists()


# --------------------------------------------------------------------------- #
# RNF-RES-002
# --------------------------------------------------------------------------- #


def test_fresh_backups_in_both_stacks_meet_the_declared_rpo(tmp_path):
    _write_manifest(tmp_path / "database", stack="database", artifact_name="db.dump", age_hours=2)
    _write_manifest(tmp_path / "files", stack="files", artifact_name="files.tar.gz", age_hours=3)

    with override_settings(
        DATABASE_BACKUP_DIR=str(tmp_path / "database"),
        FILES_BACKUP_DIR=str(tmp_path / "files"),
        RECOVERY_POINT_OBJECTIVE_HOURS=24,
    ):
        health = {stack["stack"]: stack for stack in backup_health()}

        assert health["database"]["meets_rpo"] is True
        assert health["files"]["meets_rpo"] is True
        assert health["database"]["age_hours"] == pytest.approx(2, abs=0.1)

        call_command("check_backup_freshness")


def test_a_backup_older_than_the_rpo_fails_the_check(tmp_path):
    _write_manifest(tmp_path / "database", stack="database", artifact_name="db.dump", age_hours=2)
    _write_manifest(tmp_path / "files", stack="files", artifact_name="files.tar.gz", age_hours=72)

    with override_settings(
        DATABASE_BACKUP_DIR=str(tmp_path / "database"),
        FILES_BACKUP_DIR=str(tmp_path / "files"),
        RECOVERY_POINT_OBJECTIVE_HOURS=24,
    ):
        health = {stack["stack"]: stack for stack in backup_health()}

        assert health["database"]["meets_rpo"] is True
        assert health["files"]["meets_rpo"] is False

        with pytest.raises(SystemExit, match="files"):
            call_command("check_backup_freshness")


def test_a_missing_backup_is_a_breach_not_a_neutral_case(tmp_path):
    with override_settings(
        DATABASE_BACKUP_DIR=str(tmp_path / "database"),
        FILES_BACKUP_DIR=str(tmp_path / "files"),
        RECOVERY_POINT_OBJECTIVE_HOURS=24,
    ):
        health = {stack["stack"]: stack for stack in backup_health()}

        assert health["database"]["meets_rpo"] is False
        assert health["database"]["age_hours"] is None
        assert health["database"]["backup_count"] == 0

        with pytest.raises(SystemExit):
            call_command("check_backup_freshness")


def test_each_stack_is_measured_separately(tmp_path):
    """Que la base este respaldada no dice nada de los archivos (RNF-RES-001)."""
    _write_manifest(tmp_path / "database", stack="database", artifact_name="db.dump", age_hours=1)

    with override_settings(
        DATABASE_BACKUP_DIR=str(tmp_path / "database"),
        FILES_BACKUP_DIR=str(tmp_path / "files"),
        RECOVERY_POINT_OBJECTIVE_HOURS=24,
    ):
        health = {stack["stack"]: stack for stack in backup_health()}

        assert health["database"]["meets_rpo"] is True
        assert health["files"]["meets_rpo"] is False


def test_an_unreadable_manifest_is_treated_as_absent_not_as_fresh(tmp_path):
    directory = tmp_path / "database"
    directory.mkdir(parents=True)
    (directory / "roto.manifest.json").write_text("{ esto no es json")

    with override_settings(
        DATABASE_BACKUP_DIR=str(directory),
        FILES_BACKUP_DIR=str(tmp_path / "files"),
    ):
        assert latest_manifest(DATABASE_STACK) is None
        assert latest_manifest(FILES_STACK) is None
