"""Edge cases of the update / deactivate side of the catalogue services."""

import pytest

from apps.academics.models import Campus
from apps.academics.services import (
    deactivate_shift,
    deactivate_subject,
    update_campus,
    update_grade,
    update_level,
    update_level_subject,
    update_shift,
    update_subject,
)
from apps.common.models import DomainError
from tests.factories.academic import (
    CampusFactory,
    GradeFactory,
    InstitutionFactory,
    LevelFactory,
    LevelSubjectFactory,
    ShiftFactory,
    SubjectFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# --------------------------------------------------------------------------- #
# update_campus
# --------------------------------------------------------------------------- #


def test_update_campus_renames_and_trims():
    campus = CampusFactory(name="Sede Vieja")

    updated = update_campus(campus=campus, name="  Sede Nueva  ")

    assert updated.name == "Sede Nueva"


def test_update_campus_rejects_blank_name():
    campus = CampusFactory(name="Sede")

    with pytest.raises(DomainError, match="name"):
        update_campus(campus=campus, name="   ")


def test_update_campus_can_transfer_the_main_flag():
    institution = InstitutionFactory()
    current_main = CampusFactory(institution=institution, is_main=True)
    other = CampusFactory(institution=institution, is_main=False)

    update_campus(campus=other, is_main=True)

    current_main.refresh_from_db()
    assert current_main.is_main is False
    assert Campus.objects.filter(institution=institution, is_main=True).count() == 1


def test_update_campus_cannot_promote_an_inactive_campus():
    institution = InstitutionFactory()
    main = CampusFactory(institution=institution, is_main=True)
    retired = CampusFactory(institution=institution, is_active=False)

    with pytest.raises(DomainError, match="registro esta inactivo"):
        update_campus(campus=retired, is_main=True)

    main.refresh_from_db()
    assert main.is_main is True


def test_update_campus_demoting_the_main_campus_leaves_none_main():
    institution = InstitutionFactory()
    campus = CampusFactory(institution=institution, is_main=True)

    update_campus(campus=campus, is_main=False)

    assert Campus.objects.filter(institution=institution, is_main=True).exists() is False


def test_update_campus_with_no_changes_keeps_the_record():
    campus = CampusFactory(name="Sede", is_main=False)

    updated = update_campus(campus=campus)

    assert updated.name == "Sede"
    assert updated.is_main is False


def test_update_campus_repeating_the_same_main_value_is_a_no_op():
    institution = InstitutionFactory()
    campus = CampusFactory(institution=institution, is_main=True)

    update_campus(campus=campus, is_main=True)

    campus.refresh_from_db()
    assert campus.is_main is True


# --------------------------------------------------------------------------- #
# update_level
# --------------------------------------------------------------------------- #


def test_update_level_rejects_a_sequence_already_taken():
    institution = InstitutionFactory()
    LevelFactory(institution=institution, sequence=1)
    second = LevelFactory(institution=institution, sequence=2)

    with pytest.raises(DomainError, match="secuencia"):
        update_level(level=second, sequence=1)


def test_update_level_keeping_its_own_sequence_is_allowed():
    level = LevelFactory(sequence=3)

    updated = update_level(level=level, name="Basico", sequence=3)

    assert updated.sequence == 3
    assert updated.name == "Basico"


def test_update_level_rejects_non_positive_sequence():
    level = LevelFactory(sequence=2)

    with pytest.raises(DomainError, match="secuencia"):
        update_level(level=level, sequence=0)


def test_update_level_ignores_a_sequence_taken_in_another_institution():
    LevelFactory(institution=InstitutionFactory(), sequence=1)
    level = LevelFactory(institution=InstitutionFactory(), sequence=2)

    updated = update_level(level=level, sequence=1)

    assert updated.sequence == 1


# --------------------------------------------------------------------------- #
# update_grade
# --------------------------------------------------------------------------- #


def test_update_grade_rejects_a_sequence_already_taken_in_its_level():
    level = LevelFactory()
    GradeFactory(level=level, sequence=1)
    second = GradeFactory(level=level, sequence=2)

    with pytest.raises(DomainError, match="secuencia"):
        update_grade(grade=second, sequence=1)


def test_update_grade_allows_a_sequence_taken_in_another_level():
    institution = InstitutionFactory()
    primaria = LevelFactory(institution=institution, sequence=1)
    basico = LevelFactory(institution=institution, sequence=2)
    GradeFactory(level=primaria, sequence=1)
    grade = GradeFactory(level=basico, sequence=5)

    updated = update_grade(grade=grade, sequence=1)

    assert updated.sequence == 1


def test_update_grade_rejects_non_positive_sequence():
    grade = GradeFactory(sequence=2)

    with pytest.raises(DomainError, match="secuencia"):
        update_grade(grade=grade, sequence=0)


def test_update_grade_renames_without_touching_the_order():
    grade = GradeFactory(name="Primero", sequence=1)

    updated = update_grade(grade=grade, name="Primero Primaria")

    assert updated.name == "Primero Primaria"
    assert updated.sequence == 1


# --------------------------------------------------------------------------- #
# shifts and subjects
# --------------------------------------------------------------------------- #


def test_update_shift_renames_it():
    shift = ShiftFactory(name="Matutina")

    updated = update_shift(shift=shift, name="Jornada Matutina")

    assert updated.name == "Jornada Matutina"


def test_update_shift_rejects_blank_name():
    shift = ShiftFactory()

    with pytest.raises(DomainError, match="name"):
        update_shift(shift=shift, name="  ")


def test_deactivate_shift_is_idempotent():
    shift = ShiftFactory(is_active=False)

    deactivate_shift(shift=shift)

    shift.refresh_from_db()
    assert shift.is_active is False


def test_update_subject_renames_it():
    subject = SubjectFactory(name="Mate")

    updated = update_subject(subject=subject, name="Matematica")

    assert updated.name == "Matematica"


def test_deactivate_subject_keeps_its_level_links_as_history():
    link = LevelSubjectFactory()

    deactivate_subject(subject=link.subject)

    link.refresh_from_db()
    assert link.subject.is_active is False
    assert link.pk is not None


def test_deactivate_subject_is_idempotent():
    subject = SubjectFactory(is_active=False)

    deactivate_subject(subject=subject)

    subject.refresh_from_db()
    assert subject.is_active is False


# --------------------------------------------------------------------------- #
# level/subject link and sections
# --------------------------------------------------------------------------- #


def test_update_level_subject_with_no_fields_changes_nothing():
    link = LevelSubjectFactory(is_required=True, weekly_hours=4)

    updated = update_level_subject(level=link.level, subject=link.subject)

    assert updated.is_required is True
    assert updated.weekly_hours == 4


def test_update_level_subject_can_set_hours_back_to_zero():
    link = LevelSubjectFactory(weekly_hours=6)

    updated = update_level_subject(level=link.level, subject=link.subject, weekly_hours=0)

    assert updated.weekly_hours == 0
