import pytest

from apps.academics.models import Grade, Level, LevelSubject
from apps.academics.services import (
    create_grade,
    create_level,
    create_subject,
    deactivate_grade,
    deactivate_level,
    link_subject_to_level,
    unlink_subject_from_level,
    update_level_subject,
)
from apps.common.models import DomainError
from tests.factories.academic import (
    AcademicCycleFactory,
    GradeFactory,
    GradeOfferingFactory,
    InstitutionFactory,
    LevelFactory,
    LevelSubjectFactory,
    SubjectFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# --------------------------------------------------------------------------- #
# create_level  (Preprimaria, Primaria, Basico, Diversificado)
# --------------------------------------------------------------------------- #


def test_create_level_normalises_code_and_keeps_sequence():
    institution = InstitutionFactory()

    level = create_level(institution=institution, name="Primaria", code=" pri ", sequence=2)

    assert level.code == "PRI"
    assert level.sequence == 2
    assert level.institution == institution


def test_create_level_rejects_duplicate_code_in_institution():
    institution = InstitutionFactory()
    create_level(institution=institution, name="Primaria", code="PRI", sequence=1)

    with pytest.raises(DomainError, match="already"):
        create_level(institution=institution, name="Primaria bis", code="pri", sequence=2)


def test_create_level_rejects_duplicate_sequence_in_institution():
    """Sequence drives pedagogical ordering, so it must be unambiguous."""
    institution = InstitutionFactory()
    create_level(institution=institution, name="Preprimaria", code="PRE", sequence=1)

    with pytest.raises(DomainError, match="secuencia"):
        create_level(institution=institution, name="Primaria", code="PRI", sequence=1)


def test_create_level_allows_same_sequence_in_another_institution():
    create_level(institution=InstitutionFactory(), name="Primaria", code="PRI", sequence=1)
    other = create_level(institution=InstitutionFactory(), name="Primaria", code="PRI", sequence=1)

    assert other.pk is not None
    assert Level.objects.filter(sequence=1).count() == 2


def test_create_level_rejects_zero_or_negative_sequence():
    institution = InstitutionFactory()

    with pytest.raises(DomainError, match="secuencia"):
        create_level(institution=institution, name="Primaria", code="PRI", sequence=0)


def test_levels_are_returned_in_pedagogical_order():
    institution = InstitutionFactory()
    create_level(institution=institution, name="Diversificado", code="DIV", sequence=4)
    create_level(institution=institution, name="Preprimaria", code="PRE", sequence=1)
    create_level(institution=institution, name="Basico", code="BAS", sequence=3)
    create_level(institution=institution, name="Primaria", code="PRI", sequence=2)

    codes = list(Level.objects.filter(institution=institution).values_list("code", flat=True))

    assert codes == ["PRE", "PRI", "BAS", "DIV"]


# --------------------------------------------------------------------------- #
# create_grade  (Primero Primaria, Segundo Primaria, ...)
# --------------------------------------------------------------------------- #


def test_create_grade_belongs_to_a_level():
    level = LevelFactory(name="Primaria", code="PRI")

    grade = create_grade(level=level, name="Primero Primaria", code=" pri1 ", sequence=1)

    assert grade.level == level
    assert grade.code == "PRI1"
    assert grade.institution == level.institution


def test_create_grade_rejects_duplicate_code_in_same_level():
    level = LevelFactory()
    create_grade(level=level, name="Primero", code="PRI1", sequence=1)

    with pytest.raises(DomainError, match="already"):
        create_grade(level=level, name="Primero bis", code="pri1", sequence=2)


def test_create_grade_rejects_duplicate_code_across_levels_of_same_institution():
    """A grade code identifies the grade institution-wide, not just per level."""
    institution = InstitutionFactory()
    primaria = LevelFactory(institution=institution, code="PRI", sequence=1)
    basico = LevelFactory(institution=institution, code="BAS", sequence=2)
    create_grade(level=primaria, name="Primero Primaria", code="G1", sequence=1)

    with pytest.raises(DomainError, match="already"):
        create_grade(level=basico, name="Primero Basico", code="G1", sequence=1)


def test_create_grade_rejects_duplicate_sequence_in_same_level():
    level = LevelFactory()
    create_grade(level=level, name="Primero", code="PRI1", sequence=1)

    with pytest.raises(DomainError, match="secuencia"):
        create_grade(level=level, name="Segundo", code="PRI2", sequence=1)


def test_create_grade_allows_same_sequence_in_a_different_level():
    institution = InstitutionFactory()
    primaria = LevelFactory(institution=institution, code="PRI", sequence=1)
    basico = LevelFactory(institution=institution, code="BAS", sequence=2)
    create_grade(level=primaria, name="Primero Primaria", code="PRI1", sequence=1)

    grade = create_grade(level=basico, name="Primero Basico", code="BAS1", sequence=1)

    assert grade.sequence == 1


def test_create_grade_rejects_inactive_level():
    level = LevelFactory(is_active=False)

    with pytest.raises(DomainError, match="registro esta inactivo"):
        create_grade(level=level, name="Primero", code="PRI1", sequence=1)


def test_grades_are_ordered_by_level_then_sequence():
    institution = InstitutionFactory()
    primaria = LevelFactory(institution=institution, code="PRI", sequence=1)
    basico = LevelFactory(institution=institution, code="BAS", sequence=2)
    create_grade(level=basico, name="Primero Basico", code="BAS1", sequence=1)
    create_grade(level=primaria, name="Segundo Primaria", code="PRI2", sequence=2)
    create_grade(level=primaria, name="Primero Primaria", code="PRI1", sequence=1)

    codes = list(
        Grade.objects.filter(level__institution=institution).values_list("code", flat=True)
    )

    assert codes == ["PRI1", "PRI2", "BAS1"]


# --------------------------------------------------------------------------- #
# deactivate_level / deactivate_grade
# --------------------------------------------------------------------------- #


def test_deactivate_level_cascades_to_its_grades():
    level = LevelFactory()
    grade = GradeFactory(level=level)

    deactivate_level(level=level)

    level.refresh_from_db()
    grade.refresh_from_db()
    assert level.is_active is False
    assert grade.is_active is False


def test_deactivate_level_rejects_when_a_grade_is_offered_in_an_open_cycle():
    level = LevelFactory()
    grade = GradeFactory(level=level)
    cycle = AcademicCycleFactory(institution=level.institution)
    GradeOfferingFactory(academic_cycle=cycle, grade=grade)

    with pytest.raises(DomainError, match="ciclo activo"):
        deactivate_level(level=level)


def test_deactivate_grade_rejects_when_offered_in_an_open_cycle():
    grade = GradeFactory()
    cycle = AcademicCycleFactory(institution=grade.level.institution)
    GradeOfferingFactory(academic_cycle=cycle, grade=grade)

    with pytest.raises(DomainError, match="ciclo activo"):
        deactivate_grade(grade=grade)


def test_deactivate_grade_preserves_the_record():
    grade = GradeFactory()

    deactivate_grade(grade=grade)

    grade.refresh_from_db()
    assert grade.is_active is False
    assert Grade.objects.filter(pk=grade.pk).exists()


# --------------------------------------------------------------------------- #
# create_subject
# --------------------------------------------------------------------------- #


def test_create_subject_normalises_code():
    institution = InstitutionFactory()

    subject = create_subject(institution=institution, name="Matematica", code=" mat ")

    assert subject.code == "MAT"


def test_create_subject_rejects_duplicate_code_in_institution():
    institution = InstitutionFactory()
    create_subject(institution=institution, name="Matematica", code="MAT")

    with pytest.raises(DomainError, match="already"):
        create_subject(institution=institution, name="Matematicas", code="mat")


def test_create_subject_rejects_blank_name():
    with pytest.raises(DomainError, match="name"):
        create_subject(institution=InstitutionFactory(), name="   ", code="MAT")


# --------------------------------------------------------------------------- #
# link_subject_to_level
# --------------------------------------------------------------------------- #


def test_link_subject_to_level_creates_the_relation():
    institution = InstitutionFactory()
    level = LevelFactory(institution=institution)
    subject = SubjectFactory(institution=institution)

    link = link_subject_to_level(level=level, subject=subject, weekly_hours=5)

    assert link.level == level
    assert link.subject == subject
    assert link.weekly_hours == 5
    assert link.is_required is True


def test_a_subject_can_be_linked_to_several_levels():
    institution = InstitutionFactory()
    subject = SubjectFactory(institution=institution)
    primaria = LevelFactory(institution=institution, sequence=1)
    basico = LevelFactory(institution=institution, sequence=2)

    link_subject_to_level(level=primaria, subject=subject)
    link_subject_to_level(level=basico, subject=subject)

    assert LevelSubject.objects.filter(subject=subject).count() == 2
    assert set(subject.levels.values_list("pk", flat=True)) == {primaria.pk, basico.pk}


def test_link_subject_to_level_rejects_duplicate_link():
    link = LevelSubjectFactory()

    with pytest.raises(DomainError, match="already"):
        link_subject_to_level(level=link.level, subject=link.subject)


def test_link_subject_to_level_rejects_cross_institution_pairing():
    level = LevelFactory()
    foreign_subject = SubjectFactory()

    with pytest.raises(DomainError, match="misma institucion"):
        link_subject_to_level(level=level, subject=foreign_subject)


def test_link_subject_to_level_rejects_inactive_level():
    institution = InstitutionFactory()
    level = LevelFactory(institution=institution, is_active=False)
    subject = SubjectFactory(institution=institution)

    with pytest.raises(DomainError, match="registro esta inactivo"):
        link_subject_to_level(level=level, subject=subject)


def test_link_subject_to_level_rejects_inactive_subject():
    institution = InstitutionFactory()
    level = LevelFactory(institution=institution)
    subject = SubjectFactory(institution=institution, is_active=False)

    with pytest.raises(DomainError, match="registro esta inactivo"):
        link_subject_to_level(level=level, subject=subject)


def test_link_subject_to_level_rejects_negative_weekly_hours():
    institution = InstitutionFactory()
    level = LevelFactory(institution=institution)
    subject = SubjectFactory(institution=institution)

    with pytest.raises(DomainError, match="(?i)horas semanales"):
        link_subject_to_level(level=level, subject=subject, weekly_hours=-1)


def test_link_subject_to_level_accepts_zero_weekly_hours_as_unspecified():
    institution = InstitutionFactory()
    level = LevelFactory(institution=institution)
    subject = SubjectFactory(institution=institution)

    link = link_subject_to_level(level=level, subject=subject, weekly_hours=0)

    assert link.weekly_hours == 0


def test_relinking_a_previously_unlinked_subject_is_allowed():
    link = LevelSubjectFactory()
    level, subject = link.level, link.subject
    unlink_subject_from_level(level=level, subject=subject)

    relinked = link_subject_to_level(level=level, subject=subject, is_required=False)

    assert relinked.is_required is False
    assert LevelSubject.objects.filter(level=level, subject=subject).count() == 1


# --------------------------------------------------------------------------- #
# update_level_subject / unlink_subject_from_level
# --------------------------------------------------------------------------- #


def test_update_level_subject_changes_requirement_and_hours():
    link = LevelSubjectFactory(is_required=True, weekly_hours=4)

    updated = update_level_subject(
        level=link.level, subject=link.subject, is_required=False, weekly_hours=2
    )

    assert updated.is_required is False
    assert updated.weekly_hours == 2


def test_update_level_subject_rejects_negative_weekly_hours():
    link = LevelSubjectFactory()

    with pytest.raises(DomainError, match="(?i)horas semanales"):
        update_level_subject(level=link.level, subject=link.subject, weekly_hours=-3)


def test_update_level_subject_rejects_unlinked_pair():
    institution = InstitutionFactory()
    level = LevelFactory(institution=institution)
    subject = SubjectFactory(institution=institution)

    with pytest.raises(DomainError, match="no esta vinculado"):
        update_level_subject(level=level, subject=subject, weekly_hours=1)


def test_unlink_subject_from_level_removes_the_relation():
    link = LevelSubjectFactory()

    unlink_subject_from_level(level=link.level, subject=link.subject)

    assert LevelSubject.objects.filter(pk=link.pk).exists() is False


def test_unlink_subject_from_level_rejects_unlinked_pair():
    institution = InstitutionFactory()
    level = LevelFactory(institution=institution)
    subject = SubjectFactory(institution=institution)

    with pytest.raises(DomainError, match="no esta vinculado"):
        unlink_subject_from_level(level=level, subject=subject)
