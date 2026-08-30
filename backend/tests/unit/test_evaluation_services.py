"""
Unit tests for evaluation services.

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
Scenario 9: Registro de una nota por el docente
Scenario 10: Nota fuera de rango
Scenario 11: Promedio en curso con notas pendientes
Scenario 12: Promedio de las unidades
"""

from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.common.models import DomainError
from apps.enrolments.services import create_enrolment
from apps.evaluation.models import EvaluationUnit, Grade
from apps.evaluation.services import (
    close_evaluation_unit,
    create_evaluation_unit,
    get_current_average,
    get_effective_unit_count,
    get_final_subject_grade,
    get_global_evaluation_config,
    grant_capture_exception,
    register_unit_grade,
    set_cycle_unit_count,
    set_recovery_window,
    update_global_evaluation_config,
    validate_capture_allowed,
    validate_capture_window_open,
    validate_recovery_window_open,
)
from tests.factories.academic import AcademicCycleFactory, SectionFactory, SubjectFactory
from tests.factories.evaluation import CaptureExceptionGrantFactory, EvaluationUnitFactory
from tests.factories.identity import UserFactory
from tests.factories.people import PersonFactory
from tests.factories.students import StudentFactory

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

        with pytest.raises(DomainError, match="no puede ser posterior"):
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
        with pytest.raises(DomainError, match="ventana de captura"):
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
        with pytest.raises(DomainError, match="ventana de captura"):
            validate_capture_window_open(unit, on_date=date(2026, 1, 1))

    def test_invalid_capture_date_range(self):
        """
        Test that capture_starts_on > capture_ends_on is rejected.
        """
        cycle = AcademicCycleFactory()

        with pytest.raises(DomainError, match="ventana de captura"):
            create_evaluation_unit(
                academic_cycle=cycle,
                number=1,
                name="Unit 1",
                starts_on=date(2026, 1, 1),
                ends_on=date(2026, 2, 28),
                capture_starts_on=date(2026, 3, 1),
                capture_ends_on=date(2026, 1, 1),
            )


class TestCloseEvaluationUnit:
    """Tests for RF-EVC-007: Estados de la unidad."""

    def _enrolment(self, cycle):
        section = SectionFactory(academic_cycle=cycle)
        student = StudentFactory()
        return create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )

    def _expired_unit(self, cycle):
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

    def test_close_unit_records_actor_and_moment_in_bitacora(self):
        """
        Scenario: Cierre de una unidad
        GIVEN una unidad con su ventana de captura vencida
        WHEN un usuario autorizado la cierra
        THEN el sistema registra el cambio de estado en la bitácora
        """
        from apps.audit.models import AuditEvent

        cycle = AcademicCycleFactory()
        unit = self._expired_unit(cycle)
        actor = UserFactory()

        closed = close_evaluation_unit(unit, actor=actor)

        assert closed.status == EvaluationUnit.UnitStatus.CLOSED
        assert closed.is_closed

        event = AuditEvent.objects.get(action="evaluation.unit_closed")
        assert event.resource_identifier == str(unit.pk)
        assert event.actor_id == actor.pk

    def test_closed_unit_rejects_grade_capture_without_grant(self):
        """
        Scenario: Cierre de una unidad (continuacion)
        AND las notas de esa unidad dejan de admitir modificación salvo brecha excepcional
        """
        cycle = AcademicCycleFactory()
        unit = self._expired_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()
        Grade.objects.create(enrolment=enrolment, subject=subject, evaluation_unit=unit, value=70)

        close_evaluation_unit(unit)

        with pytest.raises(DomainError, match="ventana de captura"):
            register_unit_grade(
                enrolment=enrolment,
                subject=subject,
                evaluation_unit=unit,
                teacher=teacher,
                value=90,
            )

    def test_closed_unit_allows_capture_with_active_grant(self):
        """
        A closed unit still admits capture when an exceptional grant covers
        the teacher and subject (RF-EVC-004).
        """
        cycle = AcademicCycleFactory()
        unit = self._expired_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()
        close_evaluation_unit(unit)
        CaptureExceptionGrantFactory(evaluation_unit=unit, subject=subject, teacher=teacher)

        grade = register_unit_grade(
            enrolment=enrolment,
            subject=subject,
            evaluation_unit=unit,
            teacher=teacher,
            value=90,
        )

        assert grade.value == 90

    def test_reject_closing_an_already_closed_unit(self):
        cycle = AcademicCycleFactory()
        unit = self._expired_unit(cycle)
        close_evaluation_unit(unit)

        with pytest.raises(DomainError, match="ya esta cerrada"):
            close_evaluation_unit(unit)


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

        with pytest.raises(DomainError, match="ventana de recuperacion de la unidad"):
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

        with pytest.raises(DomainError, match="ventana de recuperacion de la unidad"):
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

        with pytest.raises(DomainError, match="no tiene ventana de recuperacion configurada"):
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

        with pytest.raises(DomainError, match="ventana de recuperacion"):
            set_recovery_window(
                unit=unit,
                recovery_starts_on=date(2026, 3, 20),
                recovery_ends_on=date(2026, 3, 10),
            )


