"""
Integration tests for evaluation domain.

RF-EVC-001: Estructura de unidades del ciclo
RF-EVC-002: Ventana de captura de notas
RF-EVC-003: Ventana de recuperacion
RF-EVC-004: Brecha excepcional autorizada

Cross-domain flows: evaluation interacts with academics domain (cycles).
"""

from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.academics.models import AcademicCycle
from apps.evaluation.models import EvaluationUnit
from apps.evaluation.services import (
    create_evaluation_unit,
    grant_capture_exception,
    set_recovery_window,
    validate_capture_allowed,
    validate_capture_window_open,
    validate_recovery_window_open,
)
from apps.common.models import DomainError
from tests.factories.academic import AcademicCycleFactory, SubjectFactory
from tests.factories.people import PersonFactory

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


class TestRecoveryWindowIntegration:
    """Integration tests for RF-EVC-003: Recovery window validation across domain."""

    def test_recovery_out_of_date_rejected_integration(self):
        """
        Scenario 5: Recuperación fuera de fecha (RF-EVC-003)
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
            validate_recovery_window_open(unit, on_date=date(2026, 3, 5))

    def test_recovery_audit_trail(self):
        """
        Test that setting the recovery window is recorded in the audit trail.
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

        from apps.audit.models import AuditEvent

        event = AuditEvent.objects.get(action="evaluation.unit_recovery_window_set")
        assert event.resource_identifier == str(unit.pk)
        assert event.context["recovery_starts_on"] == "2026-03-10"
        assert event.context["recovery_ends_on"] == "2026-03-20"


class TestCaptureExceptionGrantIntegration:
    """Integration tests for RF-EVC-004: Brecha excepcional autorizada."""

    def _closed_unit(self, cycle):
        yesterday = timezone.localdate() - timedelta(days=1)
        return create_evaluation_unit(
            academic_cycle=cycle,
            number=1,
            name="Unit 1",
            starts_on=yesterday - timedelta(days=30),
            ends_on=yesterday,
            capture_starts_on=yesterday - timedelta(days=30),
            capture_ends_on=yesterday,
        )

    def test_teacher_capture_scoped_to_grant_integration(self):
        """
        Scenario 6: Docente que no alcanzó a subir notas (cross-domain)
        GIVEN una unidad con la ventana de captura cerrada
        WHEN se habilita una brecha para un docente y una subárea
        THEN ese docente puede registrar notas de esa subárea durante el plazo
        AND ningún otro docente obtiene acceso por esa brecha
        """
        cycle = AcademicCycleFactory()
        unit = self._closed_unit(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()
        other_teacher = PersonFactory()

        grant_capture_exception(
            evaluation_unit=unit,
            subject=subject,
            teacher=teacher,
            reason="No alcanzó a subir notas por falla eléctrica.",
            expires_at=timezone.now() + timedelta(days=1),
        )

        validate_capture_allowed(unit, subject, teacher)

        with pytest.raises(DomainError, match="Grade capture window is closed"):
            validate_capture_allowed(unit, subject, other_teacher)

    def test_grant_expires_automatically_integration(self):
        """
        Scenario 7: Expiración automática (cross-domain)
        GIVEN una brecha excepcional cuyo plazo venció
        WHEN el docente intenta registrar una nota
        THEN el sistema rechaza la operación sin que nadie haya tenido que
             revocar la brecha
        """
        cycle = AcademicCycleFactory()
        unit = self._closed_unit(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()

        grant_capture_exception(
            evaluation_unit=unit,
            subject=subject,
            teacher=teacher,
            reason="No alcanzó a subir notas por falla eléctrica.",
            expires_at=timezone.now() + timedelta(hours=1),
        )

        after_expiration = timezone.now() + timedelta(hours=2)
        with pytest.raises(DomainError, match="Grade capture window is closed"):
            validate_capture_allowed(unit, subject, teacher, on_datetime=after_expiration)

    def test_capture_exception_audit_trail(self):
        """
        Test that granting a capture exception is recorded in the audit trail.
        """
        cycle = AcademicCycleFactory()
        unit = self._closed_unit(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()

        grant = grant_capture_exception(
            evaluation_unit=unit,
            subject=subject,
            teacher=teacher,
            reason="No alcanzó a subir notas por falla eléctrica.",
            expires_at=timezone.now() + timedelta(days=1),
        )

        from apps.audit.models import AuditEvent

        event = AuditEvent.objects.get(action="evaluation.capture_exception_granted")
        assert event.resource_identifier == str(grant.pk)
        assert event.context["unit_id"] == str(unit.public_id)
        assert event.context["subject_id"] == str(subject.public_id)
        assert event.context["teacher_id"] == str(teacher.public_id)
