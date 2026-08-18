"""
API contract tests for evaluation units.

RF-EVC-001: Estructura de unidades del ciclo
RF-EVC-002: Ventana de captura de notas
RF-EVC-003: Ventana de recuperacion
RF-EVC-004: Brecha excepcional autorizada
RF-EVC-005: Configuracion global heredable

Scenario 1: Configuración de cuatro unidades
Scenario 2: Unidades solapadas
Scenario 3: Captura dentro de la ventana
Scenario 4: Captura con la ventana cerrada
Scenario 5: Recuperación fuera de fecha
Scenario 6: Docente que no alcanzó a subir notas
Scenario 7: Expiración automática
Scenario 8: Ciclo que se aparta del valor global
"""

from datetime import date, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import TeachingAssignment
from apps.enrolments.services import create_enrolment
from apps.evaluation.models import CaptureExceptionGrant, EvaluationUnit, Grade
from tests.factories.academic import AcademicCycleFactory, SectionFactory, SubjectFactory
from tests.factories.evaluation import EvaluationUnitFactory
from tests.factories.identity import PermissionFactory, RoleAssignmentFactory, RoleFactory
from tests.factories.people import PersonFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def _grant_grade_write(user, *, section, subject, academic_cycle):
    """
    Give ``user`` the grade_write permission and a teaching assignment over
    ``section``/``subject``, matching RF-CAL-006's docente scope.
    """
    permission = PermissionFactory(codename="grade_write")
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    TeachingAssignment.objects.create(
        academic_cycle=academic_cycle,
        section=section,
        subject=subject,
        teacher=user.person,
        starts_on=academic_cycle.starts_on,
    )


