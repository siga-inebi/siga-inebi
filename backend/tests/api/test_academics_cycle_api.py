"""
HTTP contract of the cycle-scoped structure.

The service tests already cover the domain rules; what is checked here is the
translation: status codes, the shape of each payload, how a ``DomainError``
surfaces as a 400 envelope, and that nested routes resolve their parent.
"""

import datetime

import pytest
from django.urls import reverse

from apps.academics.models import (
    AcademicCycle,
    CurriculumPlan,
    GradeOffering,
    Section,
    TeachingAssignment,
)
from apps.academics.services import add_curriculum_entry
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    GradeFactory,
    GradeOfferingFactory,
    InstitutionFactory,
    SectionFactory,
    ShiftFactory,
    SubjectFactory,
)
from tests.factories.people import PersonFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

MISSING_UUID = "00000000-0000-0000-0000-000000000000"
STARTS_ON = "2026-01-15"
ENDS_ON = "2026-11-30"


def _detail(response):
    return response.json()["error"]["detail"]


def _items(response):
    return response.json()["results"]


def _draft_cycle(institution):
    return AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.DRAFT)


def _offering(institution, cycle=None):
    cycle = cycle or _draft_cycle(institution)
    return GradeOfferingFactory(
        academic_cycle=cycle,
        grade=GradeFactory(institution=institution),
        shift=ShiftFactory(campus=CampusFactory(institution=institution)),
    )


def _planned_section(institution):
    """Section whose grade already studies one subject, ready for an assignment."""
    section = SectionFactory(offering=_offering(institution))
    subject = SubjectFactory(institution=institution)
    add_curriculum_entry(cycle=section.academic_cycle, grade=section.grade, subject=subject)
    return section, subject


# --------------------------------------------------------------------------- #
# authentication
# --------------------------------------------------------------------------- #


@pytest.mark.security
def test_cycle_endpoints_require_authentication(client):
    response = client.get(reverse("cycle-list-create"))

    assert response.status_code in (401, 403)


# --------------------------------------------------------------------------- #
# cycles
# --------------------------------------------------------------------------- #


