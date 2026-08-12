"""
Unit tests for evaluation services.

RF-EVC-001: Estructura de unidades del ciclo
RF-EVC-002: Ventana de captura de notas
RF-EVC-003: Ventana de recuperacion

Scenario 1: Configuración de cuatro unidades
Scenario 2: Unidades solapadas
Scenario 3: Captura dentro de la ventana
Scenario 4: Captura con la ventana cerrada
Scenario 5: Recuperación fuera de fecha
"""

from datetime import date

import pytest

from apps.common.models import DomainError
from apps.evaluation.models import EvaluationUnit
from apps.evaluation.services import (
    create_evaluation_unit,
    set_recovery_window,
    validate_capture_window_open,
    validate_recovery_window_open,
)
from tests.factories.academic import AcademicCycleFactory

pytestmark = pytest.mark.django_db


class TestCreateEvaluationUnit:
    """Tests for create_evaluation_unit service."""

    def test_create_four_units_successfully(self):
        """
        Scenario 1: Configuración de cuatro unidades
        GIVEN un ciclo escolar sin unidades configuradas
        WHEN un usuario autorizado define cuatro unidades con sus fechas
        THEN el sistema las registra como la estructura de evaluación de ese ciclo
        """
        cycle = AcademicCycleFactory(
            starts_on=date(2026, 1, 15),
            ends_on=date(2026, 10, 31),
        )

        units = []
        for i in range(1, 5):
            start_month = 1 + (i - 1) * 2
            end_month = start_month + 1
            if end_month > 12:
                end_month = 12
            
            unit = create_evaluation_unit(
                academic_cycle=cycle,
                number=i,
                name=f"Unit {i}",
                starts_on=date(2026, start_month, 1),
                ends_on=date(2026, end_month, 28),
                capture_starts_on=date(2026, start_month, 1),
                capture_ends_on=date(2026, end_month, 28),
            )
            units.append(unit)

        assert len(units) == 4
        assert all(u.academic_cycle == cycle for u in units)
        assert [u.number for u in units] == [1, 2, 3, 4]
        assert [u.status for u in units] == [
            EvaluationUnit.UnitStatus.OPEN,
        ] * 4

    def test_reject_overlapping_dates(self):
        """
        Scenario 2: Unidades solapadas
        GIVEN un ciclo con una unidad ya configurada
        WHEN se intenta crear otra cuyo rango de fechas se solapa con la anterior
        THEN el sistema rechaza la operación indicando el conflicto
        """
        cycle = AcademicCycleFactory(
            starts_on=date(2026, 1, 15),
            ends_on=date(2026, 10, 31),
        )

        # Create first unit: Jan 1 - Feb 28
        unit1 = create_evaluation_unit(
            academic_cycle=cycle,
            number=1,
            name="Unit 1",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 2, 28),
            capture_starts_on=date(2026, 1, 1),
            capture_ends_on=date(2026, 2, 28),
        )
        assert unit1.id is not None

        # Try to create overlapping unit: Feb 1 - Mar 31
        with pytest.raises(DomainError, match="overlap"):
            create_evaluation_unit(
                academic_cycle=cycle,
                number=2,
                name="Unit 2",
                starts_on=date(2026, 2, 1),
                ends_on=date(2026, 3, 31),
                capture_starts_on=date(2026, 2, 1),
                capture_ends_on=date(2026, 3, 31),
            )

    def test_reject_invalid_date_range(self):
        """
        Test that starts_on > ends_on is rejected.
        """
        cycle = AcademicCycleFactory()

        with pytest.raises(DomainError, match="cannot be after"):
            create_evaluation_unit(
                academic_cycle=cycle,
                number=1,
                name="Unit 1",
                starts_on=date(2026, 3, 1),
                ends_on=date(2026, 1, 1),
                capture_starts_on=date(2026, 1, 1),
                capture_ends_on=date(2026, 3, 1),
            )

    def test_reject_duplicate_unit_number(self):
        """
        Test that two units with the same number in the same cycle are rejected.
        """
        cycle = AcademicCycleFactory()

        # Create first unit
        create_evaluation_unit(
            academic_cycle=cycle,
            number=1,
            name="Unit 1",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 2, 28),
            capture_starts_on=date(2026, 1, 1),
            capture_ends_on=date(2026, 2, 28),
        )

        # Try to create another with same number
        with pytest.raises(DomainError, match="number.*already exists"):
            create_evaluation_unit(
                academic_cycle=cycle,
                number=1,
                name="Unit 1 Duplicate",
                starts_on=date(2026, 3, 1),
                ends_on=date(2026, 4, 30),
                capture_starts_on=date(2026, 3, 1),
                capture_ends_on=date(2026, 4, 30),
            )

    def test_allow_units_in_different_cycles(self):
        """
        Same unit number should be allowed in different cycles.
        """
        cycle1 = AcademicCycleFactory(year=2025)
        cycle2 = AcademicCycleFactory(year=2026)

        unit1 = create_evaluation_unit(
            academic_cycle=cycle1,
            number=1,
            name="Unit 1",
            starts_on=date(2025, 1, 1),
            ends_on=date(2025, 2, 28),
            capture_starts_on=date(2025, 1, 1),
            capture_ends_on=date(2025, 2, 28),
        )

        unit2 = create_evaluation_unit(
            academic_cycle=cycle2,
            number=1,
            name="Unit 1",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 2, 28),
            capture_starts_on=date(2026, 1, 1),
            capture_ends_on=date(2026, 2, 28),
        )

        assert unit1.id != unit2.id
        assert unit1.academic_cycle_id != unit2.academic_cycle_id