class TestEvaluationUnitAPI:
    """Tests for evaluation unit REST endpoints."""

    def test_create_evaluation_unit_success(self, auth_client, institution):
        """
        POST /api/v1/academics/cycles/{cycle_id}/evaluation-units/
        GIVEN un ciclo escolar sin unidades configuradas
        WHEN un usuario autorizado define una unidad con sus fechas
        THEN el sistema responde 201 con los datos registrados
        """
        cycle = AcademicCycleFactory(
            institution=institution,
            starts_on=date(2026, 1, 15),
            ends_on=date(2026, 10, 31),
        )

        response = auth_client.post(
            reverse(
                "evaluation-unit-list",
                kwargs={"cycle_public_id": str(cycle.public_id)},
            ),
            {
                "number": 1,
                "name": "Unit 1",
                "starts_on": "2026-01-15",
                "ends_on": "2026-03-15",
                "capture_starts_on": "2026-01-01",
                "capture_ends_on": "2026-04-30",
                "status": "open",
            },
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["number"] == 1
        assert data["name"] == "Unit 1"
        assert data["status"] == EvaluationUnit.UnitStatus.OPEN
        assert data["starts_on"] == "2026-01-15"
        assert data["ends_on"] == "2026-03-15"
        assert data["capture_starts_on"] == "2026-01-01"
        assert data["capture_ends_on"] == "2026-04-30"

    def test_create_multiple_units_in_same_cycle(self, auth_client, institution):
        """
        Scenario 1: Create four units successfully
        """
        cycle = AcademicCycleFactory(
            institution=institution,
            starts_on=date(2026, 1, 15),
            ends_on=date(2026, 10, 31),
        )

        base_url = reverse(
            "evaluation-unit-list",
            kwargs={"cycle_public_id": str(cycle.public_id)},
        )

        for i in range(1, 5):
            response = auth_client.post(
                base_url,
                {
                    "number": i,
                    "name": f"Unit {i}",
                    "starts_on": f"2026-{1 + (i - 1) * 2:02d}-01",
                    "ends_on": f"2026-{2 + (i - 1) * 2:02d}-28",
                    "capture_starts_on": f"2026-{1 + (i - 1) * 2:02d}-01",
                    "capture_ends_on": f"2026-{2 + (i - 1) * 2:02d}-28",
                    "status": "open",
                },
                content_type="application/json",
            )
            assert response.status_code == 201, f"Failed to create unit {i}: {response.json()}"

        # Verify all units exist
        units = EvaluationUnit.objects.filter(academic_cycle=cycle)
        assert units.count() == 4
        assert list(units.values_list("number", flat=True)) == [1, 2, 3, 4]

    def test_reject_overlapping_dates_api(self, auth_client, institution):
        """
        Scenario 2: Unidades solapadas
        GIVEN un ciclo con una unidad ya configurada
        WHEN se intenta crear otra cuyo rango de fechas se solapa
        THEN el sistema responde 400 con detalle del conflicto
        """
        cycle = AcademicCycleFactory(
            institution=institution,
            starts_on=date(2026, 1, 15),
            ends_on=date(2026, 10, 31),
        )

        base_url = reverse(
            "evaluation-unit-list",
            kwargs={"cycle_public_id": str(cycle.public_id)},
        )

        # Create first unit
        response = auth_client.post(
            base_url,
            {
                "number": 1,
                "name": "Unit 1",
                "starts_on": "2026-01-01",
                "ends_on": "2026-02-28",
                "capture_starts_on": "2026-01-01",
                "capture_ends_on": "2026-02-28",
                "status": "open",
            },
            content_type="application/json",
        )
        assert response.status_code == 201

        # Try to create overlapping unit
        response = auth_client.post(
            base_url,
            {
                "number": 2,
                "name": "Unit 2",
                "starts_on": "2026-02-01",  # overlaps with unit 1
                "ends_on": "2026-03-31",
                "capture_starts_on": "2026-02-01",
                "capture_ends_on": "2026-03-31",
                "status": "open",
            },
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "overlap" in response.json()["error"].lower()

    def test_reject_invalid_date_range_api(self, auth_client, institution):
        """
        Test end_date before start_date rejected.
        """
        cycle = AcademicCycleFactory(institution=institution)
        base_url = reverse(
            "evaluation-unit-list",
            kwargs={"cycle_public_id": str(cycle.public_id)},
        )

        response = auth_client.post(
            base_url,
            {
                "number": 1,
                "name": "Unit 1",
                "starts_on": "2026-03-01",
                "ends_on": "2026-01-01",  # invalid
                "capture_starts_on": "2026-01-01",
                "capture_ends_on": "2026-04-01",
                "status": "open",
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        payload = response.json()
        if payload.get("ends_on"):
            assert "end" in payload["ends_on"][0].lower()

    def test_list_units_by_cycle(self, auth_client, institution):
        """
        GET /api/v1/academics/cycles/{cycle_id}/evaluation-units/
        """
        cycle = AcademicCycleFactory(institution=institution)

        # Create some units
        from tests.factories.evaluation import EvaluationUnitFactory

        for i in range(1, 4):
            EvaluationUnitFactory(academic_cycle=cycle, number=i)

        response = auth_client.get(
            reverse(
                "evaluation-unit-list",
                kwargs={"cycle_public_id": str(cycle.public_id)},
            )
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 3
        assert [u["number"] for u in data["results"]] == [1, 2, 3]

    def test_cycle_not_found_returns_404(self, auth_client):
        """
        Test endpoint with invalid cycle ID.
        """
        import uuid

        response = auth_client.post(
            reverse(
                "evaluation-unit-list",
                kwargs={"cycle_public_id": str(uuid.uuid4())},
            ),
            {
                "number": 1,
                "name": "Unit 1",
                "starts_on": "2026-01-01",
                "ends_on": "2026-02-28",
                "capture_starts_on": "2026-01-01",
                "capture_ends_on": "2026-02-28",
            },
            content_type="application/json",
        )

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()


class TestRecoveryWindowAPI:
    """Tests for PATCH recovery-window endpoint (RF-EVC-003)."""

    def test_set_recovery_window_success(self, auth_client, institution):
        """
        PATCH /api/v1/academics/cycles/{cycle_id}/evaluation-units/{unit_id}/recovery-window/
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = EvaluationUnitFactory(academic_cycle=cycle, number=1)

        response = auth_client.patch(
            reverse(
                "evaluation-unit-recovery-window",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "recovery_starts_on": "2026-03-10",
                "recovery_ends_on": "2026-03-20",
            },
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["recovery_starts_on"] == "2026-03-10"
        assert data["recovery_ends_on"] == "2026-03-20"

    def test_reject_invalid_recovery_date_range_api(self, auth_client, institution):
        """
        Test that recovery end date before start date is rejected.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = EvaluationUnitFactory(academic_cycle=cycle, number=1)

        response = auth_client.patch(
            reverse(
                "evaluation-unit-recovery-window",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "recovery_starts_on": "2026-03-20",
                "recovery_ends_on": "2026-03-10",
            },
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_unit_not_found_returns_404(self, auth_client, institution):
        """
        Test endpoint with invalid unit ID.
        """
        import uuid

        cycle = AcademicCycleFactory(institution=institution)

        response = auth_client.patch(
            reverse(
                "evaluation-unit-recovery-window",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(uuid.uuid4()),
                },
            ),
            {
                "recovery_starts_on": "2026-03-10",
                "recovery_ends_on": "2026-03-20",
            },
            content_type="application/json",
        )

        assert response.status_code == 404


class TestCaptureExceptionGrantAPI:
    """Tests for POST capture-exceptions endpoint (RF-EVC-004)."""

    def test_grant_capture_exception_success(self, auth_client, institution):
        """
        Scenario 6: Docente que no alcanzó a subir notas
        POST /api/v1/academics/cycles/{cycle_id}/evaluation-units/{unit_id}/capture-exceptions/
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = EvaluationUnitFactory(academic_cycle=cycle, number=1)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        expires_at = timezone.now() + timedelta(days=1)

        response = auth_client.post(
            reverse(
                "evaluation-unit-capture-exceptions",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "subject": subject.id,
                "teacher": teacher.id,
                "reason": "No alcanzó a subir notas por falla eléctrica.",
                "expires_at": expires_at.isoformat(),
            },
            content_type="application/json",
        )

        assert response.status_code == 201, response.json()
        data = response.json()
        assert data["reason"] == "No alcanzó a subir notas por falla eléctrica."
        assert CaptureExceptionGrant.objects.filter(
            evaluation_unit=unit, subject=subject, teacher=teacher
        ).exists()

    def test_reject_empty_reason_api(self, auth_client, institution):
        """
        Test that granting an exception without a reason is rejected.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = EvaluationUnitFactory(academic_cycle=cycle, number=1)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()

        response = auth_client.post(
            reverse(
                "evaluation-unit-capture-exceptions",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "subject": subject.id,
                "teacher": teacher.id,
                "reason": "   ",
                "expires_at": (timezone.now() + timedelta(days=1)).isoformat(),
            },
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_unit_not_found_returns_404_for_grant(self, auth_client, institution):
        """
        Test endpoint with invalid unit ID.
        """
        import uuid

        cycle = AcademicCycleFactory(institution=institution)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()

        response = auth_client.post(
            reverse(
                "evaluation-unit-capture-exceptions",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(uuid.uuid4()),
                },
            ),
            {
                "subject": subject.id,
                "teacher": teacher.id,
                "reason": "Motivo válido.",
                "expires_at": (timezone.now() + timedelta(days=1)).isoformat(),
            },
            content_type="application/json",
        )

        assert response.status_code == 404


class TestEvaluationConfigAPI:
    """Tests for global/cycle evaluation configuration endpoints (RF-EVC-005)."""

    def test_cycle_departs_from_global_value_api(self, auth_client, institution):
        """
        Scenario 8: Ciclo que se aparta del valor global
        """
        # Set the global default.
        response = auth_client.patch(
            reverse("evaluation-global-config"),
            {"default_unit_count": 4},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["default_unit_count"] == 4

        cycle_a = AcademicCycleFactory(
            institution=institution,
            year=2030,
            starts_on=date(2030, 1, 1),
            ends_on=date(2030, 12, 31),
            status="draft",
        )
        cycle_b = AcademicCycleFactory(
            institution=institution,
            year=2031,
            starts_on=date(2031, 1, 1),
            ends_on=date(2031, 12, 31),
            status="draft",
        )

        # Before any override, both cycles inherit the global default.
        for cycle in (cycle_a, cycle_b):
            response = auth_client.get(
                reverse("cycle-evaluation-config", kwargs={"cycle_public_id": str(cycle.public_id)})
            )
            assert response.status_code == 200
            assert response.json()["unit_count"] is None
            assert response.json()["effective_unit_count"] == 4

        # Cycle A departs from the global value.
        response = auth_client.patch(
            reverse("cycle-evaluation-config", kwargs={"cycle_public_id": str(cycle_a.public_id)}),
            {"unit_count": 3},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["unit_count"] == 3
        assert response.json()["effective_unit_count"] == 3

        # Cycle B and the global config remain unchanged.
        response = auth_client.get(
            reverse("cycle-evaluation-config", kwargs={"cycle_public_id": str(cycle_b.public_id)})
        )
        assert response.json()["unit_count"] is None
        assert response.json()["effective_unit_count"] == 4

        response = auth_client.get(reverse("evaluation-global-config"))
        assert response.json()["default_unit_count"] == 4

    def test_reject_non_positive_global_unit_count_api(self, auth_client):
        """
        Test that a non-positive default_unit_count is rejected.
        """
        response = auth_client.patch(
            reverse("evaluation-global-config"),
            {"default_unit_count": 0},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_cycle_config_not_found_returns_404(self, auth_client):
        """
        Test endpoint with invalid cycle ID.
        """
        import uuid

        response = auth_client.get(
            reverse("cycle-evaluation-config", kwargs={"cycle_public_id": str(uuid.uuid4())})
        )
        assert response.status_code == 404


class TestGradeAPI:
    """Tests for RF-CAL-001: Registro de la nota de unidad."""

    def _enrolment(self, cycle):
        section = SectionFactory(academic_cycle=cycle)
        student = StudentFactory()
        return create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )

    def _open_unit(self, cycle):
        """
        A unit whose capture window brackets today explicitly. The factory's
        default dates are offset by ``number``, a sequence shared across the
        whole test session, so they drift away from today as more units are
        created; the window bounds must be set explicitly here.
        """
        today = timezone.localdate()
        return EvaluationUnitFactory(
            academic_cycle=cycle,
            capture_starts_on=today - timedelta(days=5),
            capture_ends_on=today + timedelta(days=5),
        )

    def test_register_grade_success(self, auth_client, institution):
        """
        Scenario 9: Registro de una nota por el docente
        POST /api/v1/academics/cycles/{cycle_id}/evaluation-units/{unit_id}/grades/
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.id,
                "subject": subject.id,
                "teacher": teacher.id,
                "value": 85,
            },
            content_type="application/json",
        )

        assert response.status_code == 201, response.json()
        data = response.json()
        assert data["value"] == 85
        assert data["subject"] == subject.id
        assert Grade.objects.filter(
            enrolment=enrolment, subject=subject, evaluation_unit=unit
        ).exists()

    def test_register_grade_again_updates_existing_row(self, auth_client, institution):
        """
        Test that posting the same (enrolment, subject, unit) again updates
        the existing grade instead of creating a duplicate.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )

        url = reverse(
            "evaluation-unit-grades",
            kwargs={
                "cycle_public_id": str(cycle.public_id),
                "unit_public_id": str(unit.public_id),
            },
        )
        payload = {
            "enrolment": enrolment.id,
            "subject": subject.id,
            "teacher": teacher.id,
            "value": 70,
        }
        first = auth_client.post(url, payload, content_type="application/json")
        assert first.status_code == 201

        payload["value"] = 90
        second = auth_client.post(url, payload, content_type="application/json")
        assert second.status_code == 201
        assert second.json()["value"] == 90
        assert (
            Grade.objects.filter(enrolment=enrolment, subject=subject, evaluation_unit=unit).count()
            == 1
        )

    def test_reject_grade_when_capture_window_closed_api(self, auth_client, institution):
        """
        Test that a grade is rejected via the API when the capture window is closed.
        """
        cycle = AcademicCycleFactory(institution=institution)
        yesterday = timezone.localdate() - timedelta(days=1)
        unit = EvaluationUnitFactory(
            academic_cycle=cycle,
            starts_on=yesterday - timedelta(days=30),
            ends_on=yesterday,
            capture_starts_on=yesterday - timedelta(days=30),
            capture_ends_on=yesterday,
        )
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.id,
                "subject": subject.id,
                "teacher": teacher.id,
                "value": 85,
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "closed" in response.json()["error"].lower()

    def test_list_grades_by_unit(self, auth_client, institution):
        """
        GET /api/v1/academics/cycles/{cycle_id}/evaluation-units/{unit_id}/grades/
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = EvaluationUnitFactory(academic_cycle=cycle)
        subject = SubjectFactory(institution=institution)
        for _ in range(3):
            enrolment = self._enrolment(cycle)
            Grade.objects.create(
                enrolment=enrolment, subject=subject, evaluation_unit=unit, value=80
            )

        response = auth_client.get(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            )
        )

        assert response.status_code == 200
        assert len(response.json()["results"]) == 3

    def test_unit_not_found_returns_404_for_grade(self, auth_client, institution):
        """
        Test endpoint with invalid unit ID.
        """
        import uuid

        cycle = AcademicCycleFactory(institution=institution)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(uuid.uuid4()),
                },
            ),
            {
                "enrolment": enrolment.id,
                "subject": subject.id,
                "teacher": teacher.id,
                "value": 85,
            },
            content_type="application/json",
        )

        assert response.status_code == 404


class TestGradeAuthorizationAPI:
    """Tests for RF-CAL-006: Alcance del docente sobre las notas."""

    def _enrolment(self, cycle):
        section = SectionFactory(academic_cycle=cycle)
        student = StudentFactory()
        return create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )

    def _open_unit(self, cycle):
        today = timezone.localdate()
        return EvaluationUnitFactory(
            academic_cycle=cycle,
            capture_starts_on=today - timedelta(days=5),
            capture_ends_on=today + timedelta(days=5),
        )

    def test_reject_grade_write_for_subarea_ajena(self, auth_client, institution):
        """
        Scenario 12: Subárea ajena
        GIVEN un docente sin asignación sobre una subárea
        WHEN intenta registrar una nota de esa subárea
        THEN el sistema deniega la operación
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        # auth_client.user has the atomic permission but no TeachingAssignment
        # over this section/subject: an ajena subárea.
        permission = PermissionFactory(codename="grade_write")
        RoleAssignmentFactory(user=auth_client.user, role=RoleFactory(permissions=[permission]))

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.id,
                "subject": subject.id,
                "teacher": teacher.id,
                "value": 85,
            },
            content_type="application/json",
        )

        assert response.status_code == 403
        assert not Grade.objects.filter(
            enrolment=enrolment, subject=subject, evaluation_unit=unit
        ).exists()

    def test_reject_grade_write_without_atomic_permission(self, auth_client, institution):
        """
        Test that a teacher with a matching assignment but no grade_write
        permission at all is still denied: scope alone is not enough.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        TeachingAssignment.objects.create(
            academic_cycle=cycle,
            section=enrolment.section,
            subject=subject,
            teacher=auth_client.user.person,
            starts_on=cycle.starts_on,
        )

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.id,
                "subject": subject.id,
                "teacher": teacher.id,
                "value": 85,
            },
            content_type="application/json",
        )

        assert response.status_code == 403

    def test_grade_write_denial_is_audited(self, auth_client, institution):
        """
        Test that a denied grade write is recorded in the audit trail
        (RF-CAL-006 touches the sensitive identity-access domain).
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        permission = PermissionFactory(codename="grade_write")
        RoleAssignmentFactory(user=auth_client.user, role=RoleFactory(permissions=[permission]))

        auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.id,
                "subject": subject.id,
                "teacher": teacher.id,
                "value": 85,
            },
            content_type="application/json",
        )

        from apps.audit.models import AuditEvent

        event = AuditEvent.objects.get(action="evaluation.grade_write_denied")
        assert event.context["enrolment_id"] == str(enrolment.public_id)
        assert event.context["subject_id"] == str(subject.public_id)

    def test_accept_grade_write_with_matching_assignment(self, auth_client, institution):
        """
        Test that a teacher with a matching TeachingAssignment and the
        grade_write permission can register the grade.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.id,
                "subject": subject.id,
                "teacher": teacher.id,
                "value": 85,
            },
            content_type="application/json",
        )

        assert response.status_code == 201, response.json()

    def test_teacher_grade_list_scoped_to_own_assignment(self, auth_client, institution):
        """
        Test that a teacher listing grades for a unit only sees the ones for
        sections/subjects they are assigned to.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        own_subject = SubjectFactory(institution=institution)
        other_subject = SubjectFactory(institution=institution)
        own_enrolment = self._enrolment(cycle)
        other_enrolment = self._enrolment(cycle)
        Grade.objects.create(
            enrolment=own_enrolment, subject=own_subject, evaluation_unit=unit, value=80
        )
        Grade.objects.create(
            enrolment=other_enrolment, subject=other_subject, evaluation_unit=unit, value=90
        )
        TeachingAssignment.objects.create(
            academic_cycle=cycle,
            section=own_enrolment.section,
            subject=own_subject,
            teacher=auth_client.user.person,
            starts_on=cycle.starts_on,
        )

        response = auth_client.get(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            )
        )

        assert response.status_code == 200
        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["subject"] == own_subject.id


class TestGradeScaleAPI:
    """Tests for RF-CAL-002: Escala y validación de la nota."""

    def _enrolment(self, cycle):
        section = SectionFactory(academic_cycle=cycle)
        student = StudentFactory()
        return create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )

    def _open_unit(self, cycle):
        today = timezone.localdate()
        return EvaluationUnitFactory(
            academic_cycle=cycle,
            capture_starts_on=today - timedelta(days=5),
            capture_ends_on=today + timedelta(days=5),
        )

    def test_reject_value_above_scale_api(self, auth_client, institution):
        """
        Scenario 10: Nota fuera de rango
        GIVEN un docente registrando notas
        WHEN introduce un valor superior a cien
        THEN el sistema rechaza el valor indicando el rango admitido
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.id,
                "subject": subject.id,
                "teacher": teacher.id,
                "value": 101,
            },
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "0 and 100" in response.json()["value"][0]

    def test_reject_negative_value_api(self, auth_client, institution):
        """
        Test that a negative value is rejected via the API.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.id,
                "subject": subject.id,
                "teacher": teacher.id,
                "value": -1,
            },
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_reject_non_numeric_value_api(self, auth_client, institution):
        """
        Test that a non-numeric value is rejected via the API.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()

        response = auth_client.post(
            reverse(
                "evaluation-unit-grades",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "unit_public_id": str(unit.public_id),
                },
            ),
            {
                "enrolment": enrolment.id,
                "subject": subject.id,
                "teacher": teacher.id,
                "value": "not-a-number",
            },
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_accept_boundary_values_api(self, auth_client, institution):
        """
        Test that the scale boundaries (0 and 100) are accepted via the API.
        """
        cycle = AcademicCycleFactory(institution=institution)
        unit = self._open_unit(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        url = reverse(
            "evaluation-unit-grades",
            kwargs={
                "cycle_public_id": str(cycle.public_id),
                "unit_public_id": str(unit.public_id),
            },
        )

        for value in (0, 100):
            enrolment = self._enrolment(cycle)
            _grant_grade_write(
                auth_client.user,
                section=enrolment.section,
                subject=subject,
                academic_cycle=cycle,
            )
            response = auth_client.post(
                url,
                {
                    "enrolment": enrolment.id,
                    "subject": subject.id,
                    "teacher": teacher.id,
                    "value": value,
                },
                content_type="application/json",
            )
            assert response.status_code == 201, response.json()
            assert response.json()["value"] == value


class TestCurrentAverageAPI:
    """Tests for RF-CAL-003: Distinción entre sin calificar y cero."""

    def _enrolment(self, cycle):
        section = SectionFactory(academic_cycle=cycle)
        student = StudentFactory()
        return create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )

    def _units(self, cycle, count):
        today = timezone.localdate()
        units = []
        for i in range(count):
            starts = today + timedelta(days=i * 70)
            units.append(
                EvaluationUnitFactory(
                    academic_cycle=cycle,
                    number=i + 1,
                    starts_on=starts,
                    ends_on=starts + timedelta(days=60),
                    capture_starts_on=today - timedelta(days=5),
                    capture_ends_on=today + timedelta(days=5),
                )
            )
        return units

    def test_current_average_excludes_pending_units_api(self, auth_client, institution):
        """
        Scenario 11: Promedio en curso con notas pendientes
        GET {cycle}/enrolments/{enrolment_id}/subjects/{subject_id}/current-average/
        """
        cycle = AcademicCycleFactory(institution=institution)
        units = self._units(cycle, 4)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)
        teacher = PersonFactory()
        _grant_grade_write(
            auth_client.user, section=enrolment.section, subject=subject, academic_cycle=cycle
        )

        grades_url = reverse(
            "evaluation-unit-grades",
            kwargs={
                "cycle_public_id": str(cycle.public_id),
                "unit_public_id": str(units[0].public_id),
            },
        )
        auth_client.post(
            grades_url,
            {
                "enrolment": enrolment.id,
                "subject": subject.id,
                "teacher": teacher.id,
                "value": 80,
            },
            content_type="application/json",
        )
        grades_url = reverse(
            "evaluation-unit-grades",
            kwargs={
                "cycle_public_id": str(cycle.public_id),
                "unit_public_id": str(units[1].public_id),
            },
        )
        auth_client.post(
            grades_url,
            {
                "enrolment": enrolment.id,
                "subject": subject.id,
                "teacher": teacher.id,
                "value": 90,
            },
            content_type="application/json",
        )

        response = auth_client.get(
            reverse(
                "grade-current-average",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": enrolment.id,
                    "subject_id": subject.id,
                },
            )
        )

        assert response.status_code == 200
        data = response.json()
        assert data["average"] == 85
        assert data["graded_units"] == 2
        assert data["pending_units"] == 2
        assert data["total_units"] == 4

    def test_current_average_is_none_when_nothing_graded_api(self, auth_client, institution):
        """
        Test that the average is null, not zero, when nothing is graded yet.
        """
        cycle = AcademicCycleFactory(institution=institution)
        self._units(cycle, 2)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=institution)

        response = auth_client.get(
            reverse(
                "grade-current-average",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": enrolment.id,
                    "subject_id": subject.id,
                },
            )
        )

        assert response.status_code == 200
        data = response.json()
        assert data["average"] is None
        assert data["pending_units"] == 2

    def test_current_average_enrolment_not_found_returns_404(self, auth_client, institution):
        """
        Test endpoint with an enrolment from a different cycle.
        """
        cycle = AcademicCycleFactory(institution=institution)
        other_cycle = AcademicCycleFactory(
            institution=institution,
            year=cycle.year + 1,
            starts_on=date(cycle.year + 1, 1, 1),
            ends_on=date(cycle.year + 1, 12, 31),
            status="draft",
        )
        enrolment = self._enrolment(other_cycle)
        subject = SubjectFactory(institution=institution)

        response = auth_client.get(
            reverse(
                "grade-current-average",
                kwargs={
                    "cycle_public_id": str(cycle.public_id),
                    "enrolment_id": enrolment.id,
                    "subject_id": subject.id,
                },
            )
        )

        assert response.status_code == 404
