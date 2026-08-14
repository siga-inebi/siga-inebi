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

from apps.academics.cycle_policies import require_cycle_academic_writes
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
from apps.teachers.models import Teacher

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
            "The current active cycle must be closed before activating another cycle."
        ),
    }


def create_academic_cycle(
    *, institution, year, name, starts_on, ends_on, description="", actor=None
):
    """Register a non-overlapping cycle in preparation (RF-CIC-001)."""
    name = _clean_name(name)
    description = (description or "").strip()
    if starts_on > ends_on:
        raise DomainError("Academic cycle end date cannot be before its start date.")
    if starts_on.year != year:
        raise DomainError("Academic cycle year must match its start date year.")

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
    grades_with_plan = set(
        cycle.curriculum_plans.filter(is_active=True).values_list("grade_id", flat=True)
    )
    reported_plan_gaps = set()
    for offering in offerings:
        if not offering.sections.filter(is_active=True).exists():
            gaps.append(
                f"sections for grade '{offering.grade.name}' in shift '{offering.shift.name}'"
            )
        if (
            offering.grade_id not in grades_with_plan
            and offering.grade_id not in reported_plan_gaps
        ):
            gaps.append(f"curriculum plan for grade '{offering.grade.name}'")
            reported_plan_gaps.add(offering.grade_id)
    return gaps


@transaction.atomic
def clone_academic_cycle(
    *,
    source_cycle,
    year,
    name,
    starts_on,
    ends_on,
    description="",
    include_teaching_assignments=False,
    actor=None,
):
    """Create an independent draft cycle from existing academic structure (RF-CIC-007)."""
    source = AcademicCycle.objects.select_for_update().get(pk=source_cycle.pk)
    if source.status != AcademicCycle.CycleStatus.CLOSED:
        raise DomainError("Only a closed academic cycle can be cloned.")
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
        raise DomainError("Only an academic cycle in preparation can be activated.")
    if (
        AcademicCycle.objects.select_for_update()
        .filter(
            institution=locked.institution,
            status=AcademicCycle.CycleStatus.ACTIVE,
        )
        .exclude(pk=locked.pk)
        .exists()
    ):
        raise DomainError(
            "The current active cycle must be closed before activating another cycle."
        )
    opening_gaps = _academic_cycle_opening_gaps(locked)
    if opening_gaps:
        raise DomainError(
            "Academic cycle structure is incomplete: " + "; ".join(opening_gaps) + "."
        )

    locked.status = AcademicCycle.CycleStatus.ACTIVE
    with unique_violation_as(_cycle_conflicts(year=locked.year, name=locked.name)):
        locked.save(update_fields=["status", "updated_at"])
    _audit(actor, "academics.cycle.activated", locked, status=locked.status)
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
        raise DomainError("Teacher must have an active Teacher profile.") from exc
    if not teacher.is_active:
        raise DomainError("Teacher must have an active Teacher profile.")
    return teacher


def _validate_teaching_assignment(*, academic_cycle, section, subject, teacher, starts_on, ends_on):
    if section.offering.academic_cycle_id != academic_cycle.id:
        raise DomainError("Section must belong to the academic cycle.")
    if subject.institution_id != academic_cycle.institution_id:
        raise DomainError("Subject must belong to the academic cycle institution.")
    _teacher_profile_for(teacher)

    if starts_on < academic_cycle.starts_on or starts_on > academic_cycle.ends_on:
        raise DomainError("Assignment start date must be within the academic cycle.")
    if ends_on is not None:
        if ends_on < academic_cycle.starts_on or ends_on > academic_cycle.ends_on:
            raise DomainError("Assignment end date must be within the academic cycle.")
        if ends_on < starts_on:
            raise DomainError("Assignment end date cannot be before its start date.")


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
        raise DomainError("Only the current teaching assignment can be reassigned.")
    if assignment.teacher_id == teacher.id:
        raise DomainError("Reassignment requires a different teacher.")
    if ends_on < academic_cycle.starts_on or ends_on > academic_cycle.ends_on:
        raise DomainError("Assignment end date must be within the academic cycle.")
    if ends_on < assignment.starts_on:
        raise DomainError("Reassignment end date cannot be before the current assignment starts.")

    new_starts_on = ends_on + timedelta(days=1)
    if new_starts_on > academic_cycle.ends_on:
        raise DomainError("Reassignment end date must leave at least one day for the successor.")
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
