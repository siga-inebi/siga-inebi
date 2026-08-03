import pytest

from apps.academics.models import Campus, Shift
from apps.academics.services import (
    create_campus,
    create_shift,
    deactivate_campus,
    deactivate_shift,
)
from apps.common.models import DomainError
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    GradeFactory,
    GradeOfferingFactory,
    InstitutionFactory,
    ShiftFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


# --------------------------------------------------------------------------- #
# create_campus
# --------------------------------------------------------------------------- #


def test_create_campus_normalises_code_to_upper_case():
    institution = InstitutionFactory()

    campus = create_campus(institution=institution, name="Sede Central", code="  central ")

    assert campus.code == "CENTRAL"
    assert campus.name == "Sede Central"
    assert campus.is_active is True


def test_create_campus_rejects_duplicate_code_in_same_institution():
    institution = InstitutionFactory()
    create_campus(institution=institution, name="Sede Central", code="CENTRAL")

    with pytest.raises(DomainError, match="already"):
        create_campus(institution=institution, name="Otra Sede", code="central")


def test_create_campus_allows_same_code_in_different_institutions():
    first = create_campus(institution=InstitutionFactory(), name="Central", code="CENTRAL")
    second = create_campus(institution=InstitutionFactory(), name="Central", code="CENTRAL")

    assert first.pk != second.pk
    assert Campus.objects.filter(code="CENTRAL").count() == 2


def test_create_campus_rejects_duplicate_code_even_when_existing_is_inactive():
    """Codes stay reserved: history is preserved, so reuse must be explicit."""
    institution = InstitutionFactory()
    existing = create_campus(institution=institution, name="Central", code="CENTRAL")
    existing.is_active = False
    existing.save(update_fields=["is_active"])

    with pytest.raises(DomainError, match="already"):
        create_campus(institution=institution, name="Central II", code="CENTRAL")


def test_create_campus_rejects_blank_code():
    with pytest.raises(DomainError, match="code"):
        create_campus(institution=InstitutionFactory(), name="Sede", code="   ")


def test_create_campus_rejects_blank_name():
    with pytest.raises(DomainError, match="name"):
        create_campus(institution=InstitutionFactory(), name="  ", code="CENTRAL")


def test_first_main_campus_is_kept_as_main():
    institution = InstitutionFactory()

    campus = create_campus(institution=institution, name="Central", code="CENTRAL", is_main=True)

    assert campus.is_main is True


def test_promoting_a_new_main_campus_demotes_the_previous_one():
    institution = InstitutionFactory()
    old_main = create_campus(institution=institution, name="Central", code="CENTRAL", is_main=True)

    new_main = create_campus(institution=institution, name="Anexo", code="ANEXO", is_main=True)

    old_main.refresh_from_db()
    assert old_main.is_main is False
    assert new_main.is_main is True
    assert Campus.objects.filter(institution=institution, is_main=True).count() == 1


def test_main_campus_flag_is_scoped_per_institution():
    other_main = create_campus(
        institution=InstitutionFactory(), name="Central", code="CENTRAL", is_main=True
    )

    create_campus(institution=InstitutionFactory(), name="Central", code="CENTRAL", is_main=True)

    other_main.refresh_from_db()
    assert other_main.is_main is True


# --------------------------------------------------------------------------- #
# deactivate_campus
# --------------------------------------------------------------------------- #


def test_deactivate_campus_preserves_the_record():
    campus = CampusFactory()

    deactivate_campus(campus=campus)

    campus.refresh_from_db()
    assert campus.is_active is False
    assert Campus.objects.filter(pk=campus.pk).exists()


def test_deactivate_campus_cascades_to_its_shifts():
    campus = CampusFactory()
    shift = ShiftFactory(campus=campus)

    deactivate_campus(campus=campus)

    shift.refresh_from_db()
    assert shift.is_active is False


def test_deactivate_campus_rejects_when_used_by_an_open_cycle():
    campus = CampusFactory()
    shift = ShiftFactory(campus=campus)
    cycle = AcademicCycleFactory(institution=campus.institution)
    GradeOfferingFactory(academic_cycle=cycle, shift=shift)

    with pytest.raises(DomainError, match="active cycle"):
        deactivate_campus(campus=campus)


def test_deactivate_campus_allowed_when_only_closed_cycles_reference_it():
    from apps.academics.models import AcademicCycle

    campus = CampusFactory()
    shift = ShiftFactory(campus=campus)
    cycle = AcademicCycleFactory(
        institution=campus.institution, status=AcademicCycle.CycleStatus.CLOSED
    )
    GradeOfferingFactory(academic_cycle=cycle, shift=shift)

    deactivate_campus(campus=campus)

    campus.refresh_from_db()
    assert campus.is_active is False


def test_deactivate_campus_is_idempotent():
    campus = CampusFactory(is_active=False)

    deactivate_campus(campus=campus)

    campus.refresh_from_db()
    assert campus.is_active is False


def test_deactivating_the_main_campus_clears_the_main_flag():
    institution = InstitutionFactory()
    campus = create_campus(institution=institution, name="Central", code="CENTRAL", is_main=True)

    deactivate_campus(campus=campus)

    campus.refresh_from_db()
    assert campus.is_main is False


# --------------------------------------------------------------------------- #
# create_shift
# --------------------------------------------------------------------------- #


def test_create_shift_belongs_to_the_campus():
    campus = CampusFactory()

    shift = create_shift(campus=campus, name="Matutina", code="mat")

    assert shift.campus == campus
    assert shift.code == "MAT"


def test_create_shift_rejects_duplicate_code_in_same_campus():
    campus = CampusFactory()
    create_shift(campus=campus, name="Matutina", code="MAT")

    with pytest.raises(DomainError, match="already"):
        create_shift(campus=campus, name="Matutina bis", code="mat")


def test_same_shift_code_can_exist_in_two_campuses():
    institution = InstitutionFactory()
    first = create_shift(campus=CampusFactory(institution=institution), name="M", code="MAT")
    second = create_shift(campus=CampusFactory(institution=institution), name="M", code="MAT")

    assert first.pk != second.pk
    assert Shift.objects.filter(code="MAT").count() == 2


def test_create_shift_rejects_inactive_campus():
    campus = CampusFactory(is_active=False)

    with pytest.raises(DomainError, match="inactive"):
        create_shift(campus=campus, name="Matutina", code="MAT")


def test_create_shift_rejects_blank_code():
    with pytest.raises(DomainError, match="code"):
        create_shift(campus=CampusFactory(), name="Matutina", code=" ")


# --------------------------------------------------------------------------- #
# deactivate_shift
# --------------------------------------------------------------------------- #


def test_deactivate_shift_preserves_the_record():
    shift = ShiftFactory()

    deactivate_shift(shift=shift)

    shift.refresh_from_db()
    assert shift.is_active is False


def test_deactivate_shift_rejects_when_used_by_an_open_cycle():
    shift = ShiftFactory()
    cycle = AcademicCycleFactory(institution=shift.campus.institution)
    GradeOfferingFactory(
        academic_cycle=cycle,
        shift=shift,
        grade=GradeFactory(institution=shift.campus.institution),
    )

    with pytest.raises(DomainError, match="active cycle"):
        deactivate_shift(shift=shift)
