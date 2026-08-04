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

from django.db import transaction

from apps.academics.models import (
    AcademicCycle,
    Campus,
    Grade,
    GradeOffering,
    Level,
    LevelSubject,
    Section,
    Shift,
    Subject,
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


def _require_open_cycle(cycle, action):
    if cycle.is_closed:
        raise DomainError(f"Cycle '{cycle.name}' is closed: {action} is not allowed.")


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
# cycle lifecycle
# --------------------------------------------------------------------------- #


def open_cycle(*, cycle, actor=None):
    """
    Transition an AcademicCycle from draft to active.

    Rules (RF-CIC-003):
    - Cycle must be in draft status.
    - No other active cycle may exist for the same institution.
    """
    if cycle.status == AcademicCycle.CycleStatus.ACTIVE:
        raise DomainError(f"Cycle '{cycle.name}' is already active.")

    if cycle.status == AcademicCycle.CycleStatus.CLOSED:
        raise DomainError(
            f"Cycle '{cycle.name}' is closed and cannot be reopened through this operation."
        )

    conflicting = AcademicCycle.objects.filter(
        institution=cycle.institution,
        status=AcademicCycle.CycleStatus.ACTIVE,
    ).exists()
    if conflicting:
        raise DomainError(
            "Institution already has an active cycle. "
            "Close the current active cycle before opening a new one."
        )

    cycle.status = AcademicCycle.CycleStatus.ACTIVE
    cycle.save(update_fields=["status", "updated_at"])
    _audit(actor, "academics.cycle.opened", cycle, name=cycle.name)
    return cycle


def close_cycle(*, cycle, actor=None):
    """
    Transition an AcademicCycle from active to closed.

    Rules (RF-CIC-004):
    - Cycle must be currently active.
    - Once closed, structure and enrolments become immutable.
    """
    if cycle.status != AcademicCycle.CycleStatus.ACTIVE:
        raise DomainError(
            f"Cycle '{cycle.name}' cannot be closed: only active cycles can be closed."
        )

    cycle.status = AcademicCycle.CycleStatus.CLOSED
    cycle.save(update_fields=["status", "updated_at"])
    _audit(actor, "academics.cycle.closed", cycle, name=cycle.name)
    return cycle


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
# grade offerings (grade + shift of a campus, per cycle)
# --------------------------------------------------------------------------- #


def create_grade_offering(*, cycle, shift, grade, actor=None):
    """
    Offer a grade in a shift of a campus, for a cycle.

    Rules:
    - Cycle must not be closed (RF-EST-011); drafts are allowed so the
      catalogue can be assembled before activation.
    - Cycle, shift campus and grade level must belong to the same institution.
    - Campus, shift, level and grade must all be active.
    - The (cycle, shift, grade) triple is unique.
    """
    _require_open_cycle(cycle, "changing the catalogue")

    if shift.campus.institution_id != cycle.institution_id:
        raise DomainError("Shift belongs to a different institution than the cycle.")

    if grade.level.institution_id != cycle.institution_id:
        raise DomainError("Grade belongs to a different institution than the cycle.")

    _require_active(shift.campus, "Campus")
    _require_active(shift, "Shift")
    _require_active(grade.level, "Level")
    _require_active(grade, "Grade")

    conflicts = {
        "unique_grade_offering_per_cycle_shift": (
            f"Grade '{grade.name}' is already offered in shift '{shift.name}' "
            f"of campus '{shift.campus.name}' for cycle '{cycle.name}'."
        )
    }
    with unique_violation_as(conflicts):
        offering = GradeOffering.objects.create(academic_cycle=cycle, shift=shift, grade=grade)

    _audit(
        actor,
        "academics.grade_offering.created",
        offering,
        cycle_id=cycle.pk,
        shift_id=shift.pk,
        grade_id=grade.pk,
    )
    return offering


def remove_grade_offering(*, offering, actor=None):
    """
    Drop a grade offering from the catalogue.

    Rules:
    - Cycle must not be closed.
    - Refused while the offering still has sections; remove those first so no
      enrolment history is silently detached.
    """
    _require_open_cycle(offering.academic_cycle, "changing the catalogue")

    if offering.sections.exists():
        raise DomainError(
            "This offering still has sections. Remove its sections before dropping it."
        )

    _audit(actor, "academics.grade_offering.removed", offering)
    offering.delete()


# --------------------------------------------------------------------------- #
# sections
# --------------------------------------------------------------------------- #


def _section_conflicts(name):
    return {
        "unique_section_name_per_offering": (
            f"Section '{name}' already exists in this grade offering."
        )
    }


def create_section(*, offering, name, capacity=0, actor=None):
    """
    Add a section to a grade offering (RF-EST-007, RF-EST-011).

    Rules:
    - Cycle must not be closed.
    - Name is normalised to upper case and unique inside the offering.
    - Capacity cannot be negative; zero means uncapped.
    """
    _require_open_cycle(offering.academic_cycle, "adding sections")
    name = _clean_code(name, field="name")

    if capacity is None or capacity < 0:
        raise DomainError("Section capacity cannot be negative.")

    with unique_violation_as(_section_conflicts(name)):
        section = Section.objects.create(offering=offering, name=name, capacity=capacity)

    _audit(actor, "academics.section.created", section, offering_id=offering.pk, name=name)
    return section


@transaction.atomic
def update_section(*, section, name=None, capacity=None, actor=None):
    """
    Rename a section or change its declared capacity (RF-EST-008).

    Rules:
    - Cycle must not be closed.
    - Name stays unique inside the offering.
    - Capacity cannot drop below current occupancy, and cannot be negative.
    """
    _require_open_cycle(section.academic_cycle, "changing sections")

    if name is not None:
        name = _clean_code(name, field="name")
        if name == section.name:
            name = None

    if capacity is not None and capacity != section.capacity:
        if capacity < 0:
            raise DomainError("Section capacity cannot be negative.")
        # Lock the section so the occupancy read cannot go stale mid-decision.
        occupancy = locked_occupancy(section)
        if capacity != 0 and capacity < occupancy:
            raise DomainError(
                f"Capacity {capacity} is below the current occupancy of {occupancy} students."
            )
    else:
        capacity = None

    with unique_violation_as(_section_conflicts(name or section.name)):
        return _changed(section, actor, "academics.section.updated", name=name, capacity=capacity)


def locked_occupancy(section):
    """
    Active enrolment count read under a row lock on the section.

    Capacity decisions read the count and then write, so the section row is
    locked first: without it two concurrent enrolments both see the same count
    and can push occupancy past the declared capacity.
    """
    Section.objects.select_for_update().filter(pk=section.pk).exists()
    return section.enrolments.filter(status="active").count()


def deactivate_section(*, section, actor=None):
    """Deactivate a section instead of deleting it; refused while students remain."""
    if not section.is_active:
        return section

    occupancy = section.active_enrolment_count
    if occupancy:
        raise DomainError(
            f"Section '{section.name}' still has {occupancy} active enrolment(s). "
            "Move or withdraw them first."
        )

    section.is_active = False
    section.save(update_fields=["is_active", "updated_at"])
    _audit(actor, "academics.section.deactivated", section, name=section.name)
    return section
