"""
Domain services for the academic catalogue.

The catalogue is the structure enrolments are assigned to:

    Institution
      +-- Campus ("sede")
      |     +-- Shift ("jornada")
      +-- Level ("nivel")
      |     +-- Grade ("grado")
      |     +-- Subject link ("curso" del nivel)
      +-- AcademicCycle ("ciclo")
            +-- GradeOffering  (grade + shift, i.e. grade offered in a shift of a campus)
                  +-- Section

Every invariant lives here, never in views or serializers (AGENTS.md #8).
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

    record_event(
        actor=actor,
        action="academics.cycle.opened",
        resource="AcademicCycle",
        resource_identifier=str(cycle.pk),
        context={"name": cycle.name},
    )
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

    record_event(
        actor=actor,
        action="academics.cycle.closed",
        resource="AcademicCycle",
        resource_identifier=str(cycle.pk),
        context={"name": cycle.name},
    )
    return cycle


# --------------------------------------------------------------------------- #
# campuses ("sedes")
# --------------------------------------------------------------------------- #


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

    if Campus.objects.filter(institution=institution, code=code).exists():
        raise DomainError(f"Campus code '{code}' already exists for this institution.")

    if is_main:
        Campus.objects.filter(institution=institution, is_main=True).update(is_main=False)

    campus = Campus.objects.create(
        institution=institution,
        name=name,
        code=code,
        address=(address or "").strip(),
        is_main=is_main,
    )
    record_event(
        actor=actor,
        action="academics.campus.created",
        resource="Campus",
        resource_identifier=str(campus.pk),
        context={"code": code, "is_main": is_main},
    )
    return campus


@transaction.atomic
def update_campus(*, campus, name=None, address=None, is_main=None, actor=None):
    """Update the descriptive attributes of a campus. The code is immutable."""
    fields = ["updated_at"]

    if name is not None:
        campus.name = _clean_name(name)
        fields.append("name")

    if address is not None:
        campus.address = address.strip()
        fields.append("address")

    if is_main is not None and is_main != campus.is_main:
        if is_main:
            _require_active(campus, "Campus")
            Campus.objects.filter(institution=campus.institution, is_main=True).exclude(
                pk=campus.pk
            ).update(is_main=False)
        campus.is_main = is_main
        fields.append("is_main")

    campus.save(update_fields=fields)
    record_event(
        actor=actor,
        action="academics.campus.updated",
        resource="Campus",
        resource_identifier=str(campus.pk),
        context={"fields": [f for f in fields if f != "updated_at"]},
    )
    return campus


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

    record_event(
        actor=actor,
        action="academics.campus.deactivated",
        resource="Campus",
        resource_identifier=str(campus.pk),
        context={"code": campus.code},
    )
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

    if Shift.objects.filter(campus=campus, code=code).exists():
        raise DomainError(f"Shift code '{code}' already exists for campus '{campus.name}'.")

    shift = Shift.objects.create(campus=campus, name=name, code=code)
    record_event(
        actor=actor,
        action="academics.shift.created",
        resource="Shift",
        resource_identifier=str(shift.pk),
        context={"campus_id": campus.pk, "code": code},
    )
    return shift


def update_shift(*, shift, name=None, actor=None):
    """Rename a shift. The code is immutable."""
    if name is not None:
        shift.name = _clean_name(name)
        shift.save(update_fields=["name", "updated_at"])
        record_event(
            actor=actor,
            action="academics.shift.updated",
            resource="Shift",
            resource_identifier=str(shift.pk),
            context={"name": shift.name},
        )
    return shift


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
    record_event(
        actor=actor,
        action="academics.shift.deactivated",
        resource="Shift",
        resource_identifier=str(shift.pk),
        context={"code": shift.code},
    )
    return shift


# --------------------------------------------------------------------------- #
# levels ("niveles")
# --------------------------------------------------------------------------- #


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
    if sequence is None or sequence < 1:
        raise DomainError("Level sequence must be a positive integer.")

    if Level.objects.filter(institution=institution, code=code).exists():
        raise DomainError(f"Level code '{code}' already exists for this institution.")

    if Level.objects.filter(institution=institution, sequence=sequence).exists():
        raise DomainError(f"Level sequence {sequence} is already used by another level.")

    level = Level.objects.create(institution=institution, name=name, code=code, sequence=sequence)
    record_event(
        actor=actor,
        action="academics.level.created",
        resource="Level",
        resource_identifier=str(level.pk),
        context={"code": code, "sequence": sequence},
    )
    return level


def update_level(*, level, name=None, sequence=None, actor=None):
    """Rename a level or move it in the pedagogical order. The code is immutable."""
    fields = ["updated_at"]

    if name is not None:
        level.name = _clean_name(name)
        fields.append("name")

    if sequence is not None and sequence != level.sequence:
        if sequence < 1:
            raise DomainError("Level sequence must be a positive integer.")
        clash = (
            Level.objects.filter(institution_id=level.institution_id, sequence=sequence)
            .exclude(pk=level.pk)
            .exists()
        )
        if clash:
            raise DomainError(f"Level sequence {sequence} is already used by another level.")
        level.sequence = sequence
        fields.append("sequence")

    level.save(update_fields=fields)
    record_event(
        actor=actor,
        action="academics.level.updated",
        resource="Level",
        resource_identifier=str(level.pk),
        context={"fields": [f for f in fields if f != "updated_at"]},
    )
    return level


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

    record_event(
        actor=actor,
        action="academics.level.deactivated",
        resource="Level",
        resource_identifier=str(level.pk),
        context={"code": level.code},
    )
    return level


# --------------------------------------------------------------------------- #
# grades ("grados")
# --------------------------------------------------------------------------- #


def create_grade(*, level, name, code, sequence, actor=None):
    """
    Register a grade inside a level (RF-EST-001).

    Rules:
    - Level must be active.
    - Code unique institution-wide, so "G1" never means two different grades.
    - Sequence positive and unique inside the level.
    """
    _require_active(level, "Level")
    name = _clean_name(name)
    code = _clean_code(code)
    if sequence is None or sequence < 1:
        raise DomainError("Grade sequence must be a positive integer.")

    if Grade.objects.filter(level__institution_id=level.institution_id, code=code).exists():
        raise DomainError(f"Grade code '{code}' already exists for this institution.")

    if Grade.objects.filter(level=level, sequence=sequence).exists():
        raise DomainError(f"Grade sequence {sequence} is already used inside level '{level.name}'.")

    grade = Grade.objects.create(level=level, name=name, code=code, sequence=sequence)
    record_event(
        actor=actor,
        action="academics.grade.created",
        resource="Grade",
        resource_identifier=str(grade.pk),
        context={"level_id": level.pk, "code": code},
    )
    return grade


def update_grade(*, grade, name=None, sequence=None, actor=None):
    """Rename a grade or reorder it inside its level. The code is immutable."""
    fields = ["updated_at"]

    if name is not None:
        grade.name = _clean_name(name)
        fields.append("name")

    if sequence is not None and sequence != grade.sequence:
        if sequence < 1:
            raise DomainError("Grade sequence must be a positive integer.")
        clash = (
            Grade.objects.filter(level_id=grade.level_id, sequence=sequence)
            .exclude(pk=grade.pk)
            .exists()
        )
        if clash:
            raise DomainError(f"Grade sequence {sequence} is already used inside this level.")
        grade.sequence = sequence
        fields.append("sequence")

    grade.save(update_fields=fields)
    record_event(
        actor=actor,
        action="academics.grade.updated",
        resource="Grade",
        resource_identifier=str(grade.pk),
        context={"fields": [f for f in fields if f != "updated_at"]},
    )
    return grade


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
    record_event(
        actor=actor,
        action="academics.grade.deactivated",
        resource="Grade",
        resource_identifier=str(grade.pk),
        context={"code": grade.code},
    )
    return grade


# --------------------------------------------------------------------------- #
# subjects ("cursos") and their link to levels
# --------------------------------------------------------------------------- #


def create_subject(*, institution, name, code, actor=None):
    """Register a subject. Code unique per institution."""
    name = _clean_name(name)
    code = _clean_code(code)

    if Subject.objects.filter(institution=institution, code=code).exists():
        raise DomainError(f"Subject code '{code}' already exists for this institution.")

    subject = Subject.objects.create(institution=institution, name=name, code=code)
    record_event(
        actor=actor,
        action="academics.subject.created",
        resource="Subject",
        resource_identifier=str(subject.pk),
        context={"code": code},
    )
    return subject


def update_subject(*, subject, name=None, actor=None):
    """Rename a subject. The code is immutable."""
    if name is not None:
        subject.name = _clean_name(name)
        subject.save(update_fields=["name", "updated_at"])
        record_event(
            actor=actor,
            action="academics.subject.updated",
            resource="Subject",
            resource_identifier=str(subject.pk),
            context={"name": subject.name},
        )
    return subject


def deactivate_subject(*, subject, actor=None):
    """Deactivate a subject; existing level links are kept for history."""
    if not subject.is_active:
        return subject

    subject.is_active = False
    subject.save(update_fields=["is_active", "updated_at"])
    record_event(
        actor=actor,
        action="academics.subject.deactivated",
        resource="Subject",
        resource_identifier=str(subject.pk),
        context={"code": subject.code},
    )
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

    if LevelSubject.objects.filter(level=level, subject=subject).exists():
        raise DomainError(f"Subject '{subject.name}' is already linked to level '{level.name}'.")

    link = LevelSubject.objects.create(
        level=level,
        subject=subject,
        is_required=is_required,
        weekly_hours=weekly_hours or 0,
    )
    record_event(
        actor=actor,
        action="academics.level_subject.linked",
        resource="LevelSubject",
        resource_identifier=str(link.pk),
        context={"level_id": level.pk, "subject_id": subject.pk},
    )
    return link


def _get_link(level, subject):
    try:
        return LevelSubject.objects.get(level=level, subject=subject)
    except LevelSubject.DoesNotExist as exc:
        raise DomainError(
            f"Subject '{subject.name}' is not linked to level '{level.name}'."
        ) from exc


def update_level_subject(*, level, subject, is_required=None, weekly_hours=None, actor=None):
    """Update the curricular metadata of an existing level/subject link."""
    _validate_weekly_hours(weekly_hours)
    link = _get_link(level, subject)

    fields = ["updated_at"]
    if is_required is not None:
        link.is_required = is_required
        fields.append("is_required")
    if weekly_hours is not None:
        link.weekly_hours = weekly_hours
        fields.append("weekly_hours")

    link.save(update_fields=fields)
    record_event(
        actor=actor,
        action="academics.level_subject.updated",
        resource="LevelSubject",
        resource_identifier=str(link.pk),
        context={"fields": [f for f in fields if f != "updated_at"]},
    )
    return link


def unlink_subject_from_level(*, level, subject, actor=None):
    """Remove a subject from a level. The link carries no history of its own."""
    link = _get_link(level, subject)
    link_pk = link.pk
    link.delete()

    record_event(
        actor=actor,
        action="academics.level_subject.unlinked",
        resource="LevelSubject",
        resource_identifier=str(link_pk),
        context={"level_id": level.pk, "subject_id": subject.pk},
    )


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

    if GradeOffering.objects.filter(academic_cycle=cycle, shift=shift, grade=grade).exists():
        raise DomainError(
            f"Grade '{grade.name}' is already offered in shift '{shift.name}' "
            f"of campus '{shift.campus.name}' for cycle '{cycle.name}'."
        )

    offering = GradeOffering.objects.create(academic_cycle=cycle, shift=shift, grade=grade)
    record_event(
        actor=actor,
        action="academics.grade_offering.created",
        resource="GradeOffering",
        resource_identifier=str(offering.pk),
        context={"cycle_id": cycle.pk, "shift_id": shift.pk, "grade_id": grade.pk},
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

    offering_pk = offering.pk
    offering.delete()
    record_event(
        actor=actor,
        action="academics.grade_offering.removed",
        resource="GradeOffering",
        resource_identifier=str(offering_pk),
        context={},
    )


# --------------------------------------------------------------------------- #
# sections
# --------------------------------------------------------------------------- #


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

    if Section.objects.filter(offering=offering, name=name).exists():
        raise DomainError(f"Section '{name}' already exists in this grade offering.")

    section = Section.objects.create(offering=offering, name=name, capacity=capacity)
    record_event(
        actor=actor,
        action="academics.section.created",
        resource="Section",
        resource_identifier=str(section.pk),
        context={"offering_id": offering.pk, "name": name},
    )
    return section


def update_section(*, section, name=None, capacity=None, actor=None):
    """
    Rename a section or change its declared capacity (RF-EST-008).

    Rules:
    - Cycle must not be closed.
    - Name stays unique inside the offering.
    - Capacity cannot drop below current occupancy, and cannot be negative.
    """
    _require_open_cycle(section.academic_cycle, "changing sections")
    fields = ["updated_at"]

    if name is not None:
        new_name = _clean_code(name, field="name")
        if new_name != section.name:
            clash = (
                Section.objects.filter(offering_id=section.offering_id, name=new_name)
                .exclude(pk=section.pk)
                .exists()
            )
            if clash:
                raise DomainError(f"Section '{new_name}' already exists in this grade offering.")
            section.name = new_name
            fields.append("name")

    if capacity is not None and capacity != section.capacity:
        if capacity < 0:
            raise DomainError("Section capacity cannot be negative.")
        occupancy = section.active_enrolment_count
        if capacity != 0 and capacity < occupancy:
            raise DomainError(
                f"Capacity {capacity} is below the current occupancy of {occupancy} students."
            )
        section.capacity = capacity
        fields.append("capacity")

    section.save(update_fields=fields)
    record_event(
        actor=actor,
        action="academics.section.updated",
        resource="Section",
        resource_identifier=str(section.pk),
        context={"fields": [f for f in fields if f != "updated_at"]},
    )
    return section


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
    record_event(
        actor=actor,
        action="academics.section.deactivated",
        resource="Section",
        resource_identifier=str(section.pk),
        context={"name": section.name},
    )
    return section
