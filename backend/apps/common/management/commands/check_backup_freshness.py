"""
Comprueba que cada pila de respaldo cumple el RPO declarado (RNF-RES-002).

Un RPO declarado y no verificado es un numero en un documento. Este comando lo
convierte en una afirmacion comprobable todas las noches: si el respaldo mas
reciente de la base o el de los archivos es mas viejo que el RPO, la tarea falla
con codigo distinto de cero y queda registrada como fallida (RNF-OPE-001), que
es lo que hace que alguien se entere.

Las dos pilas se evaluan por separado y ambas tienen que cumplir: que la base
este respaldada no dice nada de los archivos (RNF-RES-001).
"""

import json

from django.conf import settings

from apps.common.backups import backup_health
from apps.common.management_base import MonitoredCommand


class Command(MonitoredCommand):
    help = "Verify that each backup stack is newer than the declared RPO."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit the report as JSON instead of a human-readable summary.",
        )

    def run(self, *args, **options):
        summary = options["summary"]
        health = backup_health()

        summary["rpo_hours"] = settings.RECOVERY_POINT_OBJECTIVE_HOURS
        summary["rto_hours"] = settings.RECOVERY_TIME_OBJECTIVE_HOURS
        for stack in health:
            summary[stack["stack"]] = {
                "age_hours": stack["age_hours"],
                "meets_rpo": stack["meets_rpo"],
                "backup_count": stack["backup_count"],
            }

        if options.get("json"):
            self.stdout.write(
                json.dumps(
                    [
                        {
                            **stack,
                            "created_at": (
                                stack["created_at"].isoformat() if stack["created_at"] else None
                            ),
                        }
                        for stack in health
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            self.stdout.write(f"RPO declarado: {settings.RECOVERY_POINT_OBJECTIVE_HOURS} h\n")
            for stack in health:
                age = "sin respaldo" if stack["age_hours"] is None else f"{stack['age_hours']} h"
                state = "cumple" if stack["meets_rpo"] else "INCUMPLE"
                self.stdout.write(f"- {stack['stack']}: {age} ({state})")

        breaching = [stack["stack"] for stack in health if not stack["meets_rpo"]]
        if breaching:
            raise SystemExit(
                f"RPO incumplido en: {', '.join(breaching)}. "
                f"Objetivo: {settings.RECOVERY_POINT_OBJECTIVE_HOURS} h."
            )
