"""#632 M1: bounded enrolment summaries, without personal dossiers or N+1."""

from datetime import date

import pytest
from django.urls import reverse

from apps.enrolments.api.serializers import EnrolmentSerializer
from apps.enrolments.models import Enrolment
from apps.enrolments.services import active_enrolments, enrolment_history
from tests.factories.academic import SectionFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def enrolment(**kwargs):
    section = SectionFactory()
    return Enrolment.objects.create(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        effective_on=date(2026, 1, 15),
        **kwargs,
    )


@pytest.mark.parametrize("history", [False, True])
def test_list_has_minimal_summaries_and_legacy_ids(auth_client, history):
    record = enrolment(is_active=not history, status="withdrawn" if history else "active")
    record.student.person.first_name = "Alumno"
    record.student.person.last_name = "Sintetico"
    record.student.person.save()
    route = "enrolment-history-list" if history else "active-enrolment-list"
    response = auth_client.get(reverse(route), {"student_id": str(record.student.public_id)})
    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["student_id"] == str(record.student.public_id)
    assert row["academic_cycle_id"] == str(record.academic_cycle.public_id)
    assert row["grade_id"] == str(record.grade.public_id)
    assert row["section_id"] == str(record.section.public_id)
    assert row["student"] == {
        "public_id": row["student_id"],
        "full_name": "Alumno Sintetico",
        "student_code": record.student.student_code,
    }
    assert row["academic_cycle"] == {
        "public_id": row["academic_cycle_id"],
        "name": record.academic_cycle.name,
    }
    assert row["grade"] == {"public_id": row["grade_id"], "name": record.grade.name}
    assert row["section"] == {
        "public_id": row["section_id"],
        "name": record.section.name,
        "grade_name": record.section.grade.name,
        "shift_name": record.section.shift.name,
    }


@pytest.mark.parametrize("size", [1, 25])
@pytest.mark.parametrize("history", [False, True])
def test_serializing_list_has_constant_query_count(django_assert_num_queries, size, history):
    records = [enrolment() for _ in range(size)]
    if history:
        student = records[0].student
        # Distinct sections preserve enrolment constraints in historical rows.
        Enrolment.objects.filter(pk__in=[item.pk for item in records]).update(
            student=student, is_active=False, status="completed"
        )
        queryset = enrolment_history(student=student)
    else:
        queryset = active_enrolments()
    with django_assert_num_queries(1):
        data = EnrolmentSerializer(queryset[:25], many=True).data
        assert len(data) == size
        assert all(row["student"]["full_name"] and row["section"]["shift_name"] for row in data)


def test_anonymous_cannot_read_summaries(client):
    record = enrolment()
    for route in ("active-enrolment-list", "enrolment-history-list"):
        response = client.get(reverse(route), {"student_id": str(record.student.public_id)})
        assert response.status_code == 403


def test_summaries_keep_historical_inactive_references(auth_client):
    record = enrolment(is_active=False, status="completed")
    record.student.is_active = False
    record.student.save(update_fields=["is_active"])
    record.section.is_active = False
    record.section.save(update_fields=["is_active"])
    response = auth_client.get(
        reverse("enrolment-history-list"), {"student_id": str(record.student.public_id)}
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["student"]["student_code"] == record.student.student_code
    assert response.json()["results"][0]["section"]["name"] == record.section.name
