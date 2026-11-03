"""
#631, PR 1: contratos HTTP del ciclo escolar.

PATCH del ciclo en borrador (C3), volver a borrador (D3/D6, RF-CIC-008),
preparación (C7) y días no computables (C8, RF-JOR-010).
"""

from datetime import date

import pytest
from django.urls import reverse

from apps.academics.models import AcademicCycle, CurriculumPlan, NonComputableDay
from apps.audit.models import AuditEvent
from apps.enrolments.models import Enrolment
from tests.factories.academic import (
    AcademicCycleFactory,
    GradeOfferingFactory,
    SectionFactory,
    SubjectFactory,
)
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

YEAR = 2031


def _cycle(institution, status, *, year=YEAR):
    return AcademicCycleFactory(
        institution=institution,
        year=year,
        name=f"Ciclo {year}",
        starts_on=date(year, 1, 15),
        ends_on=date(year, 10, 31),
        status=status,
    )


def _grant(user, institution, codename):
    permission = PermissionFactory(codename=codename)
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    return ScopeGrantFactory(assignment=assignment, institution=institution)


def _detail(response):
    return response.json()["error"]["detail"]


# --------------------------------------------------------------------------- #
# C3: PATCH /academics/cycles/<id>/
# --------------------------------------------------------------------------- #


