"""
Evaluation endpoints that only required a session now deny by default (#631,
#643; docs/development/permisos-en-ui.md).

- Configuration (create unit, recovery window, capture exceptions, global and
  cycle configuration): ``evaluation.configure_units`` over the institution.
- Capture progress: configuration sees every row, a teacher with
  ``grade.write`` only their own assignments, anyone else 403.
- Recovery: eligibility needs ``student.view_basic`` over the student (or the
  section, for the section list); a recovery grade needs ``grade.write`` over
  the section and subarea.
- Grade sheet: ``grade.write`` over the section and subarea (read also with
  configuration); saving always needs ``grade.write``.
"""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import CurriculumPlan, TeachingAssignment
from apps.audit.models import AuditEvent
from apps.enrolments.services import create_enrolment
from apps.evaluation.models import CaptureExceptionGrant, EvaluationUnit, RecoveryGrade
from apps.evaluation.services import register_unit_grade, set_recovery_window
from tests.factories.academic import (
    AcademicCycleFactory,
    InstitutionFactory,
    SectionFactory,
    SubjectFactory,
)
from tests.factories.evaluation import grant_scoped_permission, open_unit
from tests.factories.people import PersonFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.permissions, pytest.mark.django_db]

ATTENDANCE_SERVICE_PATH = "apps.attendance.services.compute_attendance_percentage"
UNIT_PAYLOAD = {
    "number": 1,
    "name": "Unidad 1",
    "starts_on": "2026-01-15",
    "ends_on": "2026-03-15",
    "capture_starts_on": "2026-01-15",
    "capture_ends_on": "2026-03-20",
}


def _configure(user, institution):
    grant_scoped_permission(user, "evaluation_configure_units", institution=institution)


def _unit_kwargs(unit):
    return {
        "cycle_public_id": str(unit.academic_cycle.public_id),
        "unit_public_id": str(unit.public_id),
    }


class TestConfigurationRequiresPermission:
    @pytest.fixture
    def unit(self, institution):
        return open_unit(AcademicCycleFactory(institution=institution))

    def test_create_unit_denied_without_permission(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)

        response = auth_client.post(
            reverse("evaluation-unit-list", kwargs={"cycle_public_id": str(cycle.public_id)}),
            UNIT_PAYLOAD,
            content_type="application/json",
        )

        assert response.status_code == 403
        assert not EvaluationUnit.objects.filter(academic_cycle=cycle).exists()

    def test_create_unit_denied_with_scope_over_another_institution(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)
        _configure(auth_client.user, InstitutionFactory())

        response = auth_client.post(
            reverse("evaluation-unit-list", kwargs={"cycle_public_id": str(cycle.public_id)}),
            UNIT_PAYLOAD,
            content_type="application/json",
        )

        assert response.status_code == 403

    def test_create_unit_allowed_with_permission(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)
        _configure(auth_client.user, institution)

        response = auth_client.post(
            reverse("evaluation-unit-list", kwargs={"cycle_public_id": str(cycle.public_id)}),
            UNIT_PAYLOAD,
            content_type="application/json",
        )

        assert response.status_code == 201
        assert AuditEvent.objects.get(action="evaluation.unit_created").actor_id == (
            auth_client.user.pk
        )

    def test_recovery_window(self, auth_client, institution, unit):
        url = reverse("evaluation-unit-recovery-window", kwargs=_unit_kwargs(unit))
        body = {"recovery_starts_on": "2026-04-01", "recovery_ends_on": "2026-04-05"}

        denied = auth_client.patch(url, body, content_type="application/json")
        _configure(auth_client.user, institution)
        allowed = auth_client.patch(url, body, content_type="application/json")

        assert denied.status_code == 403
        assert allowed.status_code == 200

    def test_capture_exceptions_list_and_grant(self, auth_client, institution, unit):
        url = reverse("evaluation-unit-capture-exceptions", kwargs=_unit_kwargs(unit))
        body = {
            "subject": str(SubjectFactory(institution=institution).public_id),
            "teacher": str(PersonFactory().public_id),
            "reason": "Falla de conectividad.",
            "expires_at": (timezone.now() + timedelta(days=1)).isoformat(),
        }

        denied_list = auth_client.get(url)
        denied_grant = auth_client.post(url, body, content_type="application/json")
        _configure(auth_client.user, institution)
        allowed_grant = auth_client.post(url, body, content_type="application/json")
        allowed_list = auth_client.get(url)

        assert denied_list.status_code == 403
        assert denied_grant.status_code == 403
        assert allowed_grant.status_code == 201
        assert allowed_list.status_code == 200
        assert CaptureExceptionGrant.objects.count() == 1

    def test_global_config(self, auth_client, institution):
        url = reverse("evaluation-global-config")

        reading = auth_client.get(url)
        denied = auth_client.patch(url, {"default_unit_count": 5}, content_type="application/json")
        _configure(auth_client.user, institution)
        allowed = auth_client.patch(url, {"default_unit_count": 5}, content_type="application/json")

        assert reading.status_code == 200
        assert denied.status_code == 403
        assert allowed.status_code == 200
        assert allowed.json()["default_unit_count"] == 5

    def test_cycle_config(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)
        url = reverse("cycle-evaluation-config", kwargs={"cycle_public_id": str(cycle.public_id)})

        reading = auth_client.get(url)
        denied = auth_client.patch(url, {"unit_count": 3}, content_type="application/json")
        _configure(auth_client.user, institution)
        allowed = auth_client.patch(url, {"unit_count": 3}, content_type="application/json")

        assert reading.status_code == 200
        assert denied.status_code == 403
        assert allowed.status_code == 200


