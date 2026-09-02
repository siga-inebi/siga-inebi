from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.academics.cycle_policies import require_cycle_academic_writes
from apps.academics.models import Section
from apps.audit.services import record_event
from apps.common.db import unique_violation_as
from apps.common.exceptions import DomainError
from apps.enrolments.events import student_permanence_closed, student_permanence_reopened
from apps.enrolments.models import (
    Enrolment,
    EnrolmentDocumentRequirement,
    StudentMovement,
    StudentMovementAnnulment,
)

# Las dos unicas formas en que una matricula es un duplicado (ver los
# constraints del modelo). El mensaje se lee en la pantalla de matricula, asi que
# dice que hacer, no que constraint fallo.
DUPLICATE_ENROLMENT_MESSAGES = {
    "unique_active_enrolment_per_student": (
        "El estudiante ya tiene una inscripcion activa. Cierrala antes de inscribirlo de nuevo."
    ),
    "unique_enrolment_per_student_section": (
        "El estudiante ya estuvo inscrito en esa seccion. Repetir supone otro ciclo escolar."
    ),
}


def _validate_movement_enrolments(*, student, movement_type, source_enrolment, target_enrolment):
    expected_shapes = {
        StudentMovement.MovementType.SECTION_CHANGE: (True, True),
        StudentMovement.MovementType.TRANSFER_IN: (False, True),
        StudentMovement.MovementType.TRANSFER_OUT: (True, False),
        StudentMovement.MovementType.WITHDRAWAL: (True, False),
    }
    if movement_type not in expected_shapes:
        raise DomainError("Tipo de movimiento estudiantil no valido.")

    expected_source, expected_target = expected_shapes[movement_type]
    if (source_enrolment is not None) != expected_source or (
        (target_enrolment is not None) != expected_target
    ):
        raise DomainError("Las matriculas no corresponden al tipo de movimiento.")

    enrolments = (source_enrolment, target_enrolment)
    if any(enrolment and enrolment.student_id != student.pk for enrolment in enrolments):
        raise DomainError("Las matriculas del movimiento deben pertenecer al estudiante.")
    if source_enrolment is not None and source_enrolment.pk == getattr(
        target_enrolment, "pk", None
    ):
        raise DomainError("Las matriculas de origen y destino deben ser diferentes.")


@transaction.atomic
def record_student_movement(
    *,
    student,
    movement_type,
    source_enrolment=None,
    target_enrolment=None,
    effective_on=None,
    reason="",
    actor=None,
):
    """Registra evidencia inmutable; ejecutar la operacion corresponde a su caso de uso."""
    _validate_movement_enrolments(
        student=student,
        movement_type=movement_type,
        source_enrolment=source_enrolment,
        target_enrolment=target_enrolment,
    )
    reason = reason.strip()
    if movement_type == StudentMovement.MovementType.WITHDRAWAL and not reason:
        raise DomainError("La causa del retiro es obligatoria.")
    effective_on = effective_on or timezone.localdate()
    if source_enrolment is not None and effective_on < source_enrolment.effective_on:
        raise DomainError(
            "La fecha efectiva del movimiento no puede ser anterior a la matricula de origen."
        )

    movement = StudentMovement.objects.create(
        student=student,
        movement_type=movement_type,
        source_enrolment=source_enrolment,
        target_enrolment=target_enrolment,
        effective_on=effective_on,
        reason=reason,
    )
    record_event(
        actor=actor,
        action="enrolments.student_movement.recorded",
        resource="StudentMovement",
        resource_identifier=str(movement.pk),
        context={
            "student_id": student.pk,
            "movement_type": movement_type,
            "effective_on": effective_on.isoformat(),
            "source_enrolment_id": getattr(source_enrolment, "pk", None),
            "target_enrolment_id": getattr(target_enrolment, "pk", None),
        },
    )
    return movement


