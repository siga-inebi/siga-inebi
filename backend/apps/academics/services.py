"""
Domain services for the academic catalogue.

The catalogue is the structure enrolments are assigned to:

    Institution
      +-- Campus ("sede")
      |     +-- Shift ("jornada")
      +-- Level ("nivel")
      |     +-- Grade ("grado")
      +-- Subject ("curso")
      +-- AcademicCycle ("ciclo escolar")
            +-- GradeOffering ("oferta")   grade x shift, rebuilt per cycle
            |     +-- Section ("seccion")
            |           +-- TeachingAssignment ("asignacion docente")
            +-- CurriculumPlan ("plan de estudios")   grade x subject

The permanent catalogue (levels, grades, subjects) outlives every cycle. What
hangs from a cycle is rebuilt for each one, so a closed cycle keeps the exact
structure its enrolments were made against (RF-EST-013).

Every invariant lives here, never in views or serializers (AGENTS.md #8).

Uniqueness is delegated to the database constraints and translated back into a
``DomainError`` by ``unique_violation_as``. Reading first and writing afterwards
would leave a window for two concurrent requests to both pass the check.
"""

from django.db import transaction
from django.utils import timezone

from apps.academics.models import (
    AcademicCycle,
    Campus,
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
from apps.common.db import unique_violation_as
from apps.common.models import DomainError

# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _clean_code(value, *, field="code"):
    code = (value or "").strip().upper()
    if not code:
        raise DomainError(f"A non-empty {field} is required.")
    return code


def _clean_name(value, *, field="name"):
    name = (value or "").strip()
    if not name:
        raise DomainError(f"A non-empty {field} is required.")
    return name


def _require_active(instance, label):
    if not instance.is_active:
        raise DomainError(f"{label} '{instance}' is inactive and cannot be used.")


def _has_open_cycle_usage(offering_queryset):
    """True when any of those offerings belongs to a cycle that is not closed."""
    return offering_queryset.exclude(
        academic_cycle__status=AcademicCycle.CycleStatus.CLOSED
    ).exists()


def _audit(actor, action, instance, **context):
    record_event(
        actor=actor,
        action=action,
        resource=type(instance).__name__,
        resource_identifier=str(instance.pk),
        context=context,
    )


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


@transaction.atomic
def create_campus(*, institution, name, code, address="", is_main=False, actor=None):
    """
    Register a campus.

    Rules:
    - Code is normalised to upper case and unique per institution, including
      inactive campuses so history stays readable (ADR-0006).
    - At most one main campus per institution; promoting a new one demotes the
      previous main campus.
    """
    name = _clean_name(name)
    code = _clean_code(code)

    if is_main:
        Campus.objects.filter(institution=institution, is_main=True).update(is_main=False)

    with unique_violation_as(_campus_conflicts(code)):
        campus = Campus.objects.create(
            institution=institution,
            name=name,
            code=code,
            address=(address or "").strip(),
            is_main=is_main,
        )

    _audit(actor, "academics.campus.created", campus, code=code, is_main=is_main)
    return campus


@transaction.atomic
def update_campus(*, campus, name=None, address=None, is_main=None, actor=None):
    """Update the descriptive attributes of a campus. The code is immutable."""
    if name is not None:
        name = _clean_name(name)
    if address is not None:
        address = address.strip()

    if is_main is not None and is_main != campus.is_main and is_main:
        _require_active(campus, "Campus")
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
            f"Campus '{campus.name}' is used by an active cycle and cannot be deactivated."
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
    _require_active(campus, "Campus")
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
            f"Shift '{shift.name}' is used by an active cycle and cannot be deactivated."
        )

    shift.is_active = False
    shift.save(update_fields=["is_active", "updated_at"])
    _audit(actor, "academics.shift.deactivated", shift, code=shift.code)
    return shift


# --------------------------------------------------------------------------- #
# levels ("niveles")
# --------------------------------------------------------------------------- #


def _level_conflicts(code, sequence):
    return {
        "unique_level_code_per_institution": (
            f"Level code '{code}' already exists for this institution."
        ),
        "unique_level_sequence_per_institution": (
            f"Level sequence {sequence} is already used by another level."
        ),
    }


def _require_positive_sequence(sequence, label):
    if sequence is not None and sequence < 1:
        raise DomainError(f"{label} sequence must be a positive integer.")


