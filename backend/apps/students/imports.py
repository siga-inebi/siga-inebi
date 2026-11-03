"""
Importacion de estudiantes desde CSV, todo o nada.

El flujo es vista previa y confirmacion. Las dos ejecutan lo mismo: cada fila
pasa por el ``create_student`` real dentro de su propio savepoint, en una
transaccion que la vista previa siempre revierte. Asi la regla de que es un
alta valida tiene una sola definicion y la vista previa no puede prometer algo
que la confirmacion luego rechace por otra regla.

Antes de llegar al servicio se revisa lo que solo se ve mirando el archivo
entero (CUI o codigo repetido entre filas) y lo que el servicio no valida por
si mismo porque hasta hoy lo hacia el serializador del formulario (formato de
CUI, fecha, sexo y correo).

Un CUI que ya pertenece a una persona registrada es un error en esta primera
version, tenga o no expediente: vincular personas existentes desde un archivo
no fue pedido (AGENTS.md #2) y ya existe el flujo «Convertir persona» para eso.

La confirmacion recibe el mismo archivo y la huella SHA-256 que devolvio la
vista previa: si el archivo cambio entre una y otra, no se importa.
"""

import csv
import hashlib
import io
import unicodedata
from dataclasses import dataclass, field
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.common.exceptions import DomainError
from apps.people.models import Person
from apps.students.models import Student
from apps.students.services import create_student

TEMPLATE_COLUMNS = (
    "nombres",
    "apellidos",
    "cui",
    "fecha_nacimiento",
    "sexo",
    "correo",
    "telefono",
    "codigo_estudiante",
)
MAX_IMPORT_ROWS = 500
MAX_IMPORT_BYTES = 1024 * 1024

#: Valores aceptados en ``sexo`` (sin distinguir mayusculas ni tildes).
#: Vacio equivale a «No especificado».
SEX_ALIASES = {
    "f": Person.Sex.FEMALE,
    "femenino": Person.Sex.FEMALE,
    "female": Person.Sex.FEMALE,
    "m": Person.Sex.MALE,
    "masculino": Person.Sex.MALE,
    "male": Person.Sex.MALE,
    "": Person.Sex.NOT_SPECIFIED,
    "no especificado": Person.Sex.NOT_SPECIFIED,
    "not_specified": Person.Sex.NOT_SPECIFIED,
}

STATUS_READY = "ready"
STATUS_ERROR = "error"


@dataclass
class ImportRow:
    line: int
    data: dict
    status: str = STATUS_READY
    errors: list = field(default_factory=list)
    student: Student | None = None


@dataclass
class ImportResult:
    file_sha256: str
    rows: list

    @property
    def summary(self):
        errors = sum(row.status == STATUS_ERROR for row in self.rows)
        return {"total": len(self.rows), "ready": len(self.rows) - errors, "errors": errors}

    @property
    def has_errors(self):
        return any(row.status == STATUS_ERROR for row in self.rows)

    @property
    def students(self):
        return [row.student for row in self.rows if row.student is not None]


class ImportFileChanged(DomainError):
    """The confirmed file is not the one that was previewed."""


def import_template_csv():
    """The template: UTF-8 with BOM (so spreadsheets read the accents), headers only."""
    return "﻿" + ",".join(TEMPLATE_COLUMNS) + "\r\n"