class TestCaptureExceptionGrant:
    """Tests for RF-EVC-004: Brecha excepcional autorizada."""

    def _closed_unit(self):
        """A unit whose capture window closed yesterday."""
        cycle = AcademicCycleFactory()
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

    def test_teacher_with_grant_can_capture_after_window_closed(self):
        """
        Scenario 6: Docente que no alcanzó a subir notas
        GIVEN una unidad con la ventana de captura cerrada
        WHEN un usuario con permiso de autorización académica habilita una
             brecha para un docente y una subárea indicando el motivo
        THEN ese docente puede registrar las notas de esa subárea durante el
             plazo concedido
        AND ningún otro docente obtiene acceso por esa brecha
        """
        unit = self._closed_unit()
        subject = SubjectFactory()
        teacher = PersonFactory()
        other_teacher = PersonFactory()

        grant_capture_exception(
            evaluation_unit=unit,
            subject=subject,
            teacher=teacher,
            reason="No alcanzó a subir notas por falla eléctrica.",
            expires_at=timezone.now() + timedelta(days=1),
        )

        # The authorized teacher can capture despite the closed window.
        validate_capture_allowed(unit, subject, teacher)
        # No exception raised.

        # No other teacher gains access through this grant.
        with pytest.raises(DomainError, match="ventana de captura"):
            validate_capture_allowed(unit, subject, other_teacher)

    def test_grant_expires_automatically(self):
        """
        Scenario 7: Expiración automática
        GIVEN una brecha excepcional cuyo plazo venció
        WHEN el docente intenta registrar una nota
        THEN el sistema rechaza la operación sin que nadie haya tenido que
             revocar la brecha
        """
        unit = self._closed_unit()
        subject = SubjectFactory()
        teacher = PersonFactory()

        grant_capture_exception(
            evaluation_unit=unit,
            subject=subject,
            teacher=teacher,
            reason="No alcanzó a subir notas por falla eléctrica.",
            expires_at=timezone.now() + timedelta(hours=1),
        )

        # Still active is_active=True; only expires_at determines validity.
        past_expiration = timezone.now() + timedelta(hours=2)
        with pytest.raises(DomainError, match="ventana de captura"):
            validate_capture_allowed(unit, subject, teacher, on_datetime=past_expiration)

    def test_reject_empty_reason(self):
        """
        Test that granting an exception without a reason is rejected.
        """
        unit = self._closed_unit()
        subject = SubjectFactory()
        teacher = PersonFactory()

        with pytest.raises(DomainError, match="requiere un motivo"):
            grant_capture_exception(
                evaluation_unit=unit,
                subject=subject,
                teacher=teacher,
                reason="   ",
                expires_at=timezone.now() + timedelta(days=1),
            )

    def test_reject_expiration_in_the_past(self):
        """
        Test that granting an exception with a past expiration is rejected.
        """
        unit = self._closed_unit()
        subject = SubjectFactory()
        teacher = PersonFactory()

        with pytest.raises(DomainError, match="debe ser futuro"):
            grant_capture_exception(
                evaluation_unit=unit,
                subject=subject,
                teacher=teacher,
                reason="Motivo válido.",
                expires_at=timezone.now() - timedelta(hours=1),
            )


