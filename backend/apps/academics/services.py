"""
Domain services for the academic catalogue.

The catalogue is the structure enrolments are assigned to:

    Institution
      +-- Campus ("sede")
      |     +-- Shift ("jornada")
      +-- Level ("nivel")            (added in a later PR of this chain)
      +-- AcademicCycle ("ciclo")     (added in a later PR of this chain)

Every invariant lives here, never in views or serializers (AGENTS.md #8).

Uniqueness is delegated to the database constraints and translated back into a
``DomainError`` by ``unique_violation_as``. Reading first and writing afterwards
would leave a window for two concurrent requests to both pass the check.
"""

from datetime import timedelta

from django.db import transaction
from django.db.models import F, Max
from django.utils import timezone

from apps.academics import school_calendar
from apps.academics.cycle_policies import (
    require_cycle_academic_writes,
    require_cycle_planning_writes,
)
from apps.academics.models import (
    AcademicCycle,
    Campus,
    Classroom,
    ClassScheduleBlock,
    ClassSchedulePublication,
    ClassSession,
    CurriculumPlan,
    Grade,
    GradeOffering,
    Level,
    LevelSubject,
    Section,
    Shift,
    Subject,
    TeachingAssignment,
)
from apps.audit.services import record_event
from apps.common.codes import (
    create_with_generated_code,
    next_sequential_code,
    next_suffixed_code,
)
from apps.common.db import unique_violation_as
from apps.common.exceptions import DomainError
from apps.teachers.models import Teacher

# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _clean_code(value, *, field="code"):
    code = (value or "").strip().upper()
    if not code:
        raise DomainError(f"Se requiere {field} con contenido.")
    return code


def _clean_name(value, *, field="name"):
    name = (value or "").strip()
    if not name:
        raise DomainError(f"Se requiere {field} con contenido.")
    return name


def _require_active(instance, label):
    if not instance.is_active:
        raise DomainError(f"No se puede usar {label} '{instance}': su registro esta inactivo.")


def _has_open_cycle_usage(offering_queryset):
    """True when any of those offerings belongs to a cycle that is not closed."""
    return offering_queryset.exclude(
        academic_cycle__status=AcademicCycle.CycleStatus.CLOSED
    ).exists()


# --------------------------------------------------------------------------- #
# pedagogical order ("secuencia")
#
# ``sequence`` is the pedagogical order of levels inside the institution and of
# grades inside a level. It used to be typed as a raw number, which is the wrong
# question: nobody knows "which number is Basico", they know "Basico goes after
# Primaria". Worse, inserting one in the middle meant renumbering every level
# below it by hand, one form at a time, against a unique constraint that rejects
# the intermediate states.
#
# So the API asks for a POSITION (``insert_after``) and the order is recomputed
# here. ``sequence`` stays accepted for the callers that already send a number.
# --------------------------------------------------------------------------- #

# "No position supplied": append at the end. Distinct from ``None``, which is a
# real position — the first one.
APPEND = object()


def _next_sequence(queryset):
    return (queryset.aggregate(top=Max("sequence"))["top"] or 0) + 1


def _apply_order(queryset, ordered):
    """
    Write 1..n over ``ordered``, which must hold every row of ``queryset``.

    The whole block is parked above every sequence in use before being laid back
    down: PostgreSQL validates a unique index row by row inside one statement,
    so renumbering in place collides with the rows that have not moved yet.
    """
    parked = _next_sequence(queryset)
    queryset.update(sequence=F("sequence") + parked)
    for position, row in enumerate(ordered, start=1):
        queryset.filter(pk=row.pk).update(sequence=position)
        row.sequence = position


def _ordered_with(queryset, instance, insert_after):
    """Rows of ``queryset`` in their final order, with ``instance`` moved into place."""
    rows = [row for row in queryset.order_by("sequence", "pk") if row.pk != instance.pk]
    if insert_after is None:
        index = 0
    else:
        found = next(
            (position for position, row in enumerate(rows) if row.pk == insert_after.pk),
            None,
        )
        if found is None:
            # Un hermano de otro nivel (o de otra institucion) dejaria el orden
            # a medio escribir: se rechaza antes de tocar una sola fila.
            raise DomainError("El elemento de referencia no pertenece al mismo grupo.")
        index = found + 1
    rows.insert(index, instance)
    return rows


def _place_in_order(*, queryset, instance, insert_after):
    """
    Move ``instance`` right after ``insert_after`` (or first, when it is ``None``).

    Renumbers the siblings so the visible order has no holes: an "Orden" column
    reading 1, 2, 4 looks like a bug even when the order is right.
    """
    if insert_after is APPEND:
        return instance
    if insert_after is not None and insert_after.pk == instance.pk:
        raise DomainError("Un elemento no puede insertarse despues de si mismo.")
    _apply_order(queryset, _ordered_with(queryset, instance, insert_after))
    return instance


def _audit(actor, action, instance, **context):
    record_event(
        actor=actor,
        action=action,
        resource=type(instance).__name__,
        resource_identifier=str(instance.pk),
        context=context,
    )


def _cycle_conflicts(*, year, name):
    return {
        "unique_cycle_name_per_institution": (
            f"Academic cycle name '{name}' already exists for this institution."
        ),
        "unique_cycle_year_per_institution": (
            f"Academic cycle year {year} already exists for this institution."
        ),
        "academic_cycle_no_overlapping_dates": (
            "Academic cycle dates cannot overlap another cycle in the institution."
        ),
        "unique_active_cycle_per_institution": (
            "Hay que cerrar el ciclo activo antes de activar otro."
        ),
    }


def academic_cycle_defaults(year):
    """
    Name and validity dates a cycle of ``year`` gets when nobody supplies them.

    Published as-is by the API so the form can show what it is about to send
    instead of a blank field with a rule hidden in the backend.
    """
    starts_on, ends_on = school_calendar.cycle_dates(year)
    return {
        "year": year,
        "name": school_calendar.cycle_name(year),
        "starts_on": starts_on,
        "ends_on": ends_on,
    }


def create_academic_cycle(
    *, institution, year, name=None, starts_on=None, ends_on=None, description="", actor=None
):
    """
    Register a non-overlapping cycle in preparation (RF-CIC-001).

    ``name``, ``starts_on`` and ``ends_on`` are optional: the year alone
    determines all three (see ``apps.academics.school_calendar``). They stay
    accepted because a ministerial agreement can move the calendar, and the
    name of a cycle is institutional text, not a computed value.
    """
    defaults = academic_cycle_defaults(year)
    name = _clean_name(name if (name or "").strip() else defaults["name"])
    starts_on = starts_on or defaults["starts_on"]
    ends_on = ends_on or defaults["ends_on"]
    description = (description or "").strip()
    if starts_on > ends_on:
        raise DomainError(
            "La fecha de fin del ciclo escolar no puede ser anterior a su fecha de inicio."
        )
    if starts_on.year != year:
        raise DomainError(
            "El ano del ciclo escolar debe coincidir con el ano de su fecha de inicio."
        )

    with unique_violation_as(_cycle_conflicts(year=year, name=name)):
        cycle = AcademicCycle.objects.create(
            institution=institution,
            year=year,
            name=name,
            description=description,
            starts_on=starts_on,
            ends_on=ends_on,
            status=AcademicCycle.CycleStatus.DRAFT,
        )
    _audit(
        actor,
        "academics.cycle.created",
        cycle,
        year=year,
        status=cycle.status,
        starts_on=starts_on.isoformat(),
        ends_on=ends_on.isoformat(),
    )
    return cycle