@transaction.atomic
def withdraw_student(*, enrolment, reason, actor=None, effective_on=None):
    require_cycle_academic_writes(
        cycle=enrolment.academic_cycle,
        operation="enrolment.withdraw_student",
    )
    if enrolment.status != Enrolment.EnrolmentStatus.ACTIVE:
        raise DomainError("Solo una matricula activa puede retirarse.")

    effective_on = effective_on or timezone.localdate()
    movement = record_student_movement(
        student=enrolment.student,
        movement_type=StudentMovement.MovementType.WITHDRAWAL,
        source_enrolment=enrolment,
        effective_on=effective_on,
        reason=reason,
        actor=actor,
    )
    enrolment.status = Enrolment.EnrolmentStatus.WITHDRAWN
    enrolment.ends_on = effective_on
    enrolment.save(update_fields=["status", "ends_on", "updated_at"])
    student = enrolment.student
    student.status = student.StudentStatus.WITHDRAWN
    student.save(update_fields=["status", "updated_at"])
    student_permanence_closed.send(
        sender=withdraw_student,
        student=student,
        reason=movement.reason,
        effective_on=effective_on,
        movement=movement,
        actor=actor,
    )
    record_event(
        actor=actor,
        action="enrolments.student.withdrawn",
        resource="Student",
        resource_identifier=str(student.pk),
        context={
            "enrolment_id": enrolment.pk,
            "movement_id": movement.pk,
            "effective_on": effective_on.isoformat(),
        },
    )
    return movement


@transaction.atomic
def transfer_student_out(*, enrolment, actor=None, effective_on=None, reason=""):
    require_cycle_academic_writes(
        cycle=enrolment.academic_cycle,
        operation="enrolment.transfer_student_out",
    )
    if enrolment.status != Enrolment.EnrolmentStatus.ACTIVE:
        raise DomainError("Solo una matricula activa puede trasladarse fuera de la institucion.")
    effective_on = effective_on or timezone.localdate()
    if effective_on > timezone.localdate():
        raise DomainError("Los traslados con fecha futura permanecen pendientes de definicion.")

    movement = record_student_movement(
        student=enrolment.student,
        movement_type=StudentMovement.MovementType.TRANSFER_OUT,
        source_enrolment=enrolment,
        effective_on=effective_on,
        reason=reason,
        actor=actor,
    )
    enrolment.status = Enrolment.EnrolmentStatus.COMPLETED
    enrolment.ends_on = effective_on
    enrolment.save(update_fields=["status", "ends_on", "updated_at"])
    student = enrolment.student
    student.status = student.StudentStatus.TRANSFERRED
    student.save(update_fields=["status", "updated_at"])
    student_permanence_closed.send(
        sender=transfer_student_out,
        student=student,
        reason=reason or "Traslado hacia otra institucion",
        effective_on=effective_on,
        movement=movement,
        actor=actor,
    )
    record_event(
        actor=actor,
        action="enrolments.student.transferred_out",
        resource="Student",
        resource_identifier=str(student.pk),
        context={"enrolment_id": enrolment.pk, "movement_id": movement.pk},
    )
    return movement


@transaction.atomic
def transfer_student_in(
    *, student, academic_cycle, grade, shift, section, actor=None, effective_on=None
):
    effective_on = effective_on or timezone.localdate()
    if effective_on > timezone.localdate():
        raise DomainError("Los traslados con fecha futura permanecen pendientes de definicion.")
    enrolment = matriculate_student(
        student=student,
        academic_cycle=academic_cycle,
        grade=grade,
        shift=shift,
        section=section,
        actor=actor,
        effective_on=effective_on,
    )
    movement = record_student_movement(
        student=student,
        movement_type=StudentMovement.MovementType.TRANSFER_IN,
        target_enrolment=enrolment,
        effective_on=effective_on,
        actor=actor,
    )
    record_event(
        actor=actor,
        action="enrolments.student.transferred_in",
        resource="Student",
        resource_identifier=str(student.pk),
        context={"enrolment_id": enrolment.pk, "movement_id": movement.pk},
    )
    return movement


