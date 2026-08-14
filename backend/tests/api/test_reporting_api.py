"""
RF-JOR-007 — contrato de los endpoints de alertas de asistencia.
"""

from datetime import time, timedelta
from urllib.parse import urlencode

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.attendance import services as attendance_services
from apps.enrolments.services import create_enrolment
from apps.reporting.models import Alert
from tests.factories.academic import AcademicCycleFactory, SectionFactory, ShiftFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.reporting import ReportingAlertFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

ALERT_VIEW_PERMISSION = "reporting_alert_view"
ALERT_ACKNOWLEDGE_PERMISSION = "reporting_alert_acknowledge"
ALERT_EVALUATE_PERMISSION = "reporting_alert_evaluate"
THRESHOLD_CONFIGURE_PERMISSION = "reporting_absence_threshold_configure"
STUDENT_VIEW_PERMISSION = "student_view_basic"


def _grant(user, codename):
    permission = PermissionFactory(codename=codename)
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))


def _grant_student_scope(user, student, codename=STUDENT_VIEW_PERMISSION):
    permission = PermissionFactory(codename=codename)
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    return ScopeGrantFactory(assignment=assignment, student=student)


def test_get_alerts_requires_permission_and_returns_paginated_list(auth_client):
    response = auth_client.get(reverse("reporting-alert-list"))
    assert response.status_code == 403

    _grant(auth_client.user, ALERT_VIEW_PERMISSION)
    student = StudentFactory()
    alert = ReportingAlertFactory(student=student)
    _grant_student_scope(auth_client.user, student)

    response = auth_client.get(reverse("reporting-alert-list"))

    assert response.status_code == 200
    alert_ids = {item["public_id"] for item in response.json()["results"]}
    assert str(alert.public_id) in alert_ids


def test_post_acknowledge_sets_acknowledged_by_to_requesting_user(auth_client):
    _grant(auth_client.user, ALERT_ACKNOWLEDGE_PERMISSION)
    student = StudentFactory()
    alert = ReportingAlertFactory(student=student)
    _grant_student_scope(auth_client.user, student)

    response = auth_client.post(
        reverse("reporting-alert-acknowledge", kwargs={"public_id": alert.public_id}),
        {},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["acknowledged_by_username"] == auth_client.user.username
    assert data["acknowledged_at"] is not None


def test_post_acknowledge_is_denied_for_a_student_outside_the_actors_scope(auth_client):
    """
    Holding ``reporting_alert_acknowledge`` must not be enough on its own:
    the alert is about a student, so the actor's student scope decides too,
    exactly as it does for the list endpoint.
    """
    _grant(auth_client.user, ALERT_ACKNOWLEDGE_PERMISSION)
    _grant_student_scope(auth_client.user, StudentFactory())
    foreign_alert = ReportingAlertFactory(student=StudentFactory())

    response = auth_client.post(
        reverse("reporting-alert-acknowledge", kwargs={"public_id": foreign_alert.public_id}),
        {},
        content_type="application/json",
    )

    assert response.status_code == 403
    foreign_alert.refresh_from_db()
    assert foreign_alert.acknowledged_at is None
    assert foreign_alert.acknowledged_by is None


def test_post_alert_evaluations_triggers_evaluation_and_returns_summary(auth_client):
    _grant(auth_client.user, ALERT_EVALUATE_PERMISSION)
    event_date = timezone.localdate()
    cycle = AcademicCycleFactory(starts_on=event_date - timedelta(days=30))
    section = SectionFactory(academic_cycle=cycle)
    shift = section.offering.shift
    student = StudentFactory()
    create_enrolment(
        student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
    )
    attendance_services.set_jornada_parameters(
        shift=shift,
        academic_cycle=cycle,
        entry_limit_time=time(7, 30),
        tolerance_minutes=10,
        closing_time=time(16, 0),
        duplicate_suppression_minutes=5,
        school_days=[1, 2, 3, 4, 5],
        effective_from=cycle.starts_on,
    )

    response = auth_client.post(
        reverse("reporting-alert-evaluations"),
        {"shift_id": str(shift.public_id), "event_date": str(event_date)},
        content_type="application/json",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["shift_id"] == str(shift.public_id)
    assert data["event_date"] == str(event_date)
    assert "absence_alerts" in data
    assert "frequent_absence_alerts" in data


def test_post_absence_threshold_parameters_creates_new_versioned_row(auth_client):
    _grant(auth_client.user, THRESHOLD_CONFIGURE_PERMISSION)
    shift = ShiftFactory()
    cycle = AcademicCycleFactory(institution=shift.institution)

    response = auth_client.post(
        reverse("reporting-absence-threshold-parameters-list"),
        {
            "shift_id": str(shift.public_id),
            "academic_cycle_id": str(cycle.public_id),
            "max_absences": 3,
            "lookback_days": 10,
            "effective_from": str(cycle.starts_on),
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["max_absences"] == 3
    assert data["lookback_days"] == 10
    assert data["shift_id"] == str(shift.public_id)


def test_get_alerts_filters_by_alert_type_and_acknowledged_state(auth_client):
    _grant(auth_client.user, ALERT_VIEW_PERMISSION)
    student = StudentFactory()
    _grant_student_scope(auth_client.user, student)
    matching = ReportingAlertFactory(
        student=student, alert_type=Alert.AlertType.ABSENCE_NOT_REGISTERED
    )
    ReportingAlertFactory(student=student, alert_type=Alert.AlertType.FREQUENT_ABSENCES)

    query = urlencode(
        {"alert_type": Alert.AlertType.ABSENCE_NOT_REGISTERED, "acknowledged": "false"}
    )
    response = auth_client.get(f"{reverse('reporting-alert-list')}?{query}")

    assert response.status_code == 200
    results = response.json()["results"]
    assert {item["public_id"] for item in results} == {str(matching.public_id)}