def _academic_cycle_opening_gaps(cycle):
    offerings = list(
        cycle.grade_offerings.filter(is_active=True)
        .select_related("grade", "shift")
        .prefetch_related("sections")
    )
    if not offerings:
        return ["at least one grade offering"]

    gaps = []
    subjects_by_grade = {}
    for plan in cycle.curriculum_plans.filter(is_active=True).select_related("subject"):
        subjects_by_grade.setdefault(plan.grade_id, []).append(plan.subject)

    # Current (ends_on is null) teaching assignments, keyed by the pair every
    # subarea of a section must clear (RF-EST-010): no partial credit for a
    # closed, superseded assignment.
    assigned_pairs = set(
        cycle.teaching_assignments.filter(ends_on__isnull=True).values_list(
            "section_id", "subject_id"
        )
    )

    reported_plan_gaps = set()
    for offering in offerings:
        active_sections = [section for section in offering.sections.all() if section.is_active]
        if not active_sections:
            gaps.append(
                f"faltan secciones del grado '{offering.grade.name}' en la jornada "
                f"'{offering.shift.name}'"
            )
        subjects = subjects_by_grade.get(offering.grade_id)
        if subjects is None:
            if offering.grade_id not in reported_plan_gaps:
                gaps.append(f"falta el plan de estudios del grado '{offering.grade.name}'")
                reported_plan_gaps.add(offering.grade_id)
            continue
        for section in active_sections:
            for subject in subjects:
                if (section.id, subject.id) not in assigned_pairs:
                    gaps.append(
                        f"falta asignar docente para '{subject.name}' en la seccion "
                        f"'{section.name}' del grado '{offering.grade.name}'"
                    )
    return gaps


@transaction.atomic
def clone_academic_cycle(
    *,
    source_cycle,
    year,
    name=None,
    starts_on=None,
    ends_on=None,
    description="",
    include_teaching_assignments=False,
    actor=None,
):
    """Create an independent draft cycle from existing academic structure (RF-CIC-007)."""
    source = AcademicCycle.objects.select_for_update().get(pk=source_cycle.pk)
    if source.status != AcademicCycle.CycleStatus.CLOSED:
        raise DomainError("Solo se puede clonar un ciclo escolar cerrado.")
    target = create_academic_cycle(
        institution=source.institution,
        year=year,
        name=name,
        starts_on=starts_on,
        ends_on=ends_on,
        description=description,
        actor=actor,
    )

    section_map = {}
    offerings = source.grade_offerings.select_related("grade", "shift").prefetch_related("sections")
    for source_offering in offerings:
        target_offering = GradeOffering.objects.create(
            academic_cycle=target,
            grade=source_offering.grade,
            shift=source_offering.shift,
            is_active=source_offering.is_active,
        )
        for source_section in source_offering.sections.all():
            target_section = Section.objects.create(
                offering=target_offering,
                name=source_section.name,
                capacity=source_section.capacity,
                is_active=source_section.is_active,
            )
            section_map[source_section.pk] = target_section

    CurriculumPlan.objects.bulk_create(
        [
            CurriculumPlan(
                academic_cycle=target,
                grade=plan.grade,
                subject=plan.subject,
                is_required=plan.is_required,
                is_active=plan.is_active,
            )
            for plan in source.curriculum_plans.select_related("grade", "subject")
        ]
    )

    assignment_count = 0
    if include_teaching_assignments:
        current_assignments = source.teaching_assignments.filter(
            ends_on__isnull=True
        ).select_related("section", "subject", "teacher")
        assignments = [
            TeachingAssignment(
                academic_cycle=target,
                section=section_map[assignment.section_id],
                subject=assignment.subject,
                teacher=assignment.teacher,
                starts_on=target.starts_on,
                is_active=assignment.is_active,
            )
            for assignment in current_assignments
            if assignment.section_id in section_map
        ]
        TeachingAssignment.objects.bulk_create(assignments)
        assignment_count = len(assignments)

    _audit(
        actor,
        "academics.cycle.cloned",
        target,
        source_cycle_id=source.pk,
        include_teaching_assignments=include_teaching_assignments,
        grade_offering_count=target.grade_offerings.count(),
        section_count=len(section_map),
        curriculum_plan_count=target.curriculum_plans.count(),
        teaching_assignment_count=assignment_count,
    )
    return target


@transaction.atomic
def activate_academic_cycle(*, cycle, actor=None):
    """Activate a prepared cycle with its available opening structure validated."""
    locked = AcademicCycle.objects.select_for_update().get(pk=cycle.pk)
    if locked.status != AcademicCycle.CycleStatus.DRAFT:
        raise DomainError("Solo se puede activar un ciclo escolar en preparacion.")
    if (
        AcademicCycle.objects.select_for_update()
        .filter(
            institution=locked.institution,
            status=AcademicCycle.CycleStatus.ACTIVE,
        )
        .exclude(pk=locked.pk)
        .exists()
    ):
        raise DomainError("Hay que cerrar el ciclo activo antes de activar otro.")
    opening_gaps = _academic_cycle_opening_gaps(locked)
    if opening_gaps:
        raise DomainError(
            "La estructura del ciclo escolar esta incompleta: " + "; ".join(opening_gaps) + "."
        )

    locked.status = AcademicCycle.CycleStatus.ACTIVE
    with unique_violation_as(_cycle_conflicts(year=locked.year, name=locked.name)):
        locked.save(update_fields=["status", "updated_at"])
    _audit(actor, "academics.cycle.activated", locked, status=locked.status)
    return locked


def _cycle_closure_gaps(cycle):
    """
    Evaluation units that block closing the cycle (RF-CIC-004): still open, or
    closed with a recovery window that has not expired yet.

    Read through the reverse relation only (``cycle.evaluation_units``), the
    same way ``Section.active_enrolment_count`` reads ``enrolments`` without
    importing that domain's models — ``evaluation`` depends on ``academics``,
    not the other way around (domain-map.md).
    """
    today = timezone.localdate()
    gaps = []
    for unit in cycle.evaluation_units.order_by("number"):
        if unit.status != "closed":
            gaps.append(f"la unidad de evaluacion '{unit.name}' sigue abierta")
        elif unit.recovery_ends_on is not None and today <= unit.recovery_ends_on:
            gaps.append(f"la ventana de recuperacion de la unidad '{unit.name}' aun no vence")
    return gaps