def create_level(*, institution, name, code, sequence, actor=None):
    """
    Register an educational level.

    Rules:
    - Code unique per institution.
    - Sequence is a positive integer, unique per institution, because it defines
      the pedagogical order used everywhere else.
    """
    name = _clean_name(name)
    code = _clean_code(code)
    if sequence is None:
        raise DomainError("Level sequence must be a positive integer.")
    _require_positive_sequence(sequence, "Level")

    with unique_violation_as(_level_conflicts(code, sequence)):
        level = Level.objects.create(
            institution=institution, name=name, code=code, sequence=sequence
        )

    _audit(actor, "academics.level.created", level, code=code, sequence=sequence)
    return level


def update_level(*, level, name=None, sequence=None, actor=None):
    """Rename a level or move it in the pedagogical order. The code is immutable."""
    if name is not None:
        name = _clean_name(name)
    _require_positive_sequence(sequence, "Level")

    with unique_violation_as(_level_conflicts(level.code, sequence)):
        return _changed(level, actor, "academics.level.updated", name=name, sequence=sequence)


@transaction.atomic
def deactivate_level(*, level, actor=None):
    """Deactivate a level and its grades, unless a non-closed cycle offers them."""
    if not level.is_active:
        return level

    if _has_open_cycle_usage(GradeOffering.objects.filter(grade__level=level)):
        raise DomainError(
            f"Level '{level.name}' has grades offered in an active cycle and cannot be deactivated."
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
            f"Grade sequence {sequence} is already used inside this level."
        ),
    }


def create_grade(*, level, name, code, sequence, actor=None):
    """
    Register a grade inside a level (RF-EST-001).

    Rules:
    - Level must be active.
    - Code unique institution-wide, so "G1" never means two different grades.
    - Sequence positive and unique inside the level.

    Both rules are database constraints. The institution-wide one is possible
    because ``Grade`` carries a derived ``institution`` column; see the model
    docstring and migration 0004.
    """
    _require_active(level, "Level")
    name = _clean_name(name)
    code = _clean_code(code)
    if sequence is None:
        raise DomainError("Grade sequence must be a positive integer.")
    _require_positive_sequence(sequence, "Grade")

    with unique_violation_as(_grade_conflicts(code, sequence)):
        grade = Grade.objects.create(level=level, name=name, code=code, sequence=sequence)

    _audit(actor, "academics.grade.created", grade, level_id=level.pk, code=code)
    return grade


def update_grade(*, grade, name=None, sequence=None, actor=None):
    """Rename a grade or reorder it inside its level. The code is immutable."""
    if name is not None:
        name = _clean_name(name)
    _require_positive_sequence(sequence, "Grade")

    with unique_violation_as(_grade_conflicts(grade.code, sequence)):
        return _changed(grade, actor, "academics.grade.updated", name=name, sequence=sequence)


