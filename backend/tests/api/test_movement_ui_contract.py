from datetime import date

import pytest
from django.urls import reverse

from apps.enrolments import queries
from apps.enrolments.api.serializers import StudentMovementSerializer
from apps.enrolments.models import Enrolment, StudentMovement, StudentMovementAnnulment
from tests.factories.academic import SectionFactory
from tests.factories.identity import UserFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def source_enrolment():
    section = SectionFactory()
    return Enrolment.objects.create(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        effective_on=date(2026, 1, 15),
    )


@pytest.mark.parametrize(
    "kind,supported",
    [
        ("withdrawal", True),
        ("section_change", True),
        ("transfer_in", False),
        ("transfer_out", False),
    ],
)
def test_history_reports_annulment_type_support_from_domain(auth_client, kind, supported):
    source = source_enrolment()
    target = None
    if kind == "section_change":
        section = SectionFactory(academic_cycle=source.academic_cycle, grade=source.grade)
        target = Enrolment.objects.create(
            student=source.student,
            academic_cycle=source.academic_cycle,
            grade=source.grade,
            section=section,
            status="completed",
        )
    if kind == "transfer_in":
        target = source
    movement = StudentMovement.objects.create(
        student=source.student,
        movement_type=kind,
        reason="Synthetic fixture",
        source_enrolment=None if kind == "transfer_in" else source,
        target_enrolment=target,
    )
    body = auth_client.get(
        reverse("student-movement-list"), {"student_id": source.student.public_id}
    ).json()
    assert body["results"][0]["public_id"] == str(movement.public_id)
    assert body["results"][0]["supports_annulment"] is supported
    assert body["results"][0]["annulment"] is None


def test_history_serializes_page_without_per_row_annulment_queries(django_assert_num_queries):
    source = source_enrolment()
    for _ in range(26):
        movement = StudentMovement.objects.create(
            student=source.student,
            movement_type="withdrawal",
            source_enrolment=source,
            reason="Synthetic fixture",
        )
    StudentMovementAnnulment.objects.create(
        movement=movement, annulled_by=UserFactory(), reason="Synthetic correction"
    )
    with django_assert_num_queries(1):
        rows = StudentMovementSerializer(
            queries.student_movements(student=source.student)[:25], many=True
        ).data
    assert len(rows) == 25
    assert all(row["supports_annulment"] is True for row in rows)
    assert sum(row["annulment"] is not None for row in rows) == 1