@transaction.atomic
def close_academic_cycle(*, cycle, actor=None):
    """
    Close an active cycle once every evaluation unit is settled (RF-CIC-004).

    Closing freezes the cycle: ``cycle_policies.require_cycle_academic_writes``
    already rejects academic mutations once ``status`` is ``CLOSED``, so no
    separate "freeze results" step exists yet here — there is no results
    capability implemented in the codebase to freeze (see PR notes).
    """
    locked = AcademicCycle.objects.select_for_update().get(pk=cycle.pk)
    if locked.status != AcademicCycle.CycleStatus.ACTIVE:
        raise DomainError("Solo se puede cerrar un ciclo escolar activo.")

    gaps = _cycle_closure_gaps(locked)
    if gaps:
        raise DomainError("No se puede cerrar el ciclo escolar: " + "; ".join(gaps) + ".")

    locked.status = AcademicCycle.CycleStatus.CLOSED
    locked.save(update_fields=["status", "updated_at"])
    _audit(actor, "academics.cycle.closed", locked, status=locked.status)
    return locked


def _changed(instance, actor, action, **candidates):
    """
    Apply the fields whose value was actually supplied, persist only those, and
    audit what changed. ``None`` means "not supplied", never "set to null".
    """
    fields = [name for name, value in candidates.items() if value is not None]
    for name in fields:
        setattr(instance, name, candidates[name])

    instance.save(update_fields=[*fields, "updated_at"])
    _audit(actor, action, instance, fields=fields)
    return instance


# --------------------------------------------------------------------------- #
# campuses ("sedes")
# --------------------------------------------------------------------------- #


def _campus_conflicts(code):
    return {
        "unique_campus_code_per_institution": (
            f"Campus code '{code}' already exists for this institution."
        ),
        "unique_main_campus_per_institution": (
            "Another campus was promoted to main at the same time. Retry the operation."
        ),
    }


# Serie del codigo de sede: "SED-01".
CAMPUS_CODE_PREFIX = "SED"
CAMPUS_CODE_WIDTH = 2
CAMPUS_CODE_CONSTRAINT = "unique_campus_code_per_institution"


def next_campus_code(*, institution):
    """Siguiente codigo libre de sede para la institucion."""
    return next_sequential_code(
        queryset=Campus.objects.filter(institution=institution),
        field="code",
        prefix=CAMPUS_CODE_PREFIX,
        width=CAMPUS_CODE_WIDTH,
    )


@transaction.atomic
def create_campus(*, institution, name, code=None, address="", is_main=False, actor=None):
    """
    Register a campus.

    Rules:
    - Code is optional: without one, the next of the institution series is
      generated. Supplied codes are normalised to upper case and unique per
      institution, including inactive campuses so history stays readable
      (ADR-0006).
    - At most one main campus per institution; promoting a new one demotes the
      previous main campus.
    """
    name = _clean_name(name)
    supplied = (code or "").strip()
    address = (address or "").strip()

    if is_main:
        Campus.objects.filter(institution=institution, is_main=True).update(is_main=False)

    def build(value):
        return Campus.objects.create(
            institution=institution,
            name=name,
            code=value,
            address=address,
            is_main=is_main,
        )

    if supplied:
        code = _clean_code(supplied)
        with unique_violation_as(_campus_conflicts(code)):
            campus = build(code)
    else:
        campus = create_with_generated_code(
            build=build,
            generate=lambda: next_campus_code(institution=institution),
            constraint=CAMPUS_CODE_CONSTRAINT,
        )

    _audit(
        actor,
        "academics.campus.created",
        campus,
        code=campus.code,
        is_main=is_main,
        generated=not supplied,
    )
    return campus


@transaction.atomic
def update_campus(*, campus, name=None, address=None, is_main=None, actor=None):
    """Update the descriptive attributes of a campus. The code is immutable."""
    if name is not None:
        name = _clean_name(name)
    if address is not None:
        address = address.strip()

    if is_main is not None and is_main != campus.is_main and is_main:
        _require_active(campus, "el campus")
        Campus.objects.filter(institution=campus.institution, is_main=True).exclude(
            pk=campus.pk
        ).update(is_main=False)

    # ``is_main=False`` is a real value, so it cannot ride on the None convention.
    fields = {"name": name, "address": address}
    if is_main is not None and is_main != campus.is_main:
        campus.is_main = is_main
        fields["is_main"] = is_main

    with unique_violation_as(_campus_conflicts(campus.code)):
        return _changed(campus, actor, "academics.campus.updated", **fields)


@transaction.atomic
def deactivate_campus(*, campus, actor=None):
    """
    Deactivate a campus instead of deleting it (RF-EST-012).

    Rules:
    - Refused while any of its shifts is used by a cycle that is not closed.
    - Cascades to the campus shifts and clears the main flag.
    - Idempotent.
    """
    if not campus.is_active:
        return campus

    if _has_open_cycle_usage(GradeOffering.objects.filter(shift__campus=campus)):
        raise DomainError(
            f"El campus '{campus.name}' lo usa un ciclo activo y no puede desactivarse."
        )

    campus.is_active = False
    campus.is_main = False
    campus.save(update_fields=["is_active", "is_main", "updated_at"])
    Shift.objects.filter(campus=campus, is_active=True).update(is_active=False)

    _audit(actor, "academics.campus.deactivated", campus, code=campus.code)
    return campus


# --------------------------------------------------------------------------- #
# shifts ("jornadas")
# --------------------------------------------------------------------------- #


def create_shift(*, campus, name, code, actor=None):
    """
    Register a shift for a campus (RF-EST-002).

    Rules:
    - Campus must be active.
    - Code is unique per campus, so two campuses may both have "MAT".
    """
    _require_active(campus, "el campus")
    name = _clean_name(name)
    code = _clean_code(code)

    conflicts = {
        "unique_shift_code_per_campus": (
            f"Shift code '{code}' already exists for campus '{campus.name}'."
        )
    }
    with unique_violation_as(conflicts):
        shift = Shift.objects.create(campus=campus, name=name, code=code)

    _audit(actor, "academics.shift.created", shift, campus_id=campus.pk, code=code)
    return shift


def update_shift(*, shift, name=None, actor=None):
    """Rename a shift. The code is immutable."""
    if name is None:
        return shift
    return _changed(shift, actor, "academics.shift.updated", name=_clean_name(name))


def deactivate_shift(*, shift, actor=None):
    """Deactivate a shift unless a non-closed cycle still offers grades in it."""
    if not shift.is_active:
        return shift

    if _has_open_cycle_usage(GradeOffering.objects.filter(shift=shift)):
        raise DomainError(
            f"La jornada '{shift.name}' la usa un ciclo activo y no puede desactivarse."
        )

    shift.is_active = False
    shift.save(update_fields=["is_active", "updated_at"])
    _audit(actor, "academics.shift.deactivated", shift, code=shift.code)
    return shift


# --------------------------------------------------------------------------- #
# classrooms ("aulas") -- RF-AUL-001
# --------------------------------------------------------------------------- #


