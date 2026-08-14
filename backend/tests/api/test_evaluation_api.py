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

from apps.evaluation.models import CaptureExceptionGrant, EvaluationUnit
from tests.factories.academic import AcademicCycleFactory, SubjectFactory
from tests.factories.evaluation import EvaluationUnitFactory
from tests.factories.people import PersonFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


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