class TestGlobalEvaluationConfig:
    """Tests for RF-EVC-005: Configuracion global heredable."""

    def test_cycle_departs_from_global_value(self):
        """
        Scenario 8: Ciclo que se aparta del valor global
        GIVEN una configuración global de cuatro unidades
        WHEN un usuario autorizado edita un ciclo determinado para que tenga
             otra cantidad
        THEN ese ciclo conserva su propia configuración
        AND los demás ciclos y la configuración global permanecen sin cambios
        """
        update_global_evaluation_config(default_unit_count=4)

        cycle_a = AcademicCycleFactory()
        cycle_b = AcademicCycleFactory()

        # Before any override, both cycles inherit the global default.
        assert get_effective_unit_count(cycle_a) == 4
        assert get_effective_unit_count(cycle_b) == 4

        # Cycle A departs from the global value.
        set_cycle_unit_count(academic_cycle=cycle_a, unit_count=3)

        # Cycle A keeps its own configuration.
        assert get_effective_unit_count(cycle_a) == 3

        # Cycle B and the global config remain unchanged.
        assert get_effective_unit_count(cycle_b) == 4
        assert get_global_evaluation_config().default_unit_count == 4

    def test_global_config_is_singleton(self):
        """
        Test that repeated reads/writes operate on the same global config row.
        """
        first = get_global_evaluation_config()
        update_global_evaluation_config(default_unit_count=5)
        second = get_global_evaluation_config()

        assert first.pk == second.pk
        assert second.default_unit_count == 5

    def test_reject_non_positive_global_unit_count(self):
        """
        Test that a non-positive default_unit_count is rejected.
        """
        with pytest.raises(DomainError, match="entero positivo"):
            update_global_evaluation_config(default_unit_count=0)

    def test_reject_non_positive_cycle_unit_count(self):
        """
        Test that a non-positive cycle override is rejected.
        """
        cycle = AcademicCycleFactory()

        with pytest.raises(DomainError, match="entero positivo"):
            set_cycle_unit_count(academic_cycle=cycle, unit_count=0)