def create_classroom(*, campus, name, code, location="", actor=None):
    """
    Register a classroom, lab or venue for a campus (RF-AUL-001).

    Rules:
    - Campus must be active.
    - Code is unique per campus, so two campuses may both have "A-101".
    """
    _require_active(campus, "el campus")
    name = _clean_name(name)
    code = _clean_code(code)

    conflicts = {
        "unique_classroom_code_per_campus": (
            f"Classroom code '{code}' already exists for campus '{campus.name}'."
        )
    }
    with unique_violation_as(conflicts):
        classroom = Classroom.objects.create(
            campus=campus, name=name, code=code, location=(location or "").strip()
        )

    _audit(actor, "academics.classroom.created", classroom, campus_id=campus.pk, code=code)
    return classroom


def update_classroom(*, classroom, name=None, location=None, actor=None):
    """Rename and/or relocate a classroom. The code is immutable."""
    changes = {}
    if name is not None:
        changes["name"] = _clean_name(name)
    if location is not None:
        changes["location"] = location.strip()
    if not changes:
        return classroom
    return _changed(classroom, actor, "academics.classroom.updated", **changes)


def deactivate_classroom(*, classroom, actor=None):
    if not classroom.is_active:
        return classroom
    classroom.is_active = False
    classroom.save(update_fields=["is_active", "updated_at"])
    _audit(actor, "academics.classroom.deactivated", classroom, code=classroom.code)
    return classroom


# --------------------------------------------------------------------------- #
# schedule blocks ("rejilla de bloques") -- RF-HOR-001
# --------------------------------------------------------------------------- #


def _schedule_block_conflicts(number):
    return {
        "unique_schedule_block_number_per_shift": (
            f"Schedule block number {number} already exists for this shift."
        ),
    }


def _validate_block_times(starts_on, ends_on):
    if starts_on is None or ends_on is None:
        raise DomainError("Se requiere hora de inicio y hora de fin del bloque.")
    if starts_on >= ends_on:
        raise DomainError("La hora de inicio del bloque debe ser anterior a la hora de fin.")


def _require_no_schedule_block_overlap(*, shift, starts_on, ends_on, exclude_pk=None):
    """
    No native PostgreSQL range type exists for ``time`` (see the model
    docstring), so this invariant cannot be an ``ExclusionConstraint`` like
    its date-range counterparts. ``select_for_update`` locks the shift's
    existing blocks for the rest of the transaction so two concurrent
    requests cannot both pass the check.
    """
    existing = ClassScheduleBlock.objects.select_for_update().filter(shift=shift)
    if exclude_pk is not None:
        existing = existing.exclude(pk=exclude_pk)
    for block in existing:
        if starts_on < block.ends_on and block.starts_on < ends_on:
            raise DomainError(
                f"El bloque se solapa con '{block.name}' ({block.starts_on}-{block.ends_on})."
            )


def create_class_schedule_block(*, shift, number, name, starts_on, ends_on, actor=None):
    """
    Register a period block in a shift's schedule grid (RF-HOR-001).

    Rules:
    - Shift must be active.
    - starts_on must be strictly before ends_on.
    - Block number is unique within the shift.
    - Blocks within the same shift cannot overlap in time.
    """
    _require_active(shift, "la jornada")
    name = _clean_name(name)
    _validate_block_times(starts_on, ends_on)

    with unique_violation_as(_schedule_block_conflicts(number)):
        _require_no_schedule_block_overlap(shift=shift, starts_on=starts_on, ends_on=ends_on)
        block = ClassScheduleBlock.objects.create(
            shift=shift, number=number, name=name, starts_on=starts_on, ends_on=ends_on
        )

    _audit(
        actor,
        "academics.schedule_block.created",
        block,
        shift_id=shift.pk,
        number=number,
        starts_on=str(starts_on),
        ends_on=str(ends_on),
    )
    return block


def update_class_schedule_block(*, block, name=None, starts_on=None, ends_on=None, actor=None):
    """Rename and/or retime a schedule block. Number and shift are immutable."""
    new_starts_on = block.starts_on if starts_on is None else starts_on
    new_ends_on = block.ends_on if ends_on is None else ends_on
    if starts_on is not None or ends_on is not None:
        _validate_block_times(new_starts_on, new_ends_on)
        with transaction.atomic():
            _require_no_schedule_block_overlap(
                shift=block.shift,
                starts_on=new_starts_on,
                ends_on=new_ends_on,
                exclude_pk=block.pk,
            )

    changes = {}
    if name is not None:
        changes["name"] = _clean_name(name)
    if starts_on is not None:
        changes["starts_on"] = new_starts_on
    if ends_on is not None:
        changes["ends_on"] = new_ends_on
    if not changes:
        return block
    return _changed(block, actor, "academics.schedule_block.updated", **changes)


def deactivate_class_schedule_block(*, block, actor=None):
    if not block.is_active:
        return block
    block.is_active = False
    block.save(update_fields=["is_active", "updated_at"])
    _audit(actor, "academics.schedule_block.deactivated", block, shift_id=block.shift_id)
    return block


# --------------------------------------------------------------------------- #
# levels ("niveles")
# --------------------------------------------------------------------------- #


def _level_conflicts(code, sequence):
    return {
        "unique_level_code_per_institution": (
            f"Level code '{code}' already exists for this institution."
        ),
        "unique_level_sequence_per_institution": (f"La secuencia {sequence} ya la usa otro nivel."),
    }


def _require_positive_sequence(sequence, label):
    if sequence is not None and sequence < 1:
        raise DomainError(f"La secuencia de {label} debe ser un entero positivo.")


# Estructura nacional: los cuatro niveles del sistema educativo guatemalteco.
#
# No son una decision institucional, son el marco contra el que todo
# establecimiento reporta. Se pre-crean (migracion academics 0006 para las
# instituciones existentes, ``ensure_national_levels`` para las nuevas) y el que
# no se imparte se desactiva.
NATIONAL_LEVELS = [
    ("PRE", "Preprimaria", 1),
    ("PRI", "Primaria", 2),
    ("BAS", "Basico", 3),
    ("DIV", "Diversificado", 4),
]


def ensure_national_levels(*, institution, actor=None):
    """
    Create the national levels this institution is missing. Idempotent.

    Matched by code, never by name: a level renamed to "Ciclo Basico" is still
    "BAS", and recreating it would leave two.
    """
    created = []
    for code, name, preferred in NATIONAL_LEVELS:
        levels = Level.objects.filter(institution=institution)
        if levels.filter(code=code).exists():
            continue
        taken = set(levels.values_list("sequence", flat=True))
        sequence = preferred if preferred not in taken else max(taken) + 1
        level = Level.objects.create(
            institution=institution, name=name, code=code, sequence=sequence
        )
        _audit(actor, "academics.level.created", level, code=code, sequence=sequence, national=True)
        created.append(level)
    return created


# Serie del codigo de nivel: "NIV-01".
LEVEL_CODE_PREFIX = "NIV"
LEVEL_CODE_WIDTH = 2
LEVEL_CODE_CONSTRAINT = "unique_level_code_per_institution"


def next_level_code(*, institution):
    """Siguiente codigo libre de nivel para la institucion."""
    return next_sequential_code(
        queryset=Level.objects.filter(institution=institution),
        field="code",
        prefix=LEVEL_CODE_PREFIX,
        width=LEVEL_CODE_WIDTH,
    )


