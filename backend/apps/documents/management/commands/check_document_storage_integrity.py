import json

from django.core.management.base import BaseCommand

from apps.documents.services import verify_document_storage_integrity


class Command(BaseCommand):
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

    def handle(self, *args, **options):
        institution_id = (options.get("institution_id") or "").strip()
        result = verify_document_storage_integrity(actor=None, institution=None)

        if institution_id:
            from apps.academics.models import Institution

            institution = Institution.objects.filter(public_id=institution_id).first()
            if institution is None:
                raise SystemExit(f"Institution not found for public_id={institution_id!r}")
            result = verify_document_storage_integrity(actor=None, institution=institution)

        if options.get("json"):
            self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
            return

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