def test_create_cycle_returns_201_in_draft(auth_client, institution):
    response = auth_client.post(
        reverse("cycle-list-create"),
        {"name": "Ciclo 2026", "starts_on": STARTS_ON, "ends_on": ENDS_ON},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["offering_count"] == 0
    assert AcademicCycle.objects.filter(institution=institution, name="Ciclo 2026").exists()


def test_create_cycle_rejects_duplicate_name_with_400(auth_client, institution):
    AcademicCycleFactory(institution=institution, name="Ciclo 2026")

    response = auth_client.post(
        reverse("cycle-list-create"),
        {"name": "Ciclo 2026", "starts_on": STARTS_ON, "ends_on": ENDS_ON},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "already exists" in str(_detail(response))


def test_create_cycle_rejects_an_end_date_before_the_start(auth_client, institution):
    response = auth_client.post(
        reverse("cycle-list-create"),
        {"name": "Ciclo", "starts_on": ENDS_ON, "ends_on": STARTS_ON},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "later than" in str(_detail(response))


def test_list_cycles_reports_how_many_grades_each_one_offers(auth_client, institution):
    cycle = _draft_cycle(institution)
    _offering(institution, cycle)

    response = auth_client.get(reverse("cycle-list-create"))

    assert response.status_code == 200
    assert _items(response)[0]["offering_count"] == 1


def test_update_cycle_renames_it(auth_client, institution):
    cycle = _draft_cycle(institution)

    response = auth_client.patch(
        reverse("cycle-detail", args=[cycle.public_id]),
        {"name": "Ciclo renombrado"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Ciclo renombrado"


def test_update_a_closed_cycle_returns_400(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.CLOSED)

    response = auth_client.patch(
        reverse("cycle-detail", args=[cycle.public_id]),
        {"name": "Otro"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "closed" in str(_detail(response))


def test_unknown_cycle_returns_404(auth_client, institution):
    response = auth_client.get(reverse("cycle-detail", args=[MISSING_UUID]))

    assert response.status_code == 404


def test_a_cycle_of_another_institution_is_not_reachable(auth_client, institution):
    foreign = AcademicCycleFactory(institution=InstitutionFactory())

    response = auth_client.get(reverse("cycle-detail", args=[foreign.public_id]))

    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# cycle status
# --------------------------------------------------------------------------- #


def test_activating_an_empty_cycle_returns_400(auth_client, institution):
    cycle = _draft_cycle(institution)

    response = auth_client.post(
        reverse("cycle-status", args=[cycle.public_id]),
        {"status": "active"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "no grade offering" in str(_detail(response))


def test_activating_a_cycle_with_an_offering_returns_the_new_status(auth_client, institution):
    cycle = _draft_cycle(institution)
    _offering(institution, cycle)

    response = auth_client.post(
        reverse("cycle-status", args=[cycle.public_id]),
        {"status": "active"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_moving_a_cycle_backwards_returns_400(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.ACTIVE)

    response = auth_client.post(
        reverse("cycle-status", args=[cycle.public_id]),
        {"status": "draft"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "cannot move" in str(_detail(response))


def test_an_unknown_status_is_rejected_by_the_serializer(auth_client, institution):
    cycle = _draft_cycle(institution)

    response = auth_client.post(
        reverse("cycle-status", args=[cycle.public_id]),
        {"status": "paused"},
        content_type="application/json",
    )

    assert response.status_code == 400


# --------------------------------------------------------------------------- #
# grade offerings
# --------------------------------------------------------------------------- #


def test_offer_grade_returns_201_with_campus_and_counts(auth_client, institution):
    cycle = _draft_cycle(institution)
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus=CampusFactory(institution=institution))

    response = auth_client.post(
        reverse("cycle-offering-list-create", args=[cycle.public_id]),
        {"grade_id": str(grade.public_id), "shift_id": str(shift.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["grade"]["code"] == grade.code
    assert body["campus"]["code"] == shift.campus.code
    assert body["section_count"] == 0
    assert body["enrolment_count"] == 0


def test_offer_grade_rejects_an_unknown_grade_with_400(auth_client, institution):
    cycle = _draft_cycle(institution)
    shift = ShiftFactory(campus=CampusFactory(institution=institution))

    response = auth_client.post(
        reverse("cycle-offering-list-create", args=[cycle.public_id]),
        {"grade_id": MISSING_UUID, "shift_id": str(shift.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "Grade not found" in str(_detail(response))


def test_offer_grade_rejects_a_grade_of_another_institution_with_400(auth_client, institution):
    cycle = _draft_cycle(institution)
    shift = ShiftFactory(campus=CampusFactory(institution=institution))
    foreign_grade = GradeFactory(institution=InstitutionFactory())

    response = auth_client.post(
        reverse("cycle-offering-list-create", args=[cycle.public_id]),
        {"grade_id": str(foreign_grade.public_id), "shift_id": str(shift.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "same institution" in str(_detail(response))


def test_list_offerings_of_a_cycle_excludes_other_cycles(auth_client, institution):
    cycle = _draft_cycle(institution)
    _offering(institution, cycle)
    _offering(institution)

    response = auth_client.get(reverse("cycle-offering-list-create", args=[cycle.public_id]))

    assert response.status_code == 200
    assert len(_items(response)) == 1


def test_withdraw_offering_returns_204_and_deactivates_it(auth_client, institution):
    offering = _offering(institution)

    response = auth_client.delete(reverse("offering-detail", args=[offering.public_id]))

    assert response.status_code == 204
    assert GradeOffering.objects.get(pk=offering.pk).is_active is False


# --------------------------------------------------------------------------- #
# sections
# --------------------------------------------------------------------------- #


def test_create_section_returns_201_with_normalised_name(auth_client, institution):
    offering = _offering(institution)

    response = auth_client.post(
        reverse("offering-section-list-create", args=[offering.public_id]),
        {"name": "a", "capacity": 30},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "A"
    assert body["available_seats"] == 30
    assert body["enrolment_count"] == 0


def test_a_section_without_capacity_reports_no_available_seats(auth_client, institution):
    offering = _offering(institution)

    response = auth_client.post(
        reverse("offering-section-list-create", args=[offering.public_id]),
        {"name": "U"},
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["available_seats"] is None


def test_create_section_rejects_a_duplicate_name_with_400(auth_client, institution):
    offering = _offering(institution)
    SectionFactory(offering=offering, name="A")

    response = auth_client.post(
        reverse("offering-section-list-create", args=[offering.public_id]),
        {"name": "A"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "already exists" in str(_detail(response))


def test_update_section_changes_its_capacity(auth_client, institution):
    section = SectionFactory(offering=_offering(institution), capacity=20)

    response = auth_client.patch(
        reverse("section-detail", args=[section.public_id]),
        {"capacity": 25},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["capacity"] == 25


def test_deactivate_section_returns_204(auth_client, institution):
    section = SectionFactory(offering=_offering(institution))

    response = auth_client.delete(reverse("section-detail", args=[section.public_id]))

    assert response.status_code == 204
    assert Section.objects.get(pk=section.pk).is_active is False


# --------------------------------------------------------------------------- #
# curriculum plan
# --------------------------------------------------------------------------- #


def test_add_curriculum_entry_returns_201(auth_client, institution):
    cycle = _draft_cycle(institution)
    grade = GradeFactory(institution=institution)
    subject = SubjectFactory(institution=institution)

    response = auth_client.post(
        reverse("cycle-curriculum-list-create", args=[cycle.public_id]),
        {"grade_id": str(grade.public_id), "subject_id": str(subject.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["subject"]["code"] == subject.code
    assert body["grade"]["code"] == grade.code
    assert body["is_required"] is True


def test_add_curriculum_entry_rejects_a_duplicate_with_400(auth_client, institution):
    cycle = _draft_cycle(institution)
    grade = GradeFactory(institution=institution)
    subject = SubjectFactory(institution=institution)
    add_curriculum_entry(cycle=cycle, grade=grade, subject=subject)

    response = auth_client.post(
        reverse("cycle-curriculum-list-create", args=[cycle.public_id]),
        {"grade_id": str(grade.public_id), "subject_id": str(subject.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "already in the plan" in str(_detail(response))


def test_curriculum_list_can_be_narrowed_to_one_grade(auth_client, institution):
    cycle = _draft_cycle(institution)
    wanted = GradeFactory(institution=institution)
    other = GradeFactory(institution=institution)
    add_curriculum_entry(cycle=cycle, grade=wanted, subject=SubjectFactory(institution=institution))
    add_curriculum_entry(cycle=cycle, grade=other, subject=SubjectFactory(institution=institution))

    response = auth_client.get(
        reverse("cycle-curriculum-list-create", args=[cycle.public_id]),
        {"grade": str(wanted.public_id)},
    )

    assert response.status_code == 200
    items = _items(response)
    assert len(items) == 1
    assert items[0]["grade"]["code"] == wanted.code


def test_update_curriculum_entry_turns_a_subject_optional(auth_client, institution):
    cycle = _draft_cycle(institution)
    entry = add_curriculum_entry(
        cycle=cycle,
        grade=GradeFactory(institution=institution),
        subject=SubjectFactory(institution=institution),
    )

    response = auth_client.patch(
        reverse("curriculum-entry-detail", args=[entry.public_id]),
        {"is_required": False},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["is_required"] is False


def test_remove_curriculum_entry_returns_204(auth_client, institution):
    cycle = _draft_cycle(institution)
    entry = add_curriculum_entry(
        cycle=cycle,
        grade=GradeFactory(institution=institution),
        subject=SubjectFactory(institution=institution),
    )

    response = auth_client.delete(reverse("curriculum-entry-detail", args=[entry.public_id]))

    assert response.status_code == 204
    assert not CurriculumPlan.objects.filter(pk=entry.pk).exists()


# --------------------------------------------------------------------------- #
# teaching assignments
# --------------------------------------------------------------------------- #


def test_assign_teacher_returns_201_with_the_teacher_name(auth_client, institution):
    section, subject = _planned_section(institution)
    teacher = PersonFactory(first_name="Ana", last_name="Lopez")

    response = auth_client.post(
        reverse("section-assignment-list-create", args=[section.public_id]),
        {"subject_id": str(subject.public_id), "teacher_id": str(teacher.public_id)},
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["teacher"]["full_name"] == "Ana Lopez"
    assert body["is_open"] is True
    assert body["ends_on"] is None


def test_assigning_a_subject_outside_the_plan_returns_400(auth_client, institution):
    section = SectionFactory(offering=_offering(institution))
    unplanned = SubjectFactory(institution=institution)

    response = auth_client.post(
        reverse("section-assignment-list-create", args=[section.public_id]),
        {"subject_id": str(unplanned.public_id), "teacher_id": str(PersonFactory().public_id)},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "not in the plan" in str(_detail(response))


def test_assigning_an_unknown_teacher_returns_400(auth_client, institution):
    section, subject = _planned_section(institution)

    response = auth_client.post(
        reverse("section-assignment-list-create", args=[section.public_id]),
        {"subject_id": str(subject.public_id), "teacher_id": MISSING_UUID},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "Teacher not found" in str(_detail(response))


def test_a_second_teacher_for_the_same_subject_returns_400(auth_client, institution):
    section, subject = _planned_section(institution)
    payload = {"subject_id": str(subject.public_id), "teacher_id": str(PersonFactory().public_id)}
    auth_client.post(
        reverse("section-assignment-list-create", args=[section.public_id]),
        payload,
        content_type="application/json",
    )

    response = auth_client.post(
        reverse("section-assignment-list-create", args=[section.public_id]),
        {"subject_id": str(subject.public_id), "teacher_id": str(PersonFactory().public_id)},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "already has an assigned teacher" in str(_detail(response))


def test_closing_an_assignment_returns_204_and_keeps_the_row(auth_client, institution):
    section, subject = _planned_section(institution)
    created = auth_client.post(
        reverse("section-assignment-list-create", args=[section.public_id]),
        {"subject_id": str(subject.public_id), "teacher_id": str(PersonFactory().public_id)},
        content_type="application/json",
    ).json()

    response = auth_client.delete(reverse("assignment-detail", args=[created["public_id"]]))

    assert response.status_code == 204
    assert TeachingAssignment.objects.filter(public_id=created["public_id"]).exists()


def test_closed_assignments_only_show_up_when_asked_for(auth_client, institution):
    section, subject = _planned_section(institution)
    url = reverse("section-assignment-list-create", args=[section.public_id])
    created = auth_client.post(
        url,
        {"subject_id": str(subject.public_id), "teacher_id": str(PersonFactory().public_id)},
        content_type="application/json",
    ).json()
    auth_client.delete(reverse("assignment-detail", args=[created["public_id"]]))

    assert _items(auth_client.get(url)) == []
    assert len(_items(auth_client.get(url, {"include_inactive": "true"}))) == 1


def test_closing_an_assignment_on_a_date_returns_the_updated_row(auth_client, institution):
    section, subject = _planned_section(institution)
    created = auth_client.post(
        reverse("section-assignment-list-create", args=[section.public_id]),
        {
            "subject_id": str(subject.public_id),
            "teacher_id": str(PersonFactory().public_id),
            "starts_on": "2026-03-01",
        },
        content_type="application/json",
    ).json()

    response = auth_client.patch(
        reverse("assignment-detail", args=[created["public_id"]]),
        {"ends_on": "2026-06-30"},
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ends_on"] == "2026-06-30"
    assert body["is_open"] is False


def test_an_assignment_cannot_end_before_it_starts(auth_client, institution):
    section, subject = _planned_section(institution)
    created = auth_client.post(
        reverse("section-assignment-list-create", args=[section.public_id]),
        {
            "subject_id": str(subject.public_id),
            "teacher_id": str(PersonFactory().public_id),
            "starts_on": "2026-03-01",
        },
        content_type="application/json",
    ).json()

    response = auth_client.patch(
        reverse("assignment-detail", args=[created["public_id"]]),
        {"ends_on": "2026-02-01"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "cannot end before" in str(_detail(response))


def test_the_section_reports_how_many_subjects_are_covered(auth_client, institution):
    section, subject = _planned_section(institution)
    auth_client.post(
        reverse("section-assignment-list-create", args=[section.public_id]),
        {"subject_id": str(subject.public_id), "teacher_id": str(PersonFactory().public_id)},
        content_type="application/json",
    )

    response = auth_client.get(reverse("section-detail", args=[section.public_id]))

    assert response.status_code == 200
    assert response.json()["assignment_count"] == 1


def test_dates_round_trip_unchanged(auth_client, institution):
    """A regression guard: the cycle dates must not shift by a day in the payload."""
    response = auth_client.post(
        reverse("cycle-list-create"),
        {"name": "Ciclo fechas", "starts_on": STARTS_ON, "ends_on": ENDS_ON},
        content_type="application/json",
    )

    body = response.json()
    assert body["starts_on"] == STARTS_ON
    assert body["ends_on"] == ENDS_ON
    assert AcademicCycle.objects.get(name="Ciclo fechas").starts_on == datetime.date(2026, 1, 15)