def _institution_levels(institution):
    """Todos los niveles, activos e inactivos: la secuencia es unica sobre todos."""
    return Level.objects.filter(institution=institution)


@transaction.atomic
def create_level(*, institution, name, code=None, sequence=None, insert_after=APPEND, actor=None):
    """
    Register an educational level.

    Rules:
    - Code is optional; without one the next of the institution series is used.
    - Position: ``insert_after`` is the level this one must follow, ``None`` puts
      it first, and omitting it appends at the end. The siblings are renumbered
      so the pedagogical order stays contiguous.
    - ``sequence`` is still accepted as an explicit number, and wins over the
      position, because the API contract already had it.
    """
    name = _clean_name(name)
    supplied = (code or "").strip()
    siblings = _institution_levels(institution)

    _require_positive_sequence(sequence, "nivel")
    # Un numero explicito manda sobre la posicion: es el contrato anterior de la
    # API y renumerar despues lo pisaria sin avisar.
    explicit_sequence = sequence is not None
    if not explicit_sequence:
        sequence = _next_sequence(siblings)

    def build(value):
        return Level.objects.create(
            institution=institution, name=name, code=value, sequence=sequence
        )

    if supplied:
        code = _clean_code(supplied)
        with unique_violation_as(_level_conflicts(code, sequence)):
            level = build(code)
    else:
        level = create_with_generated_code(
            build=build,
            generate=lambda: next_level_code(institution=institution),
            constraint=LEVEL_CODE_CONSTRAINT,
        )

    if not explicit_sequence:
        _place_in_order(
            queryset=_institution_levels(institution),
            instance=level,
            insert_after=insert_after,
        )

    _audit(
        actor,
        "academics.level.created",
        level,
        code=level.code,
        sequence=level.sequence,
        generated=not supplied,
    )
    return level


@transaction.atomic
def update_level(*, level, name=None, sequence=None, insert_after=APPEND, actor=None):
    """
    Rename a level or move it in the pedagogical order. The code is immutable.

    ``insert_after`` moves it relative to a sibling and renumbers the rest;
    ``sequence`` still sets the raw number for the callers that send one.
    """
    if name is not None:
        name = _clean_name(name)
    _require_positive_sequence(sequence, "nivel")

    with unique_violation_as(_level_conflicts(level.code, sequence)):
        _changed(level, actor, "academics.level.updated", name=name, sequence=sequence)

    if sequence is None:
        _place_in_order(
            queryset=_institution_levels(level.institution),
            instance=level,
            insert_after=insert_after,
        )
    return level


@transaction.atomic
def deactivate_level(*, level, actor=None):
    """Deactivate a level and its grades, unless a non-closed cycle offers them."""
    if not level.is_active:
        return level

    if _has_open_cycle_usage(GradeOffering.objects.filter(grade__level=level)):
        raise DomainError(
            f"El nivel '{level.name}' tiene grados ofertados en un ciclo activo y no puede "
            f"desactivarse."
        )

    level.is_active = False
    level.save(update_fields=["is_active", "updated_at"])
    Grade.objects.filter(level=level, is_active=True).update(is_active=False)

    _audit(actor, "academics.level.deactivated", level, code=level.code)
    return level


# --------------------------------------------------------------------------- #
# grades ("grados")
# --------------------------------------------------------------------------- #


def _grade_conflicts(code, sequence):
    return {
        "unique_grade_code_per_institution": (
            f"Grade code '{code}' already exists for this institution."
        ),
        "unique_grade_sequence_per_level": (
            f"La secuencia {sequence} ya se usa dentro de este nivel."
        ),
    }


GRADE_CODE_CONSTRAINT = "unique_grade_code_per_institution"


def next_grade_code(*, level):
    """
    Siguiente codigo libre de grado, colgado del codigo de su nivel: BAS1, BAS2.

    Se deriva del nivel y no de una serie propia porque el codigo de un grado se
    lee para saber DE QUE nivel es; "GRA-07" no dice nada. Dos niveles no pueden
    compartir codigo, asi que la serie derivada tampoco choca entre niveles.
    """
    return next_suffixed_code(
        queryset=Grade.objects.filter(institution=level.institution),
        field="code",
        prefix=level.code,
    )


def _level_grades(level):
    """Todos los grados del nivel: la secuencia es unica sobre activos e inactivos."""
    return Grade.objects.filter(level=level)


@transaction.atomic
def create_grade(*, level, name, code=None, sequence=None, insert_after=APPEND, actor=None):
    """
    Register a grade inside a level (RF-EST-001).

    Rules:
    - Level must be active.
    - Code is optional; without one it is derived from the level code ("BAS1").
      Supplied or derived, it is unique institution-wide, so "G1" never means two
      different grades.
    - Position: ``insert_after`` places it after a sibling, ``None`` first, and
      omitting it appends. ``sequence`` still accepts a raw number and wins.

    Uniqueness is a database constraint in both cases. The institution-wide one
    is possible because ``Grade`` carries a derived ``institution`` column; see
    the model docstring and migration 0004.
    """
    _require_active(level, "el nivel")
    name = _clean_name(name)
    supplied = (code or "").strip()
    siblings = _level_grades(level)

    _require_positive_sequence(sequence, "grado")
    explicit_sequence = sequence is not None
    if not explicit_sequence:
        sequence = _next_sequence(siblings)

    def build(value):
        return Grade.objects.create(level=level, name=name, code=value, sequence=sequence)

    if supplied:
        code = _clean_code(supplied)
        with unique_violation_as(_grade_conflicts(code, sequence)):
            grade = build(code)
    else:
        grade = create_with_generated_code(
            build=build,
            generate=lambda: next_grade_code(level=level),
            constraint=GRADE_CODE_CONSTRAINT,
        )

    if not explicit_sequence:
        _place_in_order(queryset=_level_grades(level), instance=grade, insert_after=insert_after)

    _audit(
        actor,
        "academics.grade.created",
        grade,
        level_id=level.pk,
        code=grade.code,
        sequence=grade.sequence,
        generated=not supplied,
    )
    return grade


@transaction.atomic
def update_grade(*, grade, name=None, sequence=None, insert_after=APPEND, actor=None):
    """Rename a grade or reorder it inside its level. The code is immutable."""
    if name is not None:
        name = _clean_name(name)
    _require_positive_sequence(sequence, "grado")

    with unique_violation_as(_grade_conflicts(grade.code, sequence)):
        _changed(grade, actor, "academics.grade.updated", name=name, sequence=sequence)

    if sequence is None:
        _place_in_order(
            queryset=_level_grades(grade.level), instance=grade, insert_after=insert_after
        )
    return grade


def deactivate_grade(*, grade, actor=None):
    """Deactivate a grade unless a non-closed cycle still offers it."""
    if not grade.is_active:
        return grade

    if _has_open_cycle_usage(GradeOffering.objects.filter(grade=grade)):
        raise DomainError(
            f"El grado '{grade.name}' esta ofertado en un ciclo activo y no puede desactivarse."
        )

    grade.is_active = False
    grade.save(update_fields=["is_active", "updated_at"])
    _audit(actor, "academics.grade.deactivated", grade, code=grade.code)
    return grade