def _two_section_world(institution, teacher_person):
    """Two sections of one grade, one subarea; ``teacher_person`` teaches only the first."""
    cycle = AcademicCycleFactory(institution=institution)
    first = SectionFactory(academic_cycle=cycle)
    second = SectionFactory(academic_cycle=cycle, grade=first.grade)
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=first.grade, subject=subject)
    for section in (first, second):
        create_enrolment(
            student=StudentFactory(), academic_cycle=cycle, grade=section.grade, section=section
        )
    TeachingAssignment.objects.create(
        academic_cycle=cycle,
        section=first,
        subject=subject,
        teacher=teacher_person,
        starts_on=cycle.starts_on,
    )
    return SimpleNamespace(
        cycle=cycle, first=first, second=second, subject=subject, unit=open_unit(cycle)
    )


class TestCaptureProgressPermission:
    def _get(self, client, world):
        return client.get(
            reverse("evaluation-unit-capture-progress", kwargs=_unit_kwargs(world.unit))
        )

    def test_denied_without_permission(self, auth_client, institution):
        world = _two_section_world(institution, PersonFactory())

        assert self._get(auth_client, world).status_code == 403

    def test_teacher_sees_only_their_rows(self, auth_client, institution):
        world = _two_section_world(institution, auth_client.user.person)
        grant_scoped_permission(auth_client.user, "grade_write")

        response = self._get(auth_client, world)

        assert response.status_code == 200
        rows = response.json()["rows"]
        assert [row["section"]["public_id"] for row in rows] == [str(world.first.public_id)]

    def test_grade_write_without_assignment_in_cycle_is_denied(self, auth_client, institution):
        world = _two_section_world(institution, PersonFactory())
        grant_scoped_permission(auth_client.user, "grade_write")

        assert self._get(auth_client, world).status_code == 403

    def test_configuration_sees_every_row(self, auth_client, institution):
        world = _two_section_world(institution, PersonFactory())
        _configure(auth_client.user, institution)

        response = self._get(auth_client, world)

        assert response.status_code == 200
        assert len(response.json()["rows"]) == 2


