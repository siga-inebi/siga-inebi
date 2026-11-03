"""
Exportacion de carnes, individual y por lote (RF-CRE-001/002).

Sigue el patron de ``apps.enrolments.bulk_initial``: entre 1 y 100
estudiantes distintos, un savepoint por estudiante y, en vista previa, la
transaccion entera revertida. La vista previa ejecuta la misma emision que la
exportacion real (``issue_credential``), asi que lo que promete es exactamente
lo que la confirmacion hara.

Cada fila termina en uno de tres estados:

- ``ready``: tiene credencial vigente; se exporta tal cual.
- ``to_issue``: no tiene credencial y el actor puede emitirla; la exportacion
  la emite antes de dibujarla.
- ``skipped``: no se exporta, con el motivo (sin inscripcion activa, sin
  permiso para emitir, fuera de alcance...).

Un estudiante fuera del alcance de impresion se trata igual que uno que no
existe: la fila no lleva nombre ni codigo, para que la respuesta no sirva para
averiguar datos de estudiantes ajenos.
"""

import io
import re
import unicodedata
import zipfile
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from apps.attendance import card_render
from apps.attendance.services import (
    _is_enrolled,
    active_credential,
    issue_credential,
    resolve_credential_print_content,
)
from apps.audit.services import record_event
from apps.common.exceptions import AuthorizationError, DomainError
from apps.common.qr import generate_qr_png
from apps.identity.scopes import authorized_student_queryset
from apps.students.models import Student

MAX_EXPORT_SIZE = 100
CREDENTIAL_PRINT_PERMISSION = "attendance_credential_print"
CREDENTIAL_ISSUE_PERMISSION = "attendance_credential_issue"

FORMAT_PDF = "pdf"
FORMAT_PNG = "png"
FORMAT_ZIP = "zip"
EXPORT_FORMATS = (FORMAT_PDF, FORMAT_PNG, FORMAT_ZIP)
CONTENT_TYPES = {
    FORMAT_PDF: "application/pdf",
    FORMAT_PNG: "image/png",
    FORMAT_ZIP: "application/zip",
}

STATUS_READY = "ready"
STATUS_TO_ISSUE = "to_issue"
STATUS_SKIPPED = "skipped"

NOT_FOUND_REASON = "Estudiante no encontrado o fuera de su alcance."
NO_ISSUE_PERMISSION_REASON = "No tiene permiso para emitir el carné de este estudiante."


@dataclass
class ExportRow:
    student_id: str
    full_name: str = ""
    student_code: str = ""
    status: str = STATUS_SKIPPED
    reason: str | None = None


@dataclass
class _Exportable:
    content: object
    token: str


@dataclass
class CredentialExport:
    rows: list
    content: bytes | None = None
    content_type: str | None = None
    filename: str | None = None
    exported_student_ids: list = field(default_factory=list)

    @property
    def summary(self):
        return {
            "total": len(self.rows),
            "ready": sum(row.status == STATUS_READY for row in self.rows),
            "to_issue": sum(row.status == STATUS_TO_ISSUE for row in self.rows),
            "skipped": sum(row.status == STATUS_SKIPPED for row in self.rows),
        }


def validate_export_request(*, student_ids, export_format):
    if export_format not in EXPORT_FORMATS:
        raise DomainError("El formato debe ser pdf, png o zip.")
    if not 1 <= len(student_ids) <= MAX_EXPORT_SIZE or len(set(student_ids)) != len(student_ids):
        raise DomainError(f"Seleccione entre 1 y {MAX_EXPORT_SIZE} estudiantes distintos.")
    if export_format == FORMAT_PNG and len(student_ids) != 1:
        raise DomainError("El formato PNG exporta un solo carné; use PDF o ZIP para varios.")


def _student_ids_in_scope(*, actor, codename, student_ids, raise_on_denied):
    """Public ids among ``student_ids`` the actor reaches with ``codename``."""
    try:
        queryset = authorized_student_queryset(user=actor, codename=codename)
    except AuthorizationError:
        if raise_on_denied:
            raise
        return set()
    return {
        str(public_id)
        for public_id in queryset.filter(public_id__in=student_ids).values_list(
            "public_id", flat=True
        )
    }


def card_file_stem(*, student_code, full_name):
    """``EST-2026-0001_Ana-Perez``: ASCII only, safe for any file system."""

    def ascii_part(value):
        normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
        return re.sub(r"[^A-Za-z0-9]+", "-", normalized).strip("-")

    parts = [ascii_part(student_code), ascii_part(full_name)]
    return "_".join(part for part in parts if part) or "carne"