def file_sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def parse_import_file(raw):
    """
    ``(line, data)`` for each data row of ``raw`` (bytes).

    Structural problems reject the whole file with a ``DomainError`` before any
    row is looked at: size, encoding, headers, no rows, too many rows.
    """
    if len(raw) > MAX_IMPORT_BYTES:
        raise DomainError(f"El archivo supera el máximo de {MAX_IMPORT_BYTES // 1024} KB.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DomainError("El archivo debe estar codificado en UTF-8.") from exc
    if not text.strip():
        raise DomainError("El archivo está vacío.")

    reader = csv.DictReader(io.StringIO(text))
    headers = [(name or "").strip().lower() for name in (reader.fieldnames or [])]
    missing = [column for column in TEMPLATE_COLUMNS if column not in headers]
    if missing:
        raise DomainError(f"Faltan columnas en el archivo: {', '.join(missing)}.")
    unknown = [name for name in headers if name not in TEMPLATE_COLUMNS]
    if unknown:
        raise DomainError(f"Columnas no reconocidas: {', '.join(unknown)}.")
    reader.fieldnames = headers

    rows = []
    for record in reader:
        if None in record:
            raise DomainError(
                f"La fila {reader.line_num} tiene más valores que columnas en el encabezado."
            )
        data = {column: (record.get(column) or "").strip() for column in TEMPLATE_COLUMNS}
        if not any(data.values()):
            continue
        if len(rows) == MAX_IMPORT_ROWS:
            raise DomainError(f"El archivo supera el máximo de {MAX_IMPORT_ROWS} filas.")
        rows.append((reader.line_num, data))
    if not rows:
        raise DomainError("El archivo no contiene filas de datos.")
    return rows


def _fold(value):
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return normalized.strip().lower()


def _person_data(data, errors):
    """``Person`` fields for one row, appending a message per invalid value."""
    person = {
        "first_name": data["nombres"],
        "last_name": data["apellidos"],
        "cui": data["cui"] or None,
        "email": data["correo"],
        "phone_number": data["telefono"],
    }
    if not data["nombres"]:
        errors.append("nombres es obligatorio.")
    if not data["apellidos"]:
        errors.append("apellidos es obligatorio.")
    for column, limit in (("nombres", 150), ("apellidos", 150), ("telefono", 30)):
        if len(data[column]) > limit:
            errors.append(f"{column} admite como máximo {limit} caracteres.")
    if data["cui"] and (not data["cui"].isdigit() or len(data["cui"]) != 13):
        errors.append("El CUI debe tener exactamente 13 dígitos.")
    if data["correo"]:
        try:
            validate_email(data["correo"])
        except ValidationError:
            errors.append("El correo no es válido.")
    if data["fecha_nacimiento"]:
        try:
            birth_date = date.fromisoformat(data["fecha_nacimiento"])
        except ValueError:
            errors.append("fecha_nacimiento debe tener el formato AAAA-MM-DD.")
        else:
            if birth_date > timezone.localdate():
                errors.append("fecha_nacimiento no puede ser una fecha futura.")
            person["birth_date"] = birth_date
    sex = SEX_ALIASES.get(_fold(data["sexo"]))
    if sex is None:
        errors.append("sexo debe ser F, M o «No especificado».")
    else:
        person["sex"] = sex
    if len(data["codigo_estudiante"]) > 50:
        errors.append("codigo_estudiante admite como máximo 50 caracteres.")
    return person


def _cross_row_errors(parsed):
    """Repeated CUI or student code inside the file, and conflicts with existing records."""
    errors = {line: [] for line, _data in parsed}
    first_seen = {"cui": {}, "codigo_estudiante": {}}
    labels = {"cui": "El CUI", "codigo_estudiante": "El código de estudiante"}
    for line, data in parsed:
        for column, seen in first_seen.items():
            value = data[column]
            if not value:
                continue
            if value in seen:
                errors[line].append(f"{labels[column]} se repite en la fila {seen[value]}.")
            else:
                seen[value] = line

    cuis = list(first_seen["cui"])
    people = {
        person.cui: person
        for person in Person.objects.filter(cui__in=cuis).select_related("student_profile")
    }
    codes = set(
        Student.objects.filter(student_code__in=list(first_seen["codigo_estudiante"])).values_list(
            "student_code", flat=True
        )
    )
    for line, data in parsed:
        person = people.get(data["cui"]) if data["cui"] else None
        if person is not None:
            if hasattr(person, "student_profile"):
                errors[line].append("El CUI ya pertenece a un estudiante registrado.")
            else:
                errors[line].append(
                    "El CUI ya pertenece a una persona registrada sin expediente de "
                    "estudiante; regístrela desde «Convertir persona»."
                )
        if data["codigo_estudiante"] in codes:
            errors[line].append(
                f"El código de estudiante '{data['codigo_estudiante']}' ya está registrado."
            )
    return errors


def _run(*, raw, actor, commit):
    parsed = parse_import_file(raw)
    cross_errors = _cross_row_errors(parsed)
    rows = [ImportRow(line=line, data=data) for line, data in parsed]

    with transaction.atomic():
        prepared = []
        for row in rows:
            person = _person_data(row.data, row.errors)
            row.errors.extend(cross_errors[row.line])
            prepared.append((row, person))
        # Codigos explicitos primero: si una fila sin codigo tomara el siguiente
        # de la serie antes, podria quitarle a una fila posterior el codigo que
        # el archivo le asigna a mano.
        ordered = sorted(prepared, key=lambda item: not item[0].data["codigo_estudiante"])
        for row, person in ordered:
            if row.errors:
                continue
            try:
                with transaction.atomic():
                    row.student = create_student(
                        person_data=person,
                        student_code=row.data["codigo_estudiante"] or None,
                        actor=actor,
                    )
            except DomainError as exc:
                row.errors.append(str(exc))
        for row in rows:
            if row.errors:
                row.status = STATUS_ERROR
                row.student = None
        result = ImportResult(file_sha256=file_sha256(raw), rows=rows)
        if not commit or result.has_errors:
            transaction.set_rollback(True)
            for row in rows:
                row.student = None
    return result


def preview_student_import(*, raw, actor):
    """Validate every row through the real service and persist nothing."""
    result = _run(raw=raw, actor=actor, commit=False)
    summary = result.summary
    record_event(
        actor=actor,
        action="students.import.previewed",
        resource="Student",
        resource_identifier="csv-import",
        context={**summary, "file_sha256": result.file_sha256},
    )
    return result


def confirm_student_import(*, raw, expected_sha256, actor):
    """
    Import every row or none.

    Raises ``ImportFileChanged`` when ``raw`` is not the previewed file. A
    result with errors means nothing was inserted.
    """
    digest = file_sha256(raw)
    if digest != (expected_sha256 or "").strip().lower():
        record_event(
            actor=actor,
            action="students.import.rejected",
            resource="Student",
            resource_identifier="csv-import",
            context={"reason": "file_changed", "file_sha256": digest},
        )
        raise ImportFileChanged(
            "El archivo no coincide con el de la vista previa. Vuelva a revisarlo antes de "
            "confirmar."
        )
    result = _run(raw=raw, actor=actor, commit=True)
    summary = result.summary
    if result.has_errors:
        record_event(
            actor=actor,
            action="students.import.rejected",
            resource="Student",
            resource_identifier="csv-import",
            context={**summary, "reason": "row_errors", "file_sha256": digest},
        )
        return result
    record_event(
        actor=actor,
        action="students.import.processed",
        resource="Student",
        resource_identifier="csv-import",
        context={**summary, "created": len(result.students), "file_sha256": digest},
    )
    return result
