"""Altas por lote; reutiliza matrícula individual sin cerrar antecedentes."""

from django.db import transaction

from apps.academics.models import Section
from apps.audit.services import record_event
from apps.common.exceptions import DomainError
from apps.enrolments.authorization import require_section_scope
from apps.enrolments.models import Enrolment
from apps.enrolments.services import matriculate_student
from apps.students.models import Student

MAX_BATCH_SIZE = 100


def bulk_matriculate_students(*, actor, section, student_ids, effective_on, preview=True):
    if not 1 <= len(student_ids) <= MAX_BATCH_SIZE or len(set(student_ids)) != len(student_ids):
        raise DomainError("Seleccione entre 1 y 100 estudiantes distintos.")
    require_section_scope(actor=actor, codenames="enrollment_create", sections=[section])
    results = []
    # Un preview acumula ocupación dentro de su transacción, pero la revierte
    # completa al terminar. Así no promete la misma última vacante a cada fila.
    with transaction.atomic():
        section = (
            Section.objects.select_for_update()
            .select_related("offering__academic_cycle", "offering__grade", "offering__shift")
            .get(pk=section.pk)
        )
        for student_id in student_ids:
            row = {
                "student_id": str(student_id),
                "status": "error",
                "enrolment_id": None,
                "error": None,
            }
            try:
                with transaction.atomic():
                    student = Student.objects.get(public_id=student_id)
                    if not student.is_active:
                        raise DomainError("Un estudiante inactivo no puede matricularse.")
                    existing = Enrolment.objects.filter(
                        student=student,
                        section=section,
                        status="active",
                        effective_on=effective_on,
                    ).first()
                    if existing is not None:
                        row.update(status="existing", enrolment_id=str(existing.public_id))
                    else:
                        enrolment = matriculate_student(
                            student=student,
                            academic_cycle=section.academic_cycle,
                            grade=section.grade,
                            shift=section.shift,
                            section=section,
                            effective_on=effective_on,
                            actor=actor,
                        )
                        row.update(
                            status="ready" if preview else "created",
                            enrolment_id=None if preview else str(enrolment.public_id),
                        )
            except Student.DoesNotExist:
                row["error"] = "Estudiante no encontrado."
            except DomainError as exc:
                row["error"] = str(exc)
            results.append(row)
        if preview:
            transaction.set_rollback(True)
    succeeded = sum(row["status"] != "error" for row in results)
    record_event(
        actor=actor,
        action="enrolments.bulk_matriculation.previewed"
        if preview
        else "enrolments.bulk_matriculation.processed",
        resource="Enrolment",
        resource_identifier="bulk-initial",
        context={"total": len(results), "succeeded": succeeded, "failed": len(results) - succeeded},
    )
    return {
        "preview": preview,
        "total": len(results),
        "succeeded": succeeded,
        "failed": len(results) - succeeded,
        "results": results,
    }
