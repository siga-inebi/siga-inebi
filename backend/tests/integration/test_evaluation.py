"""
Integration tests for evaluation domain.

RF-EVC-001: Estructura de unidades del ciclo
RF-EVC-002: Ventana de captura de notas

Cross-domain flows: evaluation interacts with academics domain (cycles).
"""

from datetime import date

import pytest

from apps.academics.models import AcademicCycle
from apps.evaluation.models import EvaluationUnit
from apps.evaluation.services import create_evaluation_unit, validate_capture_window_open
from apps.common.models import DomainError
from tests.factories.academic import AcademicCycleFactory

pytestmark = pytest.mark.django_db


class TestEvaluationIntegration:
    """Integration tests for evaluation domain."""

    def test_create_complete_cycle_structure_with_units(self):
        """
        Test creating a full cycle with academic structure and evaluation units.
        
        Workflow:
        1. Create cycle in DRAFT status
        2. Add evaluation units
        3. Verify units are associated correctly
        """
        # Create cycle
        cycle = AcademicCycleFactory(
            year=2026,
            starts_on=date(2026, 1, 15),
            ends_on=date(2026, 10, 31),
            status=AcademicCycle.CycleStatus.DRAFT,
        )

        # Add evaluation units
        units_data = [
            (1, "Trimestre 1", date(2026, 1, 15), date(2026, 3, 15), date(2026, 1, 1), date(2026, 3, 31)),
            (2, "Trimestre 2", date(2026, 4, 1), date(2026, 6, 30), date(2026, 3, 15), date(2026, 7, 15)),
            (3, "Trimestre 3", date(2026, 7, 1), date(2026, 9, 30), date(2026, 6, 15), date(2026, 10, 15)),
            (4, "Examen Final", date(2026, 10, 1), date(2026, 10, 31), date(2026, 9, 15), date(2026, 11, 15)),
        ]

        units = []
        for number, name, starts, ends, capture_starts, capture_ends in units_data:
            unit = create_evaluation_unit(
                academic_cycle=cycle,
                number=number,
                name=name,
                starts_on=starts,
                ends_on=ends,
                capture_starts_on=capture_starts,
                capture_ends_on=capture_ends,
            )
            units.append(unit)

        # Verify structure
        assert cycle.evaluation_units.count() == 4
        assert all(u.academic_cycle_id == cycle.id for u in units)
        assert [u.status for u in units] == [EvaluationUnit.UnitStatus.OPEN] * 4

    def test_evaluation_units_persist_with_soft_delete(self):
        """
        Test that is_active field works correctly for soft-delete.
        """
        cycle = AcademicCycleFactory()
        unit = create_evaluation_unit(
            academic_cycle=cycle,
            number=1,
            name="Unit 1",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 2, 28),
            capture_starts_on=date(2026, 1, 1),
            capture_ends_on=date(2026, 2, 28),
        )

        assert unit.is_active is True

        # Soft delete
        unit.is_active = False
        unit.save()

        # Unit still exists but is inactive
        fetched = EvaluationUnit.objects.get(public_id=unit.public_id)
        assert fetched.is_active is False

        # Filtering by is_active
        active_units = EvaluationUnit.objects.filter(is_active=True, academic_cycle=cycle)
        inactive_units = EvaluationUnit.objects.filter(is_active=False, academic_cycle=cycle)
        assert active_units.count() == 0
        assert inactive_units.count() == 1

    def test_audit_trail_on_unit_creation(self):
        """
        Test that audit events are recorded when units are created.
        """
        cycle = AcademicCycleFactory()

        # Service should record audit event
        unit = create_evaluation_unit(
            academic_cycle=cycle,
            number=1,
            name="Unit 1",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 2, 28),
            capture_starts_on=date(2026, 1, 1),
            capture_ends_on=date(2026, 2, 28),
        )

        # Verify audit event was recorded
        from apps.audit.models import AuditEvent

        event = AuditEvent.objects.get(action="evaluation.unit_created")
        assert event.resource == "EvaluationUnit"
        assert event.resource_identifier == str(unit.pk)
        assert event.context["cycle_id"] == str(cycle.public_id)
        assert event.context["number"] == 1
        assert event.context["capture_starts_on"] == "2026-01-01"
        assert event.context["capture_ends_on"] == "2026-02-28"


class TestCaptureWindowIntegration:
    """Integration tests for RF-EVC-002: Capture window validation across domain."""

    def test_capture_window_validation_integration(self):
        """
        Scenario 3: Captura dentro de la ventana (RF-EVC-002)
        GIVEN una unidad cuya ventana de captura está abierta
        WHEN se valida la ventana de captura
        THEN el sistema acepta la operación
        """
        cycle = AcademicCycleFactory()
        unit = create_evaluation_unit(
            academic_cycle=cycle,
            number=1,
            name="Unit 1",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 2, 28),
            capture_starts_on=date(2026, 1, 1),
            capture_ends_on=date(2026, 3, 31),
        )

        validate_capture_window_open(unit, on_date=date(2026, 2, 15))
        # No exception raised

    def test_capture_window_closed_integration(self):
        """
        Scenario 4: Captura con la ventana cerrada (RF-EVC-002)
        GIVEN una unidad cuya ventana de captura ya cerró
        WHEN se intenta registrar una nota de esa unidad
        THEN el sistema rechaza la operación indicando que la ventana está cerrada
        """
        cycle = AcademicCycleFactory()
        unit = create_evaluation_unit(
            academic_cycle=cycle,
            number=1,
            name="Unit 1",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 2, 28),
            capture_starts_on=date(2026, 1, 1),
            capture_ends_on=date(2026, 2, 28),
        )

        with pytest.raises(DomainError, match="Grade capture window is closed"):
            validate_capture_window_open(unit, on_date=date(2026, 3, 1))