def deactivate_grade(*, grade, actor=None):
    """Deactivate a grade unless a non-closed cycle still offers it."""
    if not grade.is_active:
        return grade

    if _has_open_cycle_usage(GradeOffering.objects.filter(grade=grade)):
        raise DomainError(
            f"Grade '{grade.name}' is offered in an active cycle and cannot be deactivated."
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
        raise DomainError("Weekly hours cannot be negative.")


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
        raise DomainError("Level and subject must belong to the same institution.")

    _require_active(level, "Level")
    _require_active(subject, "Subject")
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
            f"Subject '{subject.name}' is not linked to level '{level.name}'."
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
# academic cycles ("ciclos escolares")
# --------------------------------------------------------------------------- #

# Cycles only move forward. Reopening a closed cycle would let its already
# archived structure change underneath the enrolments that reference it.
_CYCLE_ORDER = {
    AcademicCycle.CycleStatus.DRAFT: 0,
    AcademicCycle.CycleStatus.ACTIVE: 1,
    AcademicCycle.CycleStatus.CLOSED: 2,
}


def _cycle_conflicts(name):
    return {
        "unique_cycle_name_per_institution": (
            f"Cycle name '{name}' already exists for this institution."
        )
    }


def _require_open_cycle(cycle, action):
    """Nothing that belongs to a closed cycle can change any more (RF-EST-011)."""
    if cycle.is_closed:
        raise DomainError(f"Cycle '{cycle.name}' is closed; {action} is no longer allowed.")


def _validate_cycle_dates(starts_on, ends_on):
    if starts_on is not None and ends_on is not None and ends_on <= starts_on:
        raise DomainError("Cycle end date must be later than its start date.")


def create_academic_cycle(*, institution, name, starts_on, ends_on, actor=None):
    """
    Open a school cycle (RF-EST-013).

    Rules:
    - Name unique per institution.
    - End date strictly after the start date.
    - Always born in draft: the structure is built first and the cycle is
      activated only once it holds something to enrol into.
    """
    name = _clean_name(name)
    if starts_on is None or ends_on is None:
        raise DomainError("A cycle needs both a start and an end date.")
    _validate_cycle_dates(starts_on, ends_on)

    with unique_violation_as(_cycle_conflicts(name)):
        cycle = AcademicCycle.objects.create(
            institution=institution,
            name=name,
            starts_on=starts_on,
            ends_on=ends_on,
            status=AcademicCycle.CycleStatus.DRAFT,
        )

    _audit(actor, "academics.cycle.created", cycle, name=name)
    return cycle


def update_academic_cycle(*, cycle, name=None, starts_on=None, ends_on=None, actor=None):
    """Rename a cycle or move its dates, while it is not closed."""
    _require_open_cycle(cycle, "editing it")

    if name is not None:
        name = _clean_name(name)
    _validate_cycle_dates(
        starts_on if starts_on is not None else cycle.starts_on,
        ends_on if ends_on is not None else cycle.ends_on,
    )

    with unique_violation_as(_cycle_conflicts(name or cycle.name)):
        return _changed(
            cycle,
            actor,
            "academics.cycle.updated",
            name=name,
            starts_on=starts_on,
            ends_on=ends_on,
        )


def change_cycle_status(*, cycle, status, actor=None):
    """
    Move a cycle forward through draft -> active -> closed (RF-EST-011).

    Rules:
    - Forward only. A closed cycle never reopens and an active one never goes
      back to draft, because enrolments already point at its structure.
    - Activating requires at least one grade offering, so no cycle can be opened
      for enrolment while it is still empty.
    """
    if status not in _CYCLE_ORDER:
        raise DomainError(f"Unknown cycle status '{status}'.")

    if _CYCLE_ORDER[status] <= _CYCLE_ORDER[cycle.status]:
        raise DomainError(
            f"Cycle '{cycle.name}' cannot move from '{cycle.status}' back to '{status}'."
        )

    if (
        status == AcademicCycle.CycleStatus.ACTIVE
        and not GradeOffering.objects.filter(academic_cycle=cycle, is_active=True).exists()
    ):
        raise DomainError(
            f"Cycle '{cycle.name}' has no grade offering yet and cannot be activated."
        )

    cycle.status = status
    cycle.save(update_fields=["status", "updated_at"])
    _audit(actor, "academics.cycle.status_changed", cycle, status=status)
    return cycle


# --------------------------------------------------------------------------- #
# grade offerings ("oferta de grados")
# --------------------------------------------------------------------------- #


def _section_has_enrolments(section_queryset):
    return section_queryset.filter(enrolments__status="active").exists()


@transaction.atomic
def offer_grade(*, cycle, grade, shift, actor=None):
    """
    Declare that a grade is taught in a shift during a cycle (RF-EST-013).

    This is the node enrolments hang from, so it is rebuilt per cycle instead of
    being shared: the same grade may be offered in one cycle and dropped in the
    next without rewriting history.

    Rules:
    - Cycle must not be closed.
    - Grade and shift must be active and belong to the institution of the cycle.
    - The trio cycle/shift/grade is unique.
    """
    _require_open_cycle(cycle, "adding grade offerings")
    _require_active(grade, "Grade")
    _require_active(shift, "Shift")

    if grade.institution_id != cycle.institution_id:
        raise DomainError("Grade and cycle must belong to the same institution.")
    if shift.campus.institution_id != cycle.institution_id:
        raise DomainError("Shift and cycle must belong to the same institution.")

    conflicts = {
        "unique_grade_offering_per_cycle_shift": (
            f"Grade '{grade.name}' is already offered in shift '{shift.name}' for this cycle."
        )
    }
    with unique_violation_as(conflicts):
        offering = GradeOffering.objects.create(academic_cycle=cycle, grade=grade, shift=shift)

    _audit(
        actor, "academics.grade_offering.created", offering, grade_id=grade.pk, shift_id=shift.pk
    )
    return offering


@transaction.atomic
def withdraw_grade_offering(*, offering, actor=None):
    """
    Deactivate an offering and its sections instead of deleting them (RF-EST-012).

    Refused while any of its sections still holds an active enrolment: dropping
    the offering would leave those students pointing at a withdrawn structure.
    """
    if not offering.is_active:
        return offering

    _require_open_cycle(offering.academic_cycle, "withdrawing grade offerings")

    if _section_has_enrolments(Section.objects.filter(offering=offering)):
        raise DomainError(
            f"Offering '{offering}' still has active enrolments and cannot be withdrawn."
        )

    offering.is_active = False
    offering.save(update_fields=["is_active", "updated_at"])
    Section.objects.filter(offering=offering, is_active=True).update(is_active=False)

    _audit(actor, "academics.grade_offering.withdrawn", offering)
    return offering


# --------------------------------------------------------------------------- #
# sections ("secciones")
# --------------------------------------------------------------------------- #


def _validate_capacity(capacity):
    if capacity is not None and capacity < 0:
        raise DomainError("Section capacity cannot be negative.")


def create_section(*, offering, name, capacity=0, actor=None):
    """
    Create a section inside a grade offering (RF-EST-007).

    Rules:
    - Offering active and its cycle not closed.
    - Name unique inside the offering; it is normalised to upper case so "a"
      and "A" are the same section.
    - Capacity cannot be negative. Zero means "no declared cap" (RF-EST-008).
    """
    _require_active(offering, "Grade offering")
    _require_open_cycle(offering.academic_cycle, "adding sections")
    name = _clean_code(name, field="section name")
    _validate_capacity(capacity)

    conflicts = {
        "unique_section_name_per_offering": (
            f"Section '{name}' already exists for offering '{offering}'."
        )
    }
    with unique_violation_as(conflicts):
        section = Section.objects.create(offering=offering, name=name, capacity=capacity or 0)

    _audit(actor, "academics.section.created", section, offering_id=offering.pk, name=name)
    return section


def update_section(*, section, name=None, capacity=None, actor=None):
    """
    Rename a section or change its declared capacity.

    Capacity cannot drop below the students already enrolled: the declared cap
    has to stay a promise the current occupancy can keep (RF-EST-008).
    """
    _require_open_cycle(section.academic_cycle, "editing sections")
    _validate_capacity(capacity)

    if name is not None:
        name = _clean_code(name, field="section name")

    if capacity is not None and capacity != 0:
        occupancy = section.active_enrolment_count
        if capacity < occupancy:
            raise DomainError(
                f"Section '{section.name}' already holds {occupancy} students; "
                f"capacity cannot be set below that."
            )

    conflicts = {
        "unique_section_name_per_offering": (
            f"Section '{name or section.name}' already exists for this offering."
        )
    }
    with unique_violation_as(conflicts):
        return _changed(section, actor, "academics.section.updated", name=name, capacity=capacity)


def deactivate_section(*, section, actor=None):
    """Deactivate a section unless students are still enrolled in it."""
    if not section.is_active:
        return section

    _require_open_cycle(section.academic_cycle, "deactivating sections")

    if section.active_enrolment_count:
        raise DomainError(
            f"Section '{section.name}' still has active enrolments and cannot be deactivated."
        )

    section.is_active = False
    section.save(update_fields=["is_active", "updated_at"])
    _audit(actor, "academics.section.deactivated", section, name=section.name)
    return section


# --------------------------------------------------------------------------- #
# curriculum plan ("plan de estudios del ciclo")
# --------------------------------------------------------------------------- #


def add_curriculum_entry(*, cycle, grade, subject, is_required=True, actor=None):
    """
    Put a subject in the study plan of a grade for one cycle (RF-EST-005).

    This is the per-cycle plan, not the permanent level catalogue: ``LevelSubject``
    says what a level teaches in general, this says what a grade actually teaches
    in this cycle, and the two can diverge without rewriting the catalogue.

    Rules:
    - Cycle not closed.
    - Grade and subject active and from the institution of the cycle.
    - A subject appears once per grade and cycle.
    """
    _require_open_cycle(cycle, "editing the curriculum")
    _require_active(grade, "Grade")
    _require_active(subject, "Subject")

    if grade.institution_id != cycle.institution_id:
        raise DomainError("Grade and cycle must belong to the same institution.")
    if subject.institution_id != cycle.institution_id:
        raise DomainError("Subject and cycle must belong to the same institution.")

    conflicts = {
        "unique_subject_per_grade_and_cycle": (
            f"Subject '{subject.name}' is already in the plan of grade '{grade.name}'."
        )
    }
    with unique_violation_as(conflicts):
        entry = CurriculumPlan.objects.create(
            academic_cycle=cycle, grade=grade, subject=subject, is_required=is_required
        )

    _audit(
        actor,
        "academics.curriculum_plan.added",
        entry,
        cycle_id=cycle.pk,
        grade_id=grade.pk,
        subject_id=subject.pk,
    )
    return entry


def get_curriculum_entry(cycle, grade, subject):
    """The plan entry for a trio, or a DomainError when the subject is not planned."""
    try:
        return CurriculumPlan.objects.select_related("academic_cycle", "grade", "subject").get(
            academic_cycle=cycle, grade=grade, subject=subject
        )
    except CurriculumPlan.DoesNotExist as exc:
        raise DomainError(
            f"Subject '{subject.name}' is not in the plan of grade '{grade.name}' for this cycle."
        ) from exc


def update_curriculum_entry(*, entry, is_required=None, actor=None):
    """Change whether a planned subject is compulsory."""
    _require_open_cycle(entry.academic_cycle, "editing the curriculum")

    if is_required is None:
        return entry

    # ``is_required=False`` is a real value, so it cannot ride on the None convention.
    entry.is_required = is_required
    return _changed(entry, actor, "academics.curriculum_plan.updated", is_required=is_required)


@transaction.atomic
def remove_curriculum_entry(*, entry, actor=None):
    """
    Drop a subject from the plan.

    Refused while a teacher is still assigned to that subject in the cycle:
    removing it would leave the assignment pointing at something the grade no
    longer teaches.
    """
    _require_open_cycle(entry.academic_cycle, "editing the curriculum")

    covered = TeachingAssignment.objects.filter(
        academic_cycle=entry.academic_cycle,
        subject=entry.subject,
        section__offering__grade=entry.grade,
        ends_on__isnull=True,
    ).exists()
    if covered:
        raise DomainError(
            f"Subject '{entry.subject.name}' still has an open teaching assignment "
            f"in grade '{entry.grade.name}' and cannot be removed from the plan."
        )

    _audit(
        actor,
        "academics.curriculum_plan.removed",
        entry,
        cycle_id=entry.academic_cycle_id,
        grade_id=entry.grade_id,
        subject_id=entry.subject_id,
    )
    entry.delete()


# --------------------------------------------------------------------------- #
# teaching assignments ("asignacion de docentes")
# --------------------------------------------------------------------------- #


def assign_teacher(*, section, subject, teacher, starts_on=None, actor=None):
    """
    Put a teacher in front of a subject of a section (RF-EST-009).

    Rules:
    - Cycle not closed and section active.
    - The subject must already be in the curriculum plan of the grade for that
      cycle: a section cannot be taught something its grade does not study.
    - Teacher must be active.
    - Only one open assignment per section and subject. Closed assignments stay
      as history, which is why the constraint is partial on ``ends_on``.
    """
    cycle = section.academic_cycle
    _require_open_cycle(cycle, "assigning teachers")
    _require_active(section, "Section")
    _require_active(teacher, "Teacher")

    # Raises a DomainError naming the missing plan entry when there is none.
    get_curriculum_entry(cycle, section.grade, subject)

    starts_on = starts_on or timezone.localdate()

    conflicts = {
        "unique_open_assignment_per_section_subject": (
            f"Subject '{subject.name}' already has an assigned teacher in section "
            f"'{section.name}'. Close that assignment first."
        ),
        "unique_assignment_per_teacher_and_start": (
            f"'{teacher}' is already assigned to '{subject.name}' in section "
            f"'{section.name}' from that same date."
        ),
    }
    with unique_violation_as(conflicts):
        assignment = TeachingAssignment.objects.create(
            academic_cycle=cycle,
            section=section,
            subject=subject,
            teacher=teacher,
            starts_on=starts_on,
        )

    _audit(
        actor,
        "academics.teaching_assignment.created",
        assignment,
        section_id=section.pk,
        subject_id=subject.pk,
        teacher_id=teacher.pk,
    )
    return assignment


def end_teaching_assignment(*, assignment, ends_on=None, actor=None):
    """
    Close an assignment so the slot can take another teacher.

    The row is kept rather than deleted (ADR-0006): who taught what and until
    when is exactly the history the audit trail is for. Idempotent.
    """
    _require_open_cycle(assignment.academic_cycle, "closing teaching assignments")

    if not assignment.is_open:
        return assignment

    ends_on = ends_on or timezone.localdate()
    if ends_on < assignment.starts_on:
        raise DomainError("An assignment cannot end before it starts.")

    assignment.ends_on = ends_on
    assignment.save(update_fields=["ends_on", "updated_at"])
    _audit(actor, "academics.teaching_assignment.ended", assignment, ends_on=str(ends_on))
    return assignment