# --------------------------------------------------------------------------- #
# subjects ("cursos") and their link to levels
# --------------------------------------------------------------------------- #


def create_subject(*, institution, name, code, actor=None):
    """Register a subject. Code unique per institution."""
    name = _clean_name(name)
    code = _clean_code(code)

    conflicts = {
        "unique_subject_code_per_institution": (
            f"Subject code '{code}' already exists for this institution."
        )
    }
    with unique_violation_as(conflicts):
        subject = Subject.objects.create(institution=institution, name=name, code=code)

    _audit(actor, "academics.subject.created", subject, code=code)
    return subject


def update_subject(*, subject, name=None, actor=None):
    """Rename a subject. The code is immutable."""
    if name is None:
        return subject
    return _changed(subject, actor, "academics.subject.updated", name=_clean_name(name))


def deactivate_subject(*, subject, actor=None):
    """Deactivate a subject; existing level links are kept for history."""
    if not subject.is_active:
        return subject

    subject.is_active = False
    subject.save(update_fields=["is_active", "updated_at"])
    _audit(actor, "academics.subject.deactivated", subject, code=subject.code)
    return subject


def _validate_weekly_hours(weekly_hours):
    if weekly_hours is not None and weekly_hours < 0:
        raise DomainError("Las horas semanales no pueden ser negativas.")


def link_subject_to_level(*, level, subject, is_required=True, weekly_hours=0, actor=None):
    """
    Declare that a subject is taught at a level.

    Rules:
    - Level and subject must belong to the same institution.
    - Both must be active.
    - Weekly hours cannot be negative; zero means "not specified yet".
    - The pair can only be linked once.
    """
    if level.institution_id != subject.institution_id:
        raise DomainError("El nivel y el curso deben pertenecer a la misma institucion.")

    _require_active(level, "el nivel")
    _require_active(subject, "el curso")
    _validate_weekly_hours(weekly_hours)

    conflicts = {
        "unique_subject_per_level": (
            f"Subject '{subject.name}' is already linked to level '{level.name}'."
        )
    }
    with unique_violation_as(conflicts):
        link = LevelSubject.objects.create(
            level=level,
            subject=subject,
            is_required=is_required,
            weekly_hours=weekly_hours or 0,
        )

    _audit(
        actor,
        "academics.level_subject.linked",
        link,
        level_id=level.pk,
        subject_id=subject.pk,
    )
    return link


def get_level_subject(level, subject):
    """The link between a level and a subject, or a DomainError if there is none."""
    try:
        return LevelSubject.objects.select_related("level", "subject").get(
            level=level, subject=subject
        )
    except LevelSubject.DoesNotExist as exc:
        raise DomainError(
            f"El curso '{subject.name}' no esta vinculado al nivel '{level.name}'."
        ) from exc


def update_level_subject(*, level, subject, is_required=None, weekly_hours=None, actor=None):
    """Update the curricular metadata of an existing level/subject link."""
    _validate_weekly_hours(weekly_hours)
    link = get_level_subject(level, subject)

    # ``is_required=False`` is a real value, so it cannot ride on the None convention.
    fields = {"weekly_hours": weekly_hours}
    if is_required is not None:
        link.is_required = is_required
        fields["is_required"] = is_required

    return _changed(link, actor, "academics.level_subject.updated", **fields)


def unlink_subject_from_level(*, level, subject, actor=None):
    """Remove a subject from a level. The link carries no history of its own."""
    link = get_level_subject(level, subject)
    _audit(
        actor,
        "academics.level_subject.unlinked",
        link,
        level_id=level.pk,
        subject_id=subject.pk,
    )
    link.delete()


# --------------------------------------------------------------------------- #
# sections ("secciones")
# --------------------------------------------------------------------------- #


def _resolve_or_create_grade_offering(*, academic_cycle, grade, shift, actor=None):
    """
    Get the (cycle, grade, shift) offering a section attaches to, creating it
    if missing.

    ``GradeOffering`` has no requirement or endpoint of its own — RF-EST-003
    and RF-EST-004 are unrelated ("Subareas del ciclo" and an unimplemented
    display label) — so a section is otherwise unreachable for any cycle that
    was not built by ``clone_academic_cycle``, which already creates offerings
    the same way, by hand. Treating it as an implementation detail here keeps
    RF-EST-007 usable end-to-end without exposing a new public resource.
    """
    if grade.institution_id != academic_cycle.institution_id:
        raise DomainError("El grado debe pertenecer a la institucion del ciclo escolar.")
    if shift.institution != academic_cycle.institution:
        raise DomainError("La jornada debe pertenecer a la institucion del ciclo escolar.")
    _require_active(grade, "el grado")
    _require_active(shift, "la jornada")

    offering, created = GradeOffering.objects.get_or_create(
        academic_cycle=academic_cycle, grade=grade, shift=shift
    )
    if created:
        _audit(
            actor,
            "academics.grade_offering.created",
            offering,
            academic_cycle_id=academic_cycle.pk,
            grade_id=grade.pk,
            shift_id=shift.pk,
        )
    return offering


def _section_conflicts(name):
    return {
        "unique_section_name_per_offering": (
            f"Section '{name}' already exists for this grade offering."
        ),
    }


def _validate_capacity(capacity):
    if capacity is not None and capacity < 0:
        raise DomainError("El cupo de la seccion no puede ser negativo.")


@transaction.atomic
def create_section(*, academic_cycle, grade, shift, name, capacity=0, actor=None):
    """
    Register a section inside a grade offering (RF-EST-007).

    Rules:
    - Rejected once the academic cycle is closed (cycle_policies), the same
      shared guard every other cycle-scoped write already consults.
    - Rejected unless the cycle is still in planning (RF-EST-011): the
      structure itself only changes before the cycle activates.
    - The offering is resolved or created as a side effect; see
      ``_resolve_or_create_grade_offering``.
    - Name unique within the offering; capacity 0 means uncapped.
    """
    require_cycle_academic_writes(cycle=academic_cycle, operation="section.create")
    require_cycle_planning_writes(cycle=academic_cycle, operation="section.create")
    name = _clean_name(name)
    _validate_capacity(capacity)

    offering = _resolve_or_create_grade_offering(
        academic_cycle=academic_cycle, grade=grade, shift=shift, actor=actor
    )

    with unique_violation_as(_section_conflicts(name)):
        section = Section.objects.create(offering=offering, name=name, capacity=capacity or 0)

    _audit(
        actor,
        "academics.section.created",
        section,
        offering_id=offering.pk,
        academic_cycle_id=academic_cycle.pk,
        grade_id=grade.pk,
        shift_id=shift.pk,
        capacity=section.capacity,
    )
    return section


def update_section(*, section, name=None, capacity=None, actor=None):
    """Rename a section or change its declared capacity. Planning-only (RF-EST-011)."""
    require_cycle_academic_writes(cycle=section.academic_cycle, operation="section.update")
    require_cycle_planning_writes(cycle=section.academic_cycle, operation="section.update")
    if name is not None:
        name = _clean_name(name)
    _validate_capacity(capacity)

    with unique_violation_as(_section_conflicts(name or section.name)):
        return _changed(section, actor, "academics.section.updated", name=name, capacity=capacity)