@transaction.atomic
def annul_student_movement(*, movement, reason, actor):
    reason = reason.strip()
    if not reason:
        raise DomainError("El motivo de la anulacion es obligatorio.")
    if actor is None:
        raise DomainError("La anulacion debe identificar quien la autorizo.")

    movement = StudentMovement.objects.select_for_update().get(pk=movement.pk)
    if StudentMovementAnnulment.objects.filter(movement=movement).exists():
        raise DomainError("El movimiento ya fue anulado.")
    if movement.movement_type not in {
        StudentMovement.MovementType.WITHDRAWAL,
        StudentMovement.MovementType.SECTION_CHANGE,
    }:
        raise DomainError("Este tipo de movimiento todavia no admite anulacion segura.")

    source = movement.source_enrolment
    require_cycle_academic_writes(
        cycle=source.academic_cycle,
        operation="enrolment.annul_student_movement",
    )

    if movement.movement_type == StudentMovement.MovementType.WITHDRAWAL:
        student = movement.student
        if source.status != Enrolment.EnrolmentStatus.WITHDRAWN:
            raise DomainError("El retiro ya no coincide con el estado actual de la matricula.")
        if (
            Enrolment.objects.filter(
                student=student,
                status=Enrolment.EnrolmentStatus.ACTIVE,
            )
            .exclude(pk=source.pk)
            .exists()
        ):
            raise DomainError("El estudiante ya tiene otra matricula activa.")

        source.status = Enrolment.EnrolmentStatus.ACTIVE
        source.ends_on = None
        source.save(update_fields=["status", "ends_on", "updated_at"])
        student.status = student.StudentStatus.ACTIVE
        student.save(update_fields=["status", "updated_at"])
        student_permanence_reopened.send(
            sender=annul_student_movement,
            student=student,
            movement=movement,
            actor=actor,
        )
    else:
        target = Enrolment.objects.select_for_update().get(pk=movement.target_enrolment_id)
        if (
            source.status != Enrolment.EnrolmentStatus.COMPLETED
            or target.status != Enrolment.EnrolmentStatus.ACTIVE
        ):
            raise DomainError("El cambio de seccion ya no coincide con el estado actual.")
        if (
            Enrolment.objects.filter(
                student=movement.student,
                status=Enrolment.EnrolmentStatus.ACTIVE,
            )
            .exclude(pk=target.pk)
            .exists()
        ):
            raise DomainError("El estudiante ya tiene otra matricula activa.")
        _ensure_section_has_capacity(source.section)

        target.status = Enrolment.EnrolmentStatus.CANCELLED
        target.ends_on = max(movement.effective_on, target.effective_on)
        target.save(update_fields=["status", "ends_on", "updated_at"])
        source.status = Enrolment.EnrolmentStatus.ACTIVE
        source.ends_on = None
        source.save(update_fields=["status", "ends_on", "updated_at"])

    annulment = StudentMovementAnnulment.objects.create(
        movement=movement,
        reason=reason,
        annulled_by=actor,
    )
    record_event(
        actor=actor,
        action="enrolments.student_movement.annulled",
        resource="StudentMovement",
        resource_identifier=str(movement.public_id),
        context={
            "annulment_id": str(annulment.public_id),
            "movement_type": movement.movement_type,
            "student_id": str(movement.student.public_id),
        },
    )
    return annulment


def section_occupancy(*, academic_cycle=None, grade=None, section=None, include_inactive=False):
    """
    Declared capacity and real-time occupancy per section (RF-EST-008).

    Annotates ``_active_enrolments`` so ``Section.active_enrolment_count`` and
    ``Section.available_seats`` read the annotation instead of one query per
    row (see the property docstrings in ``apps.academics.models.Section``).
    Filters are all optional; passing none of them lists every section.
    """
    queryset = Section.objects.select_related(
        "offering__grade__level", "offering__shift", "offering__academic_cycle"
    ).annotate(
        _active_enrolments=Count(
            "enrolments", filter=Q(enrolments__status=Enrolment.EnrolmentStatus.ACTIVE)
        )
    )
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    if academic_cycle is not None:
        queryset = queryset.filter(offering__academic_cycle=academic_cycle)
    if grade is not None:
        queryset = queryset.filter(offering__grade=grade)
    if section is not None:
        queryset = queryset.filter(pk=section.pk)
    return queryset.order_by(
        "offering__grade__level__sequence", "offering__grade__sequence", "name"
    )