class TestRegisterUnitGrade:
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

    def test_register_grade_within_capture_window(self):
        """
        Scenario 9: Registro de una nota por el docente
        GIVEN un docente con una subárea a su cargo y la ventana de captura abierta
        WHEN registra la nota de un estudiante para la unidad en curso
        THEN el sistema la almacena asociada al estudiante, la subárea, la unidad y el ciclo
        """
        cycle = AcademicCycleFactory()
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()

        grade = register_unit_grade(
            enrolment=enrolment,
            subject=subject,
            evaluation_unit=unit,
            teacher=teacher,
            value=85,
        )

        assert grade.enrolment == enrolment
        assert grade.subject == subject
        assert grade.evaluation_unit == unit
        assert grade.evaluation_unit.academic_cycle == cycle
        assert grade.value == 85

    def test_register_grade_again_updates_the_single_consolidated_value(self):
        """
        Registering the same (enrolment, subject, unit) again updates the
        existing grade instead of creating a duplicate row.
        """
        cycle = AcademicCycleFactory()
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()

        first = register_unit_grade(
            enrolment=enrolment, subject=subject, evaluation_unit=unit, teacher=teacher, value=70
        )
        second = register_unit_grade(
            enrolment=enrolment, subject=subject, evaluation_unit=unit, teacher=teacher, value=90
        )

        assert first.pk == second.pk
        assert second.value == 90
        assert (
            Grade.objects.filter(enrolment=enrolment, subject=subject, evaluation_unit=unit).count()
            == 1
        )

    def test_reject_grade_when_capture_window_closed(self):
        """
        Test that a grade is rejected when the capture window is closed and no
        exceptional grant covers the teacher and subject.
        """
        cycle = AcademicCycleFactory()
        yesterday = timezone.localdate() - timedelta(days=1)
        unit = create_evaluation_unit(
            academic_cycle=cycle,
            number=1,
            name="Unit 1",
            starts_on=yesterday - timedelta(days=30),
            ends_on=yesterday,
            capture_starts_on=yesterday - timedelta(days=30),
            capture_ends_on=yesterday,
        )
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()

        with pytest.raises(DomainError, match="ventana de captura"):
            register_unit_grade(
                enrolment=enrolment,
                subject=subject,
                evaluation_unit=unit,
                teacher=teacher,
                value=85,
            )

    def test_reject_enrolment_and_unit_from_different_cycles(self):
        """
        Test that an enrolment and a unit from different academic cycles are
        rejected.
        """
        cycle = AcademicCycleFactory()
        other_cycle = AcademicCycleFactory()
        unit = EvaluationUnitFactory(academic_cycle=other_cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()

        with pytest.raises(DomainError, match="ciclos escolares distintos"):
            register_unit_grade(
                enrolment=enrolment,
                subject=subject,
                evaluation_unit=unit,
                teacher=teacher,
                value=85,
            )


class TestGradeCorrection:
    """Tests for RF-CAL-005: Corrección de notas registradas."""

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

    def test_correction_with_open_window_is_accepted_and_audited(self):
        """
        Scenario: Corrección con la ventana abierta
        GIVEN una nota registrada y una ventana de captura abierta
        WHEN el docente la corrige
        THEN el sistema acepta el cambio y registra en bitácora el valor anterior y el nuevo
        """
        from apps.audit.models import AuditEvent

        cycle = AcademicCycleFactory()
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()

        register_unit_grade(
            enrolment=enrolment, subject=subject, evaluation_unit=unit, teacher=teacher, value=70
        )
        corrected = register_unit_grade(
            enrolment=enrolment, subject=subject, evaluation_unit=unit, teacher=teacher, value=90
        )

        assert corrected.value == 90

        event = AuditEvent.objects.filter(action="evaluation.grade_updated").latest("created_at")
        assert event.context["changes"] == {"value": {"before": 70, "after": 90}}

    def test_correction_with_closed_window_and_no_grant_is_rejected(self):
        """
        Scenario: Corrección con la ventana cerrada y sin brecha
        GIVEN una nota de una unidad cerrada, sin brecha excepcional vigente
        WHEN el docente intenta corregirla
        THEN el sistema rechaza la operación
        """
        cycle = AcademicCycleFactory()
        yesterday = timezone.localdate() - timedelta(days=1)
        unit = create_evaluation_unit(
            academic_cycle=cycle,
            number=1,
            name="Unit 1",
            starts_on=yesterday - timedelta(days=30),
            ends_on=yesterday,
            capture_starts_on=yesterday - timedelta(days=30),
            capture_ends_on=yesterday,
        )
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()

        # A grade already registered before the window closed.
        Grade.objects.create(enrolment=enrolment, subject=subject, evaluation_unit=unit, value=70)

        with pytest.raises(DomainError, match="ventana de captura"):
            register_unit_grade(
                enrolment=enrolment,
                subject=subject,
                evaluation_unit=unit,
                teacher=teacher,
                value=90,
            )

        assert (
            Grade.objects.get(enrolment=enrolment, subject=subject, evaluation_unit=unit).value
            == 70
        )


class TestGradeScale:
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

    def test_reject_value_above_scale(self):
        """
        Scenario 10: Nota fuera de rango
        GIVEN un docente registrando notas
        WHEN introduce un valor superior a cien
        THEN el sistema rechaza el valor indicando el rango admitido
        """
        cycle = AcademicCycleFactory()
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()

        with pytest.raises(DomainError, match="entre 0 y 100"):
            register_unit_grade(
                enrolment=enrolment,
                subject=subject,
                evaluation_unit=unit,
                teacher=teacher,
                value=101,
            )

    def test_reject_negative_value(self):
        """
        Test that a negative value is rejected, indicating the admitted range.
        """
        cycle = AcademicCycleFactory()
        unit = self._open_unit(cycle)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()

        with pytest.raises(DomainError, match="entre 0 y 100"):
            register_unit_grade(
                enrolment=enrolment,
                subject=subject,
                evaluation_unit=unit,
                teacher=teacher,
                value=-1,
            )

    def test_accept_boundary_values(self):
        """
        Test that the scale boundaries (0 and 100) are accepted.
        """
        cycle = AcademicCycleFactory()
        unit = self._open_unit(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()

        zero_enrolment = self._enrolment(cycle)
        zero_grade = register_unit_grade(
            enrolment=zero_enrolment,
            subject=subject,
            evaluation_unit=unit,
            teacher=teacher,
            value=0,
        )
        assert zero_grade.value == 0

        hundred_enrolment = self._enrolment(cycle)
        hundred_grade = register_unit_grade(
            enrolment=hundred_enrolment,
            subject=subject,
            evaluation_unit=unit,
            teacher=teacher,
            value=100,
        )
        assert hundred_grade.value == 100


class TestGetCurrentAverage:
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
        """
        ``count`` units in the cycle, all with a capture window open today
        so any of them can be graded, but with non-overlapping evaluation
        periods to satisfy the unit's own exclusion constraint.
        """
        today = timezone.localdate()
        units = []
        for i in range(count):
            starts = today + timedelta(days=i * 70)
            units.append(
                create_evaluation_unit(
                    academic_cycle=cycle,
                    number=i + 1,
                    name=f"Unit {i + 1}",
                    starts_on=starts,
                    ends_on=starts + timedelta(days=60),
                    capture_starts_on=today - timedelta(days=5),
                    capture_ends_on=today + timedelta(days=5),
                )
            )
        return units

    def test_average_excludes_pending_units(self):
        """
        Scenario 11: Promedio en curso con notas pendientes
        GIVEN un estudiante con dos unidades calificadas y dos sin registrar
        WHEN consulta su promedio en curso
        THEN el sistema lo calcula únicamente sobre las unidades calificadas
        AND indica cuántas unidades están pendientes de registrar
        """
        cycle = AcademicCycleFactory()
        units = self._units(cycle, 4)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()

        register_unit_grade(
            enrolment=enrolment,
            subject=subject,
            evaluation_unit=units[0],
            teacher=teacher,
            value=80,
        )
        register_unit_grade(
            enrolment=enrolment,
            subject=subject,
            evaluation_unit=units[1],
            teacher=teacher,
            value=90,
        )
        # units[2] and units[3] stay ungraded: "sin calificar", not zero.

        result = get_current_average(enrolment, subject)

        assert result["average"] == 85
        assert result["graded_units"] == 2
        assert result["pending_units"] == 2
        assert result["total_units"] == 4

    def test_average_is_none_when_nothing_graded(self):
        """
        Test that the average is None, not zero, when no unit has been
        graded yet: an absence of data must never present as a zero.
        """
        cycle = AcademicCycleFactory()
        self._units(cycle, 2)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=cycle.institution)

        result = get_current_average(enrolment, subject)

        assert result["average"] is None
        assert result["graded_units"] == 0
        assert result["pending_units"] == 2

    def test_average_only_counts_the_given_subject(self):
        """
        Test that another subarea's grades don't leak into this subject's average.
        """
        cycle = AcademicCycleFactory()
        units = self._units(cycle, 2)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        other_subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()

        register_unit_grade(
            enrolment=enrolment,
            subject=subject,
            evaluation_unit=units[0],
            teacher=teacher,
            value=70,
        )
        register_unit_grade(
            enrolment=enrolment,
            subject=other_subject,
            evaluation_unit=units[1],
            teacher=teacher,
            value=40,
        )

        result = get_current_average(enrolment, subject)

        assert result["average"] == 70
        assert result["graded_units"] == 1


class TestGetFinalSubjectGrade:
    """Tests for RF-RES-001: Nota final de la subárea."""

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
                create_evaluation_unit(
                    academic_cycle=cycle,
                    number=i + 1,
                    name=f"Unit {i + 1}",
                    starts_on=starts,
                    ends_on=starts + timedelta(days=60),
                    capture_starts_on=today - timedelta(days=5),
                    capture_ends_on=today + timedelta(days=5),
                )
            )
        return units

    def test_final_grade_is_the_average_of_all_graded_units(self):
        """
        Scenario 12: Promedio de las unidades
        GIVEN un estudiante con todas las unidades calificadas en una subárea
        WHEN se calcula su nota final
        THEN el resultado es el promedio de esas notas
        """
        cycle = AcademicCycleFactory()
        units = self._units(cycle, 3)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()

        for unit, value in zip(units, (60, 75, 90), strict=True):
            register_unit_grade(
                enrolment=enrolment,
                subject=subject,
                evaluation_unit=unit,
                teacher=teacher,
                value=value,
            )

        result = get_final_subject_grade(enrolment, subject)

        assert result["average"] == 75
        assert result["graded_units"] == 3
        assert result["pending_units"] == 0

    def test_final_grade_recalculates_on_correction(self):
        """
        Test that the final grade, while the cycle is open, recalculates on
        every correction (comportamiento exigido) rather than freezing after
        the first computation.
        """
        cycle = AcademicCycleFactory()
        units = self._units(cycle, 2)
        enrolment = self._enrolment(cycle)
        subject = SubjectFactory(institution=cycle.institution)
        teacher = PersonFactory()

        register_unit_grade(
            enrolment=enrolment,
            subject=subject,
            evaluation_unit=units[0],
            teacher=teacher,
            value=60,
        )
        register_unit_grade(
            enrolment=enrolment,
            subject=subject,
            evaluation_unit=units[1],
            teacher=teacher,
            value=60,
        )
        assert get_final_subject_grade(enrolment, subject)["average"] == 60

        # A correction to an already-registered unit changes the final grade.
        register_unit_grade(
            enrolment=enrolment,
            subject=subject,
            evaluation_unit=units[0],
            teacher=teacher,
            value=100,
        )

        assert get_final_subject_grade(enrolment, subject)["average"] == 80