class TestCaptureWindowValidation:
    """Tests for RF-EVC-002: Ventana de captura de notas (Capture window validation)."""

    def test_capture_within_window(self):
        """
        Scenario 3: Captura dentro de la ventana
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
            capture_ends_on=date(2026, 2, 28),
        )

        # Validate on a date within the window
        validate_capture_window_open(unit, on_date=date(2026, 1, 15))
        # Should not raise

    def test_capture_after_window_closed(self):
        """
        Scenario 4: Captura con la ventana cerrada
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

        # Try to validate on a date after the window closed
        with pytest.raises(DomainError, match="Grade capture window is closed"):
            validate_capture_window_open(unit, on_date=date(2026, 3, 1))

    def test_capture_before_window_opens(self):
        """
        Test that capture is rejected when tried before window opens.
        """
        cycle = AcademicCycleFactory()
        unit = create_evaluation_unit(
            academic_cycle=cycle,
            number=1,
            name="Unit 1",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 2, 28),
            capture_starts_on=date(2026, 1, 15),
            capture_ends_on=date(2026, 2, 28),
        )

        # Try to validate before the window opens
        with pytest.raises(DomainError, match="Grade capture window is closed"):
            validate_capture_window_open(unit, on_date=date(2026, 1, 1))

    def test_invalid_capture_date_range(self):
        """
        Test that capture_starts_on > capture_ends_on is rejected.
        """
        cycle = AcademicCycleFactory()

        with pytest.raises(DomainError, match="Capture window start date"):
            create_evaluation_unit(
                academic_cycle=cycle,
                number=1,
                name="Unit 1",
                starts_on=date(2026, 1, 1),
                ends_on=date(2026, 2, 28),
                capture_starts_on=date(2026, 3, 1),
                capture_ends_on=date(2026, 1, 1),
            )


class TestRecoveryWindow:
    """Tests for RF-EVC-003: Ventana de recuperacion."""

    def test_recovery_before_window_opens_is_rejected(self):
        """
        Scenario 5: Recuperación fuera de fecha
        GIVEN una ventana de recuperación aún no abierta
        WHEN un docente intenta registrar una nota de recuperación
        THEN el sistema rechaza la operación
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
        set_recovery_window(
            unit=unit,
            recovery_starts_on=date(2026, 3, 10),
            recovery_ends_on=date(2026, 3, 20),
        )

        with pytest.raises(DomainError, match="Recovery window is closed"):
            validate_recovery_window_open(unit, on_date=date(2026, 3, 1))

    def test_recovery_after_window_closed_is_rejected(self):
        """
        Test that recovery is rejected after the window has closed.
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
        set_recovery_window(
            unit=unit,
            recovery_starts_on=date(2026, 3, 10),
            recovery_ends_on=date(2026, 3, 20),
        )

        with pytest.raises(DomainError, match="Recovery window is closed"):
            validate_recovery_window_open(unit, on_date=date(2026, 3, 21))

    def test_recovery_within_window_is_accepted(self):
        """
        Test that recovery is accepted while the window is open.
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
        set_recovery_window(
            unit=unit,
            recovery_starts_on=date(2026, 3, 10),
            recovery_ends_on=date(2026, 3, 20),
        )

        validate_recovery_window_open(unit, on_date=date(2026, 3, 15))
        # No exception raised

    def test_recovery_without_configured_window_is_rejected(self):
        """
        Test that recovery is rejected when no recovery window is configured.
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

        with pytest.raises(DomainError, match="No recovery window has been configured"):
            validate_recovery_window_open(unit, on_date=date(2026, 3, 15))

    def test_reject_invalid_recovery_date_range(self):
        """
        Test that recovery_starts_on > recovery_ends_on is rejected.
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

        with pytest.raises(DomainError, match="Recovery window start date"):
            set_recovery_window(
                unit=unit,
                recovery_starts_on=date(2026, 3, 20),
                recovery_ends_on=date(2026, 3, 10),
            )