def _ensure_section_has_capacity(section):
    locked_section = section.__class__.objects.select_for_update().get(pk=section.pk)
    if locked_section.capacity == 0:
        return

    active_count = Enrolment.objects.filter(
        section=locked_section,
        status=Enrolment.EnrolmentStatus.ACTIVE,
    ).count()
    if active_count >= locked_section.capacity:
        raise DomainError("La seccion alcanzo su cupo.")


def active_enrolments(*, student=None):
    queryset = (
        Enrolment.objects.filter(is_active=True, status=Enrolment.EnrolmentStatus.ACTIVE)
        .select_related("student", "academic_cycle", "grade", "section")
        .order_by("student__student_code", "effective_on", "pk")
    )
    return queryset.filter(student=student) if student is not None else queryset


def enrolment_history(*, student):
    return (
        Enrolment.objects.filter(student=student)
        .select_related("student", "academic_cycle", "grade", "section")
        .order_by("-effective_on", "-created_at", "-pk")
    )


@transaction.atomic
def create_enrolment(
    *,
    student,
    academic_cycle,
    grade,
    section,
    actor=None,
    effective_on=None,
    ends_on=None,
):
    effective_on = effective_on or timezone.localdate()

    require_cycle_academic_writes(
        cycle=academic_cycle,
        operation="enrolment.create",
    )
    if section.academic_cycle.id != academic_cycle.pk:
        raise DomainError("La seccion debe pertenecer al ciclo escolar.")
    if section.grade.id != grade.pk:
        raise DomainError("La seccion debe pertenecer al grado.")
    if ends_on is not None and effective_on > ends_on:
        raise DomainError(
            "La fecha de fin de la matricula no puede ser anterior a su fecha de vigencia."
        )
    _ensure_section_has_capacity(section)

    with unique_violation_as(DUPLICATE_ENROLMENT_MESSAGES):
        enrolment = Enrolment.objects.create(
            student=student,
            academic_cycle=academic_cycle,
            grade=grade,
            section=section,
            effective_on=effective_on,
            ends_on=ends_on,
        )
    record_event(
        actor=actor,
        action="enrolments.enrolment.created",
        resource="Enrolment",
        resource_identifier=str(enrolment.pk),
        context={"student_id": student.pk, "section_id": section.pk},
    )
    return enrolment


@transaction.atomic
def matriculate_student(
    *, student, academic_cycle, grade, shift, section, actor=None, effective_on=None
):
    """
    Enrol a student into a section of a cycle.

    No exige que el expediente este en "preinscrito". Lo exigia, y eso obligaba
    a devolver a preinscrito a cada estudiante activo antes de matricularlo en el
    ciclo siguiente: un paso que no protege nada, porque lo que hay que evitar es
    la matricula DUPLICADA, y de eso se encargan los constraints del modelo (una
    sola activa por estudiante, y nunca dos veces la misma seccion).

    El expediente dado de baja si se rechaza: no es una regla de duplicados sino
    de existencia, y matricular a alguien archivado lo reviviria a medias.
    """
    if not student.is_active:
        raise DomainError("Un estudiante inactivo no puede matricularse.")
    if section.shift.id != shift.pk:
        raise DomainError("La seccion debe pertenecer a la jornada seleccionada.")

    enrolment = create_enrolment(
        student=student,
        academic_cycle=academic_cycle,
        grade=grade,
        section=section,
        actor=actor,
        effective_on=effective_on,
    )
    student.status = student.StudentStatus.ACTIVE
    student.save(update_fields=["status", "updated_at"])
    record_event(
        actor=actor,
        action="enrolments.student.matriculated",
        resource="Student",
        resource_identifier=str(student.pk),
        context={
            "enrolment_id": enrolment.pk,
            "academic_cycle_id": academic_cycle.pk,
            "grade_id": grade.pk,
            "shift_id": shift.pk,
            "section_id": section.pk,
        },
    )
    return enrolment


