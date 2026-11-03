"""
Grade sheet end to end (V2, V3, V8 of docs/ux-ui.md 2.11): the teacher opens
the sheet, saves a batch, corrects one grade, and the capture-progress panel
and the audit trail reflect it.
"""

import pytest
from django.urls import reverse

from apps.academics.models import CurriculumPlan, TeachingAssignment
from apps.audit.models import AuditEvent
from apps.enrolments.services import create_enrolment
from tests.factories.academic import AcademicCycleFactory, SectionFactory, SubjectFactory
from tests.factories.evaluation import grant_scoped_permission, open_unit
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_sheet_save_correct_and_progress(auth_client, institution):
    user = auth_client.user
    cycle = AcademicCycleFactory(institution=institution)
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=section.grade, subject=subject)
    enrolments = [
        create_enrolment(
            student=StudentFactory(), academic_cycle=cycle, grade=section.grade, section=section
        )
        for _ in range(3)
    ]
    TeachingAssignment.objects.create(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=user.person,
        starts_on=cycle.starts_on,
    )
    grant_scoped_permission(user, "grade_write")
    unit = open_unit(cycle)
    kwargs = {"cycle_public_id": str(cycle.public_id), "unit_public_id": str(unit.public_id)}
    params = {"section_id": str(section.public_id), "subject_id": str(subject.public_id)}

    sheet = auth_client.get(reverse("evaluation-unit-sheet", kwargs=kwargs), params).json()
    assert sheet["teacher"]["public_id"] == str(user.person.public_id)
    assert all(row["grade"] is None for row in sheet["rows"])

    save_url = reverse("evaluation-unit-grades-sheet", kwargs=kwargs)
    first = auth_client.post(
        save_url,
        {
            **params,
            "grades": [
                {"enrolment_id": row["enrolment_id"], "value": 70} for row in sheet["rows"][:2]
            ],
        },
        content_type="application/json",
    )
    assert first.json() == {"created": 2, "updated": 0}

    correction = auth_client.post(
        save_url,
        {**params, "grades": [{"enrolment_id": sheet["rows"][0]["enrolment_id"], "value": 85}]},
        content_type="application/json",
    )
    assert correction.json() == {"created": 0, "updated": 1}
    updated = AuditEvent.objects.get(action="evaluation.grade_updated")
    assert updated.context["changes"] == {"value": {"before": 70, "after": 85}}

    progress = auth_client.get(reverse("evaluation-unit-capture-progress", kwargs=kwargs)).json()
    row = progress["rows"][0]
    assert (row["students_graded"], row["students_pending"]) == (2, 1)
    assert row["teacher"]["public_id"] == str(user.person.public_id)

    reloaded = auth_client.get(reverse("evaluation-unit-sheet", kwargs=kwargs), params).json()
    values = {row["enrolment_id"]: row["grade"] for row in reloaded["rows"]}
    assert values[sheet["rows"][0]["enrolment_id"]]["value"] == 85
    assert len(enrolments) == 3