@transaction.atomic
def deactivate_section(*, section, actor=None):
    """
    Deactivate a section instead of deleting it (planning-only, RF-EST-011),
    unless it still has active enrolments.
    """
    if not section.is_active:
        return section

    require_cycle_academic_writes(cycle=section.academic_cycle, operation="section.deactivate")
    require_cycle_planning_writes(cycle=section.academic_cycle, operation="section.deactivate")
    if section.enrolments.filter(status="active").exists():
        raise DomainError(
            f"La seccion '{section.name}' tiene matriculas activas y no puede desactivarse."
        )

    section.is_active = False
    section.save(update_fields=["is_active", "updated_at"])
    _audit(actor, "academics.section.deactivated", section, offering_id=section.offering_id)
    return section


# --------------------------------------------------------------------------- #
# curriculum plans ("plan de estudios")
# --------------------------------------------------------------------------- #


def _curriculum_plan_conflicts(subject_name):
    return {
        "unique_curriculum_plan_per_cycle_grade_subject": (
            f"Subject '{subject_name}' is already part of the curriculum plan for this "
            "grade and cycle."
        ),
    }


@transaction.atomic
def create_curriculum_plan(*, academic_cycle, grade, subject, is_required=True, actor=None):
    """
    Assign a subject to a grade's study plan for a cycle (RF-EST-005).

    Rules:
    - Rejected once the academic cycle is closed (cycle_policies), and unless
      the cycle is still in planning (RF-EST-011) — the study plan is part of
      the structure, same as sections.
    - Grade and subject must belong to the cycle's institution and be active.
    - One entry per (cycle, grade, subject). Unlike a section, a plan entry
      has no shift/capacity, so there is no implicit resource to resolve.
    """
    require_cycle_academic_writes(cycle=academic_cycle, operation="curriculum_plan.create")
    require_cycle_planning_writes(cycle=academic_cycle, operation="curriculum_plan.create")

    if grade.institution_id != academic_cycle.institution_id:
        raise DomainError("El grado debe pertenecer a la institucion del ciclo escolar.")
    if subject.institution_id != academic_cycle.institution_id:
        raise DomainError("El curso debe pertenecer a la institucion del ciclo escolar.")
    _require_active(grade, "el grado")
    _require_active(subject, "el curso")

    with unique_violation_as(_curriculum_plan_conflicts(subject.name)):
        plan = CurriculumPlan.objects.create(
            academic_cycle=academic_cycle,
            grade=grade,
            subject=subject,
            is_required=is_required,
        )

    _audit(
        actor,
        "academics.curriculum_plan.created",
        plan,
        academic_cycle_id=academic_cycle.pk,
        grade_id=grade.pk,
        subject_id=subject.pk,
        is_required=plan.is_required,
    )
    return plan


def update_curriculum_plan(*, plan, is_required=None, actor=None):
    """Change whether a subject is required in the plan. Planning-only (RF-EST-011)."""
    require_cycle_academic_writes(cycle=plan.academic_cycle, operation="curriculum_plan.update")
    require_cycle_planning_writes(cycle=plan.academic_cycle, operation="curriculum_plan.update")

    return _changed(plan, actor, "academics.curriculum_plan.updated", is_required=is_required)


@transaction.atomic
def deactivate_curriculum_plan(*, plan, actor=None):
    """Deactivate a curriculum plan entry instead of deleting it. Planning-only (RF-EST-011)."""
    if not plan.is_active:
        return plan

    require_cycle_academic_writes(cycle=plan.academic_cycle, operation="curriculum_plan.deactivate")
    require_cycle_planning_writes(cycle=plan.academic_cycle, operation="curriculum_plan.deactivate")

    plan.is_active = False
    plan.save(update_fields=["is_active", "updated_at"])
    _audit(
        actor,
        "academics.curriculum_plan.deactivated",
        plan,
        academic_cycle_id=plan.academic_cycle_id,
    )
    return plan


# --------------------------------------------------------------------------- #
# teaching assignments
# --------------------------------------------------------------------------- #


def _teaching_assignment_conflicts():
    return {
        "teaching_assignment_no_overlapping_period": (
            "Another teacher is already assigned to this section and subject for that period."
        ),
    }


def _teacher_profile_for(person):
    try:
        teacher = person.teacher_profile
    except Teacher.DoesNotExist as exc:
        raise DomainError("El docente debe tener un perfil de docente activo.") from exc
    if not teacher.is_active:
        raise DomainError("El docente debe tener un perfil de docente activo.")
    return teacher


def _validate_teaching_assignment(*, academic_cycle, section, subject, teacher, starts_on, ends_on):
    if section.offering.academic_cycle_id != academic_cycle.id:
        raise DomainError("La seccion debe pertenecer al ciclo escolar.")
    if subject.institution_id != academic_cycle.institution_id:
        raise DomainError("El curso debe pertenecer a la institucion del ciclo escolar.")
    _teacher_profile_for(teacher)

    if starts_on < academic_cycle.starts_on or starts_on > academic_cycle.ends_on:
        raise DomainError("La fecha de inicio de la asignacion debe caer dentro del ciclo escolar.")
    if ends_on is not None:
        if ends_on < academic_cycle.starts_on or ends_on > academic_cycle.ends_on:
            raise DomainError(
                "La fecha de fin de la asignacion debe caer dentro del ciclo escolar."
            )
        if ends_on < starts_on:
            raise DomainError(
                "La fecha de fin de la asignacion no puede ser anterior a su fecha de inicio."
            )


@transaction.atomic
def create_teaching_assignment(
    *, academic_cycle, section, subject, teacher, starts_on=None, actor=None
):
    """Create the single current assignment for a cycle, section, and subject."""
    require_cycle_academic_writes(
        cycle=academic_cycle,
        operation="teaching_assignment.create",
    )
    starts_on = starts_on or academic_cycle.starts_on
    _validate_teaching_assignment(
        academic_cycle=academic_cycle,
        section=section,
        subject=subject,
        teacher=teacher,
        starts_on=starts_on,
        ends_on=None,
    )

    with unique_violation_as(_teaching_assignment_conflicts()):
        assignment = TeachingAssignment.objects.create(
            academic_cycle=academic_cycle,
            section=section,
            subject=subject,
            teacher=teacher,
            starts_on=starts_on,
        )

    _audit(
        actor,
        "academics.teaching_assignment.created",
        assignment,
        academic_cycle_id=academic_cycle.pk,
        section_id=section.pk,
        subject_id=subject.pk,
        teacher_id=teacher.pk,
        starts_on=starts_on.isoformat(),
    )
    return assignment


