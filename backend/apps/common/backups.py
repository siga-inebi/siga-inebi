"""
Lectura de los manifiestos de respaldo y medicion del RPO (RNF-RES-001/002).

Los respaldos los produce `scripts/backup/`, fuera de Django: son tareas de
sistema y deben poder correr aunque la aplicacion no arranque. Lo que vive aqui
es la mitad que si le corresponde a la aplicacion, que es CONTESTAR si el
respaldo sirve:

- un respaldo que nadie mira es una suposicion, no una garantia;
- un RPO declarado y no verificado es un numero en un documento.

Cada pila se mide por separado, nunca agregada, porque el requerimiento las
declara independientes: que la base este respaldada no dice nada de los
archivos.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

DATABASE_STACK = "database"
FILES_STACK = "files"

_ARTIFACT_SUFFIX = {DATABASE_STACK: ".dump", FILES_STACK: ".tar.gz"}


def _manifest_dir(stack):
    if stack == DATABASE_STACK:
        return Path(settings.DATABASE_BACKUP_DIR)
    if stack == FILES_STACK:
        return Path(settings.FILES_BACKUP_DIR)
    raise ValueError(f"Pila de respaldo desconocida: {stack!r}")


def _parse_created_at(raw):
    """
    ``created_at`` viene del script en UTC con sufijo ``Z``.

    ``fromisoformat`` no acepta la ``Z`` antes de Python 3.11 y, sobre todo, un
    manifiesto escrito a mano puede traer cualquier cosa: un valor ilegible se
    trata como ausente, que es el caso conservador -- el respaldo se reporta
    como no verificable en vez de como fresco.
    """
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if timezone.is_naive(parsed):
        return parsed.replace(tzinfo=UTC)
    return parsed


def read_manifests(stack):
    """Manifiestos de una pila, del mas reciente al mas antiguo."""
    directory = _manifest_dir(stack)
    if not directory.is_dir():
        return []

    manifests = []
    for path in sorted(directory.glob("*.manifest.json")):
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            # Un manifiesto ilegible no puede tumbar la comprobacion: el resto
            # de respaldos sigue siendo informacion valida, y su ausencia en la
            # lista ya lo delata.
            continue
        payload["manifest_path"] = str(path)
        payload["created_at_parsed"] = _parse_created_at(payload.get("created_at"))
        manifests.append(payload)

    return sorted(
        manifests,
        key=lambda item: item["created_at_parsed"] or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )


def latest_manifest(stack):
    manifests = read_manifests(stack)
    return manifests[0] if manifests else None


def stack_health(stack, *, now=None):
    """
    Estado de una pila frente al RPO declarado.

    ``meets_rpo`` es falso cuando no hay respaldo: la ausencia es el peor caso,
    no un caso neutro.
    """
    now = now or timezone.now()
    rpo_hours = settings.RECOVERY_POINT_OBJECTIVE_HOURS
    manifest = latest_manifest(stack)
    created_at = manifest["created_at_parsed"] if manifest else None

    age_hours = None
    if created_at is not None:
        age_hours = (now - created_at) / timedelta(hours=1)

    return {
        "stack": stack,
        "artifact": manifest.get("artifact", "") if manifest else "",
        "created_at": created_at,
        "age_hours": round(age_hours, 2) if age_hours is not None else None,
        "size_bytes": manifest.get("size_bytes") if manifest else None,
        "sha256": manifest.get("sha256", "") if manifest else "",
        "rpo_hours": rpo_hours,
        "meets_rpo": age_hours is not None and age_hours <= rpo_hours,
        "backup_count": len(read_manifests(stack)),
    }


def backup_health(*, now=None):
    """Una fila por pila. Nunca se agregan: son independientes (RNF-RES-001)."""
    return [stack_health(stack, now=now) for stack in (DATABASE_STACK, FILES_STACK)]


def artifact_path(manifest):
    """Ruta del artefacto que describe un manifiesto, junto a el."""
    manifest_path = Path(manifest["manifest_path"])
    return manifest_path.parent / manifest["artifact"]


def artifact_suffix(stack):
    return _ARTIFACT_SUFFIX[stack]