def _close_open_enrolments(*, student, academic_cycle, effective_on, actor=None):
    """
    Cierra como completadas las matriculas activas de otros ciclos.

    Es lo que hace posible reinscribir sin pasar antes por una pantalla de
    cierre: el ciclo anterior termino, la matricula que quedo abierta es un
    pendiente administrativo, no una decision.
    """
    open_ones = list(
        Enrolment.objects.filter(student=student, status=Enrolment.EnrolmentStatus.ACTIVE).exclude(
            academic_cycle=academic_cycle
        )
    )
    for enrolment in open_ones:
        enrolment.status = Enrolment.EnrolmentStatus.COMPLETED
        # La vigencia no puede terminar antes de empezar: una matricula del ciclo
        # pasado registrada con fecha posterior cerraria con un rango invalido.
        enrolment.ends_on = max(effective_on, enrolment.effective_on)
        enrolment.save(update_fields=["status", "ends_on", "updated_at"])
        record_event(
            actor=actor,
            action="enrolments.enrolment.completed_on_reenrolment",
            resource="Enrolment",
            resource_identifier=str(enrolment.pk),
            context={
                "student_id": student.pk,
                "next_academic_cycle_id": academic_cycle.pk,
                "ends_on": enrolment.ends_on.isoformat(),
            },
        )
    return open_ones


@transaction.atomic
def reenrol_student(
    *, student, academic_cycle, grade, shift, section, actor=None, effective_on=None
):
    """
    Create a new-cycle enrolment using the student's existing record.

    Lo que distingue reinscribir de matricular es el historial: sin matricula
    previa no hay nada que continuar, y eso si se sigue exigiendo. El estado del
    expediente ya no, por lo mismo que en ``matriculate_student``.

    La matricula anterior que siguiera activa se CIERRA aqui, en la misma
    transaccion: un estudiante cursa en un lugar a la vez, y dejar la del ciclo
    pasado abierta era lo que hacia que el expediente dijera dos cosas. Se cierra
    como completada, con la fecha en que arranca la nueva.
    """
    if not student.is_active:
        raise DomainError("Un estudiante inactivo no puede reinscribirse.")

    previous = (
        Enrolment.objects.filter(student=student)
        .exclude(academic_cycle=academic_cycle)
        .exclude(status=Enrolment.EnrolmentStatus.CANCELLED)
        .order_by("-effective_on", "-created_at")
        .first()
    )
    if previous is None:
        raise DomainError("El estudiante no tiene matricula previa de la cual heredar.")
    if section.shift.id != shift.pk:
        raise DomainError("La seccion debe pertenecer a la jornada seleccionada.")

    _close_open_enrolments(
        student=student,
        academic_cycle=academic_cycle,
        effective_on=effective_on or timezone.localdate(),
        actor=actor,
    )

    enrolment = create_enrolment(
        student=student,
        academic_cycle=academic_cycle,
        grade=grade,
        section=section,
        actor=actor,
        effective_on=effective_on,
    )
    student.status = student.StudentStatus.ACTIVE
    student.save(update_fields=["status", "updated_at"])
    record_event(
        actor=actor,
        action="enrolments.student.reenrolled",
        resource="Student",
        resource_identifier=str(student.pk),
        context={
            "enrolment_id": enrolment.pk,
            "previous_enrolment_id": previous.pk,
            "academic_cycle_id": academic_cycle.pk,
        },
    )
    return enrolment