@transaction.atomic
def reassign_teaching_assignment(*, assignment, teacher, ends_on, actor=None):
    """Close a current assignment and open its successor on the following day."""
    assignment = (
        TeachingAssignment.objects.select_for_update()
        .select_related("academic_cycle", "section", "subject", "teacher")
        .get(pk=assignment.pk)
    )
    academic_cycle = assignment.academic_cycle

    require_cycle_academic_writes(
        cycle=academic_cycle,
        operation="teaching_assignment.reassign",
    )

    if assignment.ends_on is not None:
        raise DomainError("Solo se puede reasignar la asignacion docente vigente.")
    if assignment.teacher_id == teacher.id:
        raise DomainError("La reasignacion requiere un docente distinto.")
    if ends_on < academic_cycle.starts_on or ends_on > academic_cycle.ends_on:
        raise DomainError("La fecha de fin de la asignacion debe caer dentro del ciclo escolar.")
    if ends_on < assignment.starts_on:
        raise DomainError(
            "La fecha de fin de la reasignacion no puede ser anterior al inicio de la "
            "asignacion vigente."
        )

    new_starts_on = ends_on + timedelta(days=1)
    if new_starts_on > academic_cycle.ends_on:
        raise DomainError(
            "La fecha de fin de la reasignacion debe dejar al menos un dia al sucesor."
        )
    _validate_teaching_assignment(
        academic_cycle=academic_cycle,
        section=assignment.section,
        subject=assignment.subject,
        teacher=teacher,
        starts_on=new_starts_on,
        ends_on=None,
    )

    assignment.ends_on = ends_on
    assignment.save(update_fields=["ends_on", "updated_at"])
    with unique_violation_as(_teaching_assignment_conflicts()):
        successor = TeachingAssignment.objects.create(
            academic_cycle=academic_cycle,
            section=assignment.section,
            subject=assignment.subject,
            teacher=teacher,
            starts_on=new_starts_on,
        )

    _audit(
        actor,
        "academics.teaching_assignment.reassigned",
        successor,
        previous_assignment_id=assignment.pk,
        previous_teacher_id=assignment.teacher_id,
        teacher_id=teacher.pk,
        ends_on=ends_on.isoformat(),
        starts_on=new_starts_on.isoformat(),
    )
    return successor


# --------------------------------------------------------------------------- #
# class sessions ("sesiones de clase") -- RF-HOR-003
# --------------------------------------------------------------------------- #


def _class_session_conflicts():
    return {
        "unique_class_session_registration": (
            "Esta sesion ya esta registrada para esa seccion, subarea, dia y bloque."
        ),
    }


def create_class_session(
    *, academic_cycle, section, subject, schedule_block, day_of_week, classroom=None, actor=None
):
    """
    Schedule a class session (RF-HOR-003): a subject taught to a section on a
    day of the week, in a block of the schedule grid.

    Rules:
    - Section must belong to the academic cycle.
    - Subject must belong to the cycle's institution.
    - The block must belong to the same shift as the section (a session
      cannot borrow a block from another jornada).
    - Classroom is optional (not every session needs one, e.g. outdoor PE);
      when given, it must belong to the section's campus.
    - The exact same registration twice is rejected (unique constraint).
    - A section cannot attend two different sessions at once: an active
      session with a different subject already occupying the same
      (section, day_of_week, schedule_block) is a conflict (RF-HOR-005).
    - A classroom cannot host two sessions at once either: an active
      session -- any section, any subject -- already occupying the same
      (classroom, day_of_week, schedule_block) is a conflict, checked only
      when a classroom is given.
    """
    require_cycle_academic_writes(cycle=academic_cycle, operation="class_session.create")

    if section.offering.academic_cycle_id != academic_cycle.id:
        raise DomainError("La seccion debe pertenecer al ciclo escolar.")
    if subject.institution_id != academic_cycle.institution_id:
        raise DomainError("El curso debe pertenecer a la institucion del ciclo escolar.")
    if schedule_block.shift_id != section.offering.shift_id:
        raise DomainError("El bloque de horario debe pertenecer a la misma jornada que la seccion.")
    if classroom is not None and classroom.campus_id != section.offering.shift.campus_id:
        raise DomainError("El aula debe pertenecer a la misma sede que la seccion.")
    if (
        ClassSession.objects.filter(
            section=section,
            day_of_week=day_of_week,
            schedule_block=schedule_block,
            is_active=True,
        )
        .exclude(subject=subject)
        .exists()
    ):
        raise DomainError(
            "La seccion ya tiene otra sesion agendada en ese dia y bloque: cruce de horario."
        )
    if (
        classroom is not None
        and ClassSession.objects.filter(
            classroom=classroom,
            day_of_week=day_of_week,
            schedule_block=schedule_block,
            is_active=True,
        ).exists()
    ):
        raise DomainError(
            "El aula ya tiene otra sesion agendada en ese dia y bloque: cruce de horario."
        )

    with unique_violation_as(_class_session_conflicts()):
        session = ClassSession.objects.create(
            academic_cycle=academic_cycle,
            section=section,
            subject=subject,
            schedule_block=schedule_block,
            classroom=classroom,
            day_of_week=day_of_week,
        )

    _audit(
        actor,
        "academics.class_session.created",
        session,
        academic_cycle_id=academic_cycle.pk,
        section_id=section.pk,
        subject_id=subject.pk,
        schedule_block_id=schedule_block.pk,
        classroom_id=classroom.pk if classroom else None,
        day_of_week=day_of_week,
    )
    return session


def deactivate_class_session(*, session, actor=None):
    if not session.is_active:
        return session
    session.is_active = False
    session.save(update_fields=["is_active", "updated_at"])
    _audit(
        actor,
        "academics.class_session.deactivated",
        session,
        section_id=session.section_id,
        subject_id=session.subject_id,
    )
    return session


# --------------------------------------------------------------------------- #
# class schedule publication -- RF-HOR-009
# --------------------------------------------------------------------------- #


def publish_class_schedule(*, academic_cycle, actor=None):
    """
    Publish the cycle's class schedule (RF-HOR-009).

    Idempotent: publishing an already-published schedule just refreshes
    ``published_at``. Who gets to see it once published (docentes,
    estudiantes, encargados) is a query-time concern (RF-HOR-010, #203).
    """
    require_cycle_academic_writes(cycle=academic_cycle, operation="class_schedule.publish")
    publication, _ = ClassSchedulePublication.objects.get_or_create(academic_cycle=academic_cycle)
    publication.published_at = timezone.now()
    publication.save(update_fields=["published_at", "updated_at"])
    _audit(
        actor,
        "academics.class_schedule.published",
        publication,
        academic_cycle_id=academic_cycle.pk,
    )
    return publication


def unpublish_class_schedule(*, academic_cycle, actor=None):
    """Revert the cycle's schedule to draft. A no-op if never published."""
    require_cycle_academic_writes(cycle=academic_cycle, operation="class_schedule.unpublish")
    publication, _ = ClassSchedulePublication.objects.get_or_create(academic_cycle=academic_cycle)
    if publication.published_at is None:
        return publication
    publication.published_at = None
    publication.save(update_fields=["published_at", "updated_at"])
    _audit(
        actor,
        "academics.class_schedule.unpublished",
        publication,
        academic_cycle_id=academic_cycle.pk,
    )
    return publication
