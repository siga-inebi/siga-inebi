from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.academics.cycle_policies import require_cycle_academic_writes
from apps.academics.models import Section
from apps.audit.services import record_event
from apps.common.db import unique_violation_as
from apps.common.exceptions import DomainError
from apps.enrolments.events import student_permanence_closed
from apps.enrolments.models import Enrolment, EnrolmentDocumentRequirement, StudentMovement

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