class TestGradeSheetPermission:
    def _params(self, world, section):
        return {"section_id": str(section.public_id), "subject_id": str(world.subject.public_id)}

    def test_teacher_of_another_section_is_denied_and_audited(self, auth_client, institution):
        world = _two_section_world(institution, auth_client.user.person)
        grant_scoped_permission(auth_client.user, "grade_write")

        response = auth_client.get(
            reverse("evaluation-unit-sheet", kwargs=_unit_kwargs(world.unit)),
            self._params(world, world.second),
        )

        assert response.status_code == 403
        assert AuditEvent.objects.filter(action="evaluation.grade_write_denied").exists()

    def test_configuration_reads_but_cannot_save(self, auth_client, institution):
        world = _two_section_world(institution, PersonFactory())
        _configure(auth_client.user, institution)

        read = auth_client.get(
            reverse("evaluation-unit-sheet", kwargs=_unit_kwargs(world.unit)),
            self._params(world, world.first),
        )
        save = auth_client.post(
            reverse("evaluation-unit-grades-sheet", kwargs=_unit_kwargs(world.unit)),
            {**self._params(world, world.first), "grades": [{"student_code": "X", "value": 70}]},
            content_type="application/json",
        )

        assert read.status_code == 200
        assert save.status_code == 403


class TestRecoveryPermissions:
    def _world(self, institution):
        cycle = AcademicCycleFactory(institution=institution)
        section = SectionFactory(academic_cycle=cycle)
        enrolment = create_enrolment(
            student=StudentFactory(), academic_cycle=cycle, grade=section.grade, section=section
        )
        subject = SubjectFactory(institution=institution)
        CurriculumPlan.objects.create(academic_cycle=cycle, grade=section.grade, subject=subject)
        unit = open_unit(cycle)
        register_unit_grade(
            enrolment=enrolment,
            subject=subject,
            evaluation_unit=unit,
            teacher=PersonFactory(),
            value=40,
        )
        today = timezone.localdate()
        set_recovery_window(unit, today - timedelta(days=1), today + timedelta(days=1))
        return SimpleNamespace(cycle=cycle, section=section, enrolment=enrolment, subject=subject)

    def _eligibility_url(self, world):
        return reverse(
            "recovery-eligibility",
            kwargs={
                "cycle_public_id": str(world.cycle.public_id),
                "enrolment_id": str(world.enrolment.public_id),
            },
        )

    def _section_url(self, world):
        return reverse(
            "section-recovery-eligibility",
            kwargs={
                "cycle_public_id": str(world.cycle.public_id),
                "section_id": str(world.section.public_id),
            },
        )

    def _grade_url(self, world):
        return reverse(
            "recovery-grade-create",
            kwargs={
                "cycle_public_id": str(world.cycle.public_id),
                "enrolment_id": str(world.enrolment.public_id),
            },
        )

    def test_eligibility_reads_need_student_view(self, auth_client, institution):
        world = self._world(institution)

        with patch(ATTENDANCE_SERVICE_PATH, return_value=SimpleNamespace(percentage=90.0)):
            denied_one = auth_client.get(self._eligibility_url(world))
            denied_section = auth_client.get(self._section_url(world))
            grant_scoped_permission(auth_client.user, "student_view_basic", institution=institution)
            allowed_one = auth_client.get(self._eligibility_url(world))
            allowed_section = auth_client.get(self._section_url(world))

        assert denied_one.status_code == 403
        assert denied_section.status_code == 403
        assert allowed_one.status_code == 200
        assert allowed_section.status_code == 200
        assert allowed_section.json()["count"] == 1

    def test_section_list_denied_with_scope_over_another_institution(
        self, auth_client, institution
    ):
        world = self._world(institution)
        grant_scoped_permission(
            auth_client.user, "student_view_basic", institution=InstitutionFactory()
        )

        assert auth_client.get(self._section_url(world)).status_code == 403

    def test_recovery_grade_needs_grade_write(self, auth_client, institution):
        world = self._world(institution)
        body = {"subject": str(world.subject.public_id), "value": 70}

        with patch(ATTENDANCE_SERVICE_PATH, return_value=SimpleNamespace(percentage=90.0)):
            denied = auth_client.post(self._grade_url(world), body, content_type="application/json")
            grant_scoped_permission(auth_client.user, "grade_write", section=world.section)
            allowed = auth_client.post(
                self._grade_url(world), body, content_type="application/json"
            )

        assert denied.status_code == 403
        assert AuditEvent.objects.filter(
            action="evaluation.grade_write_denied", context__recovery=True
        ).exists()
        assert allowed.status_code == 201, allowed.json()
        assert RecoveryGrade.objects.count() == 1