def _bulk_reenrolment_result(*, source_enrolment, target_section, effective_on, actor, preview):
    student = source_enrolment.student
    target_cycle = target_section.academic_cycle
    if not source_enrolment.is_active or source_enrolment.status not in {
        Enrolment.EnrolmentStatus.ACTIVE,
        Enrolment.EnrolmentStatus.COMPLETED,
    }:
        raise DomainError("La matricula seleccionada no es elegible para reinscripcion.")
    if target_cycle.year != source_enrolment.academic_cycle.year + 1:
        raise DomainError("La seccion destino debe pertenecer al ciclo escolar siguiente.")
    if target_cycle.institution_id != source_enrolment.academic_cycle.institution_id:
        raise DomainError("El ciclo destino debe pertenecer a la misma institucion.")
    if not actor.has_scoped_permission(
        "enrollment_create",
        scope={"student": student, "section": target_section, "module_key": "enrolments"},
    ):
        raise DomainError("El actor no tiene alcance sobre el estudiante seleccionado.")

    existing = (
        Enrolment.objects.filter(student=student, academic_cycle=target_cycle)
        .exclude(status=Enrolment.EnrolmentStatus.CANCELLED)
        .first()
    )
    if existing is not None:
        if existing.section_id != target_section.pk:
            raise DomainError("El estudiante ya tiene matricula en otra seccion del ciclo destino.")
        return existing, "existing"

    enrolment = reenrol_student(
        student=student,
        academic_cycle=target_cycle,
        grade=target_section.grade,
        shift=target_section.shift,
        section=target_section,
        effective_on=effective_on,
        actor=actor,
    )
    return enrolment, "ready" if preview else "created"


def bulk_reenrol_students(*, items, effective_on, actor, preview=True):
    """Preview or process explicitly selected next-cycle re-enrolments independently."""
    results = []
    for item in items:
        source_id = item["source_enrolment_id"]
        section_id = item["target_section_id"]
        try:
            with transaction.atomic():
                source = Enrolment.objects.select_related(
                    "student", "academic_cycle__institution"
                ).get(public_id=source_id)
                target = Section.objects.select_related(
                    "offering__academic_cycle__institution",
                    "offering__grade",
                    "offering__shift",
                ).get(public_id=section_id)
                enrolment, result_status = _bulk_reenrolment_result(
                    source_enrolment=source,
                    target_section=target,
                    effective_on=effective_on,
                    actor=actor,
                    preview=preview,
                )
                result = {
                    "source_enrolment_id": str(source.public_id),
                    "target_section_id": str(target.public_id),
                    "student_id": str(source.student.public_id),
                    "status": result_status,
                    "enrolment_id": (
                        None if result_status == "ready" else str(enrolment.public_id)
                    ),
                    "error": None,
                }
                if preview and result_status != "existing":
                    transaction.set_rollback(True)
        except Enrolment.DoesNotExist:
            result = _bulk_error(source_id, section_id, "Matricula de origen no encontrada.")
        except Section.DoesNotExist:
            result = _bulk_error(source_id, section_id, "Seccion destino no encontrada.")
        except DomainError as exc:
            result = _bulk_error(source_id, section_id, str(exc))
        results.append(result)

    succeeded = sum(result["status"] != "error" for result in results)
    record_event(
        actor=actor,
        action="enrolments.bulk_reenrolment.previewed"
        if preview
        else "enrolments.bulk_reenrolment.processed",
        resource="Enrolment",
        resource_identifier="bulk-next-cycle",
        context={"total": len(results), "succeeded": succeeded, "failed": len(results) - succeeded},
    )
    return {
        "preview": preview,
        "total": len(results),
        "succeeded": succeeded,
        "failed": len(results) - succeeded,
        "results": results,
    }


def _bulk_error(source_id, section_id, message):
    return {
        "source_enrolment_id": str(source_id),
        "target_section_id": str(section_id),
        "student_id": None,
        "status": "error",
        "enrolment_id": None,
        "error": message,
    }