def _package(exportables, export_format, *, qr_generator, photo_loader):
    cards = []
    for exportable in exportables:
        content = exportable.content
        cards.append(
            card_render.RenderedCard(
                filename=card_file_stem(
                    student_code=content.student.student_code, full_name=content.full_name
                )
                + ".png",
                png=card_render.render_card_png(
                    content,
                    exportable.token,
                    qr_generator=qr_generator,
                    photo_loader=photo_loader,
                ),
            )
        )
    today = timezone.localdate().isoformat()
    if export_format == FORMAT_PNG:
        return cards[0].png, cards[0].filename
    if export_format == FORMAT_PDF:
        name = cards[0].filename[: -len(".png")] if len(cards) == 1 else f"carnes-{today}"
        return card_render.render_cards_pdf(card.png for card in cards), f"{name}.pdf"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for card in cards:
            archive.writestr(card.filename, card.png)
    return buffer.getvalue(), f"carnes-{today}.zip"


def export_credentials(
    *,
    actor,
    student_ids,
    export_format,
    preview=True,
    qr_generator=generate_qr_png,
    photo_loader=None,
):
    """
    Preview or export the cards of ``student_ids`` in ``export_format``.

    Requires ``attendance.credential.print`` with scope (403 otherwise).
    Missing credentials are issued only where the actor also holds
    ``attendance.credential.issue`` over that student; elsewhere the row is
    skipped. In preview nothing persists. A real export with nothing to export
    is a ``DomainError``; it never answers with an empty file.
    """
    student_ids = [str(student_id) for student_id in student_ids]
    validate_export_request(student_ids=student_ids, export_format=export_format)
    printable = _student_ids_in_scope(
        actor=actor,
        codename=CREDENTIAL_PRINT_PERMISSION,
        student_ids=student_ids,
        raise_on_denied=True,
    )
    students = {
        str(student.public_id): student
        for student in Student.objects.select_related("person").filter(public_id__in=printable)
    }
    issuable = None
    rows = []
    exportables = []

    with transaction.atomic():
        for student_id in student_ids:
            row = ExportRow(student_id=student_id)
            rows.append(row)
            student = students.get(student_id)
            if student is None:
                row.reason = NOT_FOUND_REASON
                continue
            row.full_name = f"{student.person.first_name} {student.person.last_name}".strip()
            row.student_code = student.student_code
            try:
                with transaction.atomic():
                    if not student.is_active:
                        raise DomainError("El estudiante está inactivo.")
                    if not _is_enrolled(student):
                        raise DomainError("El estudiante no tiene inscripción activa.")
                    credential = active_credential(student=student)
                    status = STATUS_READY
                    if credential is None:
                        if issuable is None:
                            issuable = _student_ids_in_scope(
                                actor=actor,
                                codename=CREDENTIAL_ISSUE_PERMISSION,
                                student_ids=student_ids,
                                raise_on_denied=False,
                            )
                        if student_id not in issuable:
                            raise DomainError(NO_ISSUE_PERMISSION_REASON)
                        credential = issue_credential(student=student, actor=actor)
                        status = STATUS_TO_ISSUE
                    content = resolve_credential_print_content(student=student)
            except DomainError as exc:
                row.reason = str(exc)
                continue
            row.status = status
            exportables.append(_Exportable(content=content, token=credential.opaque_identifier))

        if preview:
            transaction.set_rollback(True)
        elif not exportables:
            raise DomainError("Ninguno de los estudiantes seleccionados tiene un carné exportable.")

    result = CredentialExport(rows=rows)
    if preview:
        return result

    # Se dibuja fuera de la transaccion: leer fotos y codificar imagenes no
    # debe alargar el tiempo en que las credenciales recien emitidas quedan
    # bloqueadas.
    result.content, result.filename = _package(
        exportables, export_format, qr_generator=qr_generator, photo_loader=photo_loader
    )
    result.content_type = CONTENT_TYPES[export_format]
    result.exported_student_ids = [str(item.content.student.public_id) for item in exportables]
    summary = result.summary
    # Igual que en la emision, el asiento dice que se exporto y de quienes,
    # nunca los tokens que van dentro de cada QR.
    record_event(
        actor=actor,
        action="attendance.credential.exported",
        resource="StudentCredential",
        resource_identifier="export",
        context={
            "format": export_format,
            "count": len(exportables),
            "issued": summary["to_issue"],
            "skipped": summary["skipped"],
            "student_ids": result.exported_student_ids,
        },
    )
    return result