def test_patch_draft_cycle_updates_and_get_still_returns_historical_detail(
    admin_client, institution
):
    cycle = _cycle(institution, AcademicCycle.CycleStatus.DRAFT)
    url = reverse("academic-cycle-historical-detail", args=[cycle.public_id])

    response = admin_client.patch(
        url,
        {"name": "Ciclo lectivo 2031", "ends_on": "2031-10-15", "description": "Ajustado"},
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Ciclo lectivo 2031"
    assert body["ends_on"] == "2031-10-15"
    assert body["status"] == "draft"
    assert AuditEvent.objects.filter(action="academics.cycle.updated").exists()

    detail = admin_client.get(url)
    assert detail.status_code == 200
    assert detail.json()["name"] == "Ciclo lectivo 2031"
    assert "grade_offerings" in detail.json()


def test_patch_active_cycle_is_rejected(admin_client, institution):
    cycle = _cycle(institution, AcademicCycle.CycleStatus.ACTIVE)

    response = admin_client.patch(
        reverse("academic-cycle-historical-detail", args=[cycle.public_id]),
        {"name": "Otro"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "en preparación" in _detail(response)


def test_patch_cycle_requires_assignment_scope(auth_client, institution):
    cycle = _cycle(institution, AcademicCycle.CycleStatus.DRAFT)

    response = auth_client.patch(
        reverse("academic-cycle-historical-detail", args=[cycle.public_id]),
        {"name": "Otro"},
        content_type="application/json",
    )

    assert response.status_code == 403
    cycle.refresh_from_db()
    assert cycle.name == f"Ciclo {YEAR}"


# --------------------------------------------------------------------------- #
# D3/D6: POST /academics/cycles/<id>/revert-to-draft/
# --------------------------------------------------------------------------- #


def test_revert_to_draft_contract(auth_client, institution):
    cycle = _cycle(institution, AcademicCycle.CycleStatus.ACTIVE)
    _grant(auth_client.user, institution, "academic_cycle_revert")

    response = auth_client.post(
        reverse("academic-cycle-revert-to-draft", args=[cycle.public_id]),
        {"reason": "Se activó por error"},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "draft"
    event = AuditEvent.objects.get(action="academics.cycle.reverted_to_draft")
    assert event.context["reason"] == "Se activó por error"


def test_revert_to_draft_rejects_blank_reason(auth_client, institution):
    cycle = _cycle(institution, AcademicCycle.CycleStatus.ACTIVE)
    _grant(auth_client.user, institution, "academic_cycle_revert")

    response = auth_client.post(
        reverse("academic-cycle-revert-to-draft", args=[cycle.public_id]),
        {"reason": "  "},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "motivo" in _detail(response)


def test_revert_to_draft_lists_activity_that_blocks_it(auth_client, institution):
    cycle = _cycle(institution, AcademicCycle.CycleStatus.ACTIVE)
    section = SectionFactory(academic_cycle=cycle)
    Enrolment.objects.create(
        student=StudentFactory(), academic_cycle=cycle, grade=section.grade, section=section
    )
    _grant(auth_client.user, institution, "academic_cycle_revert")

    response = auth_client.post(
        reverse("academic-cycle-revert-to-draft", args=[cycle.public_id]),
        {"reason": "Se activó por error"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "Tiene 1 matrícula." in _detail(response)
    cycle.refresh_from_db()
    assert cycle.status == AcademicCycle.CycleStatus.ACTIVE


# --------------------------------------------------------------------------- #
# C7: GET /academics/cycles/<id>/readiness/
# --------------------------------------------------------------------------- #


def test_readiness_contract_for_draft_cycle(auth_client, institution):
    active = _cycle(institution, AcademicCycle.CycleStatus.ACTIVE)
    draft = _cycle(institution, AcademicCycle.CycleStatus.DRAFT, year=YEAR + 1)
    offering = GradeOfferingFactory(academic_cycle=draft)
    section = SectionFactory(academic_cycle=draft, grade=offering.grade, shift=offering.shift)
    subject = SubjectFactory(institution=institution, name="Matemática")
    CurriculumPlan.objects.create(academic_cycle=draft, grade=offering.grade, subject=subject)

    response = auth_client.get(reverse("academic-cycle-readiness", args=[draft.public_id]))

    assert response.status_code == 200
    body = response.json()
    assert body["active_cycle"] == {"public_id": str(active.public_id), "name": active.name}
    assert body["activation"]["ready"] is False
    first, second = body["activation"]["gaps"]
    assert first["code"] == "active_cycle_exists"
    assert first["grade"] is None
    assert second == {
        "code": "missing_teacher",
        "message": (
            f"Falta asignar docente para 'Matemática' en la sección '{section.name}' "
            f"del grado '{offering.grade.name}'."
        ),
        "grade": {"public_id": str(offering.grade.public_id), "name": offering.grade.name},
        "section": {"public_id": str(section.public_id), "name": section.name},
        "subject": {"public_id": str(subject.public_id), "name": "Matemática"},
    }
    assert body["revert"] == {
        "allowed": False,
        "blockers": [
            {
                "code": "invalid_status",
                "count": None,
                "message": "Solo se puede volver a borrador un ciclo escolar activo.",
            }
        ],
    }
    assert body["close"]["ready"] is False


def test_readiness_contract_for_active_cycle_with_activity(auth_client, institution):
    cycle = _cycle(institution, AcademicCycle.CycleStatus.ACTIVE)
    section = SectionFactory(academic_cycle=cycle)
    for _ in range(3):
        Enrolment.objects.create(
            student=StudentFactory(), academic_cycle=cycle, grade=section.grade, section=section
        )

    body = auth_client.get(reverse("academic-cycle-readiness", args=[cycle.public_id])).json()

    assert body["active_cycle"] is None
    assert body["revert"] == {
        "allowed": False,
        "blockers": [{"code": "enrolments", "count": 3, "message": "Tiene 3 matrículas."}],
    }
    assert body["close"] == {"ready": True, "gaps": []}


def test_readiness_requires_authentication(client, institution):
    cycle = _cycle(institution, AcademicCycle.CycleStatus.DRAFT)

    response = client.get(reverse("academic-cycle-readiness", args=[cycle.public_id]))

    assert response.status_code == 403


def test_readiness_of_unknown_cycle_is_404(auth_client, institution):
    response = auth_client.get(
        reverse("academic-cycle-readiness", args=["00000000-0000-0000-0000-000000000000"])
    )

    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# C8: días no computables
# --------------------------------------------------------------------------- #


def test_non_computable_days_list_create_and_delete(admin_client, institution):
    cycle = _cycle(institution, AcademicCycle.CycleStatus.ACTIVE)
    url = reverse("cycle-non-computable-day-list-create", args=[cycle.public_id])

    created = admin_client.post(
        url, {"day": "2031-09-15", "reason": "Feriado nacional"}, content_type="application/json"
    )
    admin_client.post(
        url, {"day": "2031-05-01", "reason": "Día del trabajo"}, content_type="application/json"
    )

    assert created.status_code == 201
    assert created.json()["day"] == "2031-09-15"
    assert created.json()["academic_cycle_id"] == str(cycle.public_id)

    listing = admin_client.get(url)
    assert listing.status_code == 200
    assert listing.json()["count"] == 2
    assert [row["day"] for row in listing.json()["results"]] == ["2031-05-01", "2031-09-15"]

    deleted = admin_client.delete(
        reverse("non-computable-day-detail", args=[created.json()["public_id"]])
    )
    assert deleted.status_code == 204
    assert [row["day"] for row in admin_client.get(url).json()["results"]] == ["2031-05-01"]
    assert NonComputableDay.objects.filter(public_id=created.json()["public_id"]).exists()
    assert AuditEvent.objects.filter(action="academics.non_computable_day.removed").exists()

    again = admin_client.delete(
        reverse("non-computable-day-detail", args=[created.json()["public_id"]])
    )
    assert again.status_code == 404


def test_non_computable_day_outside_cycle_is_rejected(admin_client, institution):
    cycle = _cycle(institution, AcademicCycle.CycleStatus.ACTIVE)

    response = admin_client.post(
        reverse("cycle-non-computable-day-list-create", args=[cycle.public_id]),
        {"day": "2032-01-05", "reason": "Fuera del ciclo"},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "pertenecer al ciclo escolar" in _detail(response)


def test_non_computable_day_of_closed_cycle_cannot_be_removed(admin_client, institution):
    cycle = _cycle(institution, AcademicCycle.CycleStatus.CLOSED)
    record = NonComputableDay.objects.create(
        academic_cycle=cycle, day=date(YEAR, 3, 2), reason="Asueto"
    )

    response = admin_client.delete(reverse("non-computable-day-detail", args=[record.public_id]))

    assert response.status_code == 400
    record.refresh_from_db()
    assert record.is_active is True


def test_non_computable_day_writes_require_assignment_scope(auth_client, institution):
    cycle = _cycle(institution, AcademicCycle.CycleStatus.ACTIVE)
    record = NonComputableDay.objects.create(
        academic_cycle=cycle, day=date(YEAR, 3, 2), reason="Asueto"
    )
    url = reverse("cycle-non-computable-day-list-create", args=[cycle.public_id])

    assert auth_client.get(url).status_code == 200
    created = auth_client.post(
        url, {"day": "2031-05-01", "reason": "Día del trabajo"}, content_type="application/json"
    )
    deleted = auth_client.delete(reverse("non-computable-day-detail", args=[record.public_id]))

    assert created.status_code == 403
    assert deleted.status_code == 403
    record.refresh_from_db()
    assert record.is_active is True