@transaction.atomic
def change_section(*, enrolment, new_section, actor=None, effective_on=None):
    require_cycle_academic_writes(
        cycle=enrolment.academic_cycle,
        operation="enrolment.change_section",
    )
    if new_section.academic_cycle.id != enrolment.academic_cycle_id:
        raise DomainError("La seccion debe pertenecer al ciclo escolar.")
    if new_section.grade.id != enrolment.grade_id:
        raise DomainError("La seccion debe pertenecer al grado.")
    if enrolment.status != Enrolment.EnrolmentStatus.ACTIVE:
        raise DomainError("Solo una matricula activa puede cambiar de seccion.")
    if new_section.id == enrolment.section_id:
        raise DomainError("La seccion destino debe ser distinta de la actual.")
    _ensure_section_has_capacity(new_section)

    effective_on = effective_on or timezone.localdate()
    enrolment.status = Enrolment.EnrolmentStatus.COMPLETED
    enrolment.ends_on = effective_on
    enrolment.save(update_fields=["status", "ends_on", "updated_at"])

    # Mismo mapeo de duplicados que el alta: mover a una seccion en la que el
    # estudiante ya estuvo choca con el constraint, y sin traducirlo saldria como
    # un 500 en vez del rechazo que la pantalla sabe explicar.
    with unique_violation_as(DUPLICATE_ENROLMENT_MESSAGES):
        replacement = Enrolment.objects.create(
            student=enrolment.student,
            academic_cycle=enrolment.academic_cycle,
            grade=enrolment.grade,
            section=new_section,
            effective_on=effective_on,
            status=Enrolment.EnrolmentStatus.ACTIVE,
        )
    record_student_movement(
        student=enrolment.student,
        movement_type=StudentMovement.MovementType.SECTION_CHANGE,
        source_enrolment=enrolment,
        target_enrolment=replacement,
        effective_on=effective_on,
        actor=actor,
    )
    record_event(
        actor=actor,
        action="enrolments.enrolment.section_changed",
        resource="Enrolment",
        resource_identifier=str(replacement.pk),
        context={
            "previous_enrolment_id": enrolment.pk,
            "new_section_id": new_section.pk,
        },
    )
    return replacement


@transaction.atomic
def set_document_requirement(
    *,
    enrolment,
    code,
    name,
    status=None,
    is_required=None,
    actor=None,
):
    if enrolment.academic_cycle.status == enrolment.academic_cycle.CycleStatus.CLOSED:
        raise DomainError("Un ciclo escolar cerrado no admite cambios en documentos.")

    code = code.strip().upper()
    name = name.strip()
    if not code:
        raise DomainError("El codigo del documento no puede estar vacio.")
    if not name:
        raise DomainError("El nombre del documento no puede estar vacio.")
    if status is not None and status not in EnrolmentDocumentRequirement.DeliveryStatus.values:
        raise DomainError("Estado de entrega del documento no valido.")

    # Only overwrite what the caller actually supplied: a partial update must not
    # reset the delivery state. On creation the model defaults fill the rest.
    defaults = {"name": name, "is_active": True}
    if status is not None:
        defaults["status"] = status
    if is_required is not None:
        defaults["is_required"] = is_required

    requirement, created = EnrolmentDocumentRequirement.objects.update_or_create(
        enrolment=enrolment,
        code=code,
        defaults=defaults,
    )
    record_event(
        actor=actor,
        action=(
            "enrolments.document_requirement.created"
            if created
            else "enrolments.document_requirement.updated"
        ),
        resource="EnrolmentDocumentRequirement",
        resource_identifier=str(requirement.pk),
        context={"enrolment_id": enrolment.pk, "code": code, "status": requirement.status},
    )
    return requirement


def pending_required_document_codes(*, enrolment):
    """Return the codes of active, required documents not yet delivered."""
    return list(
        EnrolmentDocumentRequirement.objects.filter(
            enrolment=enrolment, is_active=True, is_required=True
        )
        .exclude(status=EnrolmentDocumentRequirement.DeliveryStatus.DELIVERED)
        .values_list("code", flat=True)
    )
