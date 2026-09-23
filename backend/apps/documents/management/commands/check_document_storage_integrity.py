import json

from django.core.exceptions import ValidationError

from apps.common.management_base import MonitoredCommand
from apps.documents.services import verify_document_storage_integrity


class Command(MonitoredCommand):
    """
    Scheduled integrity scan of persisted documents.

    Runs unattended from cron, so it inherits ``MonitoredCommand``: every
    execution leaves a ``TaskRun`` row with its counters, and a scan that finds
    corruption ends with a non-zero exit code recorded as a failed run
    (RNF-OPE-001).
    """

    help = "Check persisted document files against their stored SHA-256 hashes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--institution-id",
            type=str,
            default="",
            help="Optional institution public ID to scope the integrity scan.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit the summary as JSON instead of a human-readable report.",
        )

    def run(self, *args, **options):
        summary = options["summary"]
        institution_id = (options.get("institution_id") or "").strip()
        result = verify_document_storage_integrity(actor=None, institution=None)

        if institution_id:
            from apps.academics.models import Institution

            # Un identificador mal formado tiene que salir por la misma puerta
            # que uno inexistente: `filter(public_id=...)` levanta
            # `ValidationError` si no es un UUID, y eso convertia un argumento
            # mal tecleado en una traza cruda en el log del cron.
            try:
                institution = Institution.objects.filter(public_id=institution_id).first()
            except (ValidationError, ValueError):
                institution = None
            if institution is None:
                raise SystemExit(f"Institution not found for public_id={institution_id!r}")
            result = verify_document_storage_integrity(actor=None, institution=institution)

        # The counters, not the per-file issue list: the summary is read in a
        # table, and the detail is already in the command's own output.
        summary.update(
            {
                "institution_id": institution_id,
                "total_checked": result["total_checked"],
                "ok": result["ok"],
                "corrupted": result["corrupted"],
                "unreadable": result.get("unreadable", 0),
                "missing": result["missing"],
            }
        )

        if options.get("json"):
            self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            self.stdout.write(
                "Document storage integrity summary\n"
                f"- total_checked: {result['total_checked']}\n"
                f"- ok: {result['ok']}\n"
                f"- corrupted: {result['corrupted']}\n"
                f"- unreadable: {result.get('unreadable', 0)}\n"
                f"- missing: {result['missing']}\n"
            )

            for issue in result["issues"]:
                self.stdout.write(
                    f"- {issue['status']}: {issue['storage_key']} ({issue.get('document_id', '')})"
                )

        if result["corrupted"] or result.get("unreadable") or result["missing"]:
            raise SystemExit(1)
