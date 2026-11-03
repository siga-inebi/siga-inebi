"""
#631, PR 1: ciclo escolar editable, volver a borrador, preparación y días no computables.

C3 (editar borrador), D3/D6 (volver a borrador solo sin actividad, RF-CIC-008),
C7 (lista de verificación estructurada) y C8 (RF-JOR-010).
"""

from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.academics import queries
from apps.academics.models import (
    AcademicCycle,
    CurriculumPlan,
    NonComputableDay,
    TeachingAssignment,
)
from apps.academics.services import (
    activate_academic_cycle,
    close_academic_cycle,
    declare_non_computable_day,
    remove_non_computable_day,
    revert_academic_cycle_to_draft,
    update_academic_cycle,
)
from apps.audit.models import AuditEvent
from apps.common.exceptions import DomainError
from apps.documents.models import DocumentIssuance
from apps.enrolments.models import Enrolment
from apps.evaluation.models import EvaluationUnit, Grade
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    GradeOfferingFactory,
    InstitutionFactory,
    SectionFactory,
    ShiftFactory,
    SubjectFactory,
)
from tests.factories.attendance import AttendanceEventFactory
from tests.factories.evaluation import EvaluationUnitFactory
from tests.factories.identity import UserFactory
from tests.factories.students import StudentFactory
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

YEAR = 2031


def _cycle(status, *, institution=None, year=YEAR):
    return AcademicCycleFactory(
        institution=institution or InstitutionFactory(),
        year=year,
        name=f"Ciclo {year}",
        starts_on=date(year, 1, 15),
        ends_on=date(year, 10, 31),
        status=status,
    )


def _complete_structure(cycle):
    """One offering, one section, one subject in the plan and its current teacher."""
    offering = GradeOfferingFactory(academic_cycle=cycle)
    section = SectionFactory(academic_cycle=cycle, grade=offering.grade, shift=offering.shift)
    subject = SubjectFactory(institution=cycle.institution)
    plan = CurriculumPlan.objects.create(
        academic_cycle=cycle, grade=offering.grade, subject=subject
    )
    assignment = TeachingAssignment.objects.create(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=TeacherFactory().person,
        starts_on=cycle.starts_on,
    )
    return offering, section, subject, plan, assignment


def _enrolment(cycle, section=None):
    section = section or SectionFactory(academic_cycle=cycle)
    return Enrolment.objects.create(
        student=StudentFactory(),
        academic_cycle=cycle,
        grade=section.grade,
        section=section,
    )


# --------------------------------------------------------------------------- #
# C3: editar un ciclo en borrador
# --------------------------------------------------------------------------- #


def test_update_draft_cycle_changes_fields_and_audits_before_and_after():
    cycle = _cycle(AcademicCycle.CycleStatus.DRAFT)
    actor = UserFactory()

    updated = update_academic_cycle(
        cycle=cycle,
        name="  Ciclo lectivo 2031  ",
        description="Calendario ajustado",
        ends_on=date(YEAR, 10, 15),
        actor=actor,
    )

    updated.refresh_from_db()
    assert updated.name == "Ciclo lectivo 2031"
    assert updated.description == "Calendario ajustado"
    assert updated.ends_on == date(YEAR, 10, 15)
    event = AuditEvent.objects.get(action="academics.cycle.updated")
    assert event.actor == actor
    assert event.context["changes"]["ends_on"] == {"before": "2031-10-31", "after": "2031-10-15"}
    assert event.context["changes"]["name"]["after"] == "Ciclo lectivo 2031"


def test_update_cycle_changes_year_with_matching_dates():
    cycle = _cycle(AcademicCycle.CycleStatus.DRAFT)

    updated = update_academic_cycle(
        cycle=cycle,
        year=YEAR + 1,
        starts_on=date(YEAR + 1, 1, 15),
        ends_on=date(YEAR + 1, 10, 30),
    )

    assert (updated.year, updated.starts_on) == (YEAR + 1, date(YEAR + 1, 1, 15))


def test_update_cycle_without_changes_writes_no_audit_event():
    cycle = _cycle(AcademicCycle.CycleStatus.DRAFT)

    update_academic_cycle(cycle=cycle, name=cycle.name)

    assert not AuditEvent.objects.filter(action="academics.cycle.updated").exists()


@pytest.mark.parametrize(
    "status", [AcademicCycle.CycleStatus.ACTIVE, AcademicCycle.CycleStatus.CLOSED]
)
def test_update_cycle_rejects_cycles_that_are_not_in_preparation(status):
    cycle = _cycle(status)

    with pytest.raises(DomainError, match="Solo se puede editar un ciclo escolar en preparación"):
        update_academic_cycle(cycle=cycle, name="Otro nombre")


def test_update_cycle_rejects_year_that_does_not_match_start_date():
    cycle = _cycle(AcademicCycle.CycleStatus.DRAFT)

    with pytest.raises(DomainError, match="año del ciclo escolar"):
        update_academic_cycle(cycle=cycle, year=YEAR + 1)


def test_update_cycle_rejects_inverted_dates():
    cycle = _cycle(AcademicCycle.CycleStatus.DRAFT)

    with pytest.raises(DomainError, match="fecha de fin"):
        update_academic_cycle(cycle=cycle, ends_on=date(YEAR, 1, 1))


def test_update_cycle_rejects_name_used_by_another_cycle():
    cycle = _cycle(AcademicCycle.CycleStatus.DRAFT)
    _cycle(AcademicCycle.CycleStatus.CLOSED, institution=cycle.institution, year=YEAR - 1)

    with pytest.raises(DomainError):
        update_academic_cycle(cycle=cycle, name=f"Ciclo {YEAR - 1}")

    cycle.refresh_from_db()
    assert cycle.name == f"Ciclo {YEAR}"


# --------------------------------------------------------------------------- #
# D3/D6: volver a borrador (RF-CIC-008)
# --------------------------------------------------------------------------- #


def test_revert_active_cycle_without_activity_keeps_structure_and_audits_reason():
    cycle = _cycle(AcademicCycle.CycleStatus.ACTIVE)
    offering, section, _subject, plan, assignment = _complete_structure(cycle)
    actor = UserFactory()

    reverted = revert_academic_cycle_to_draft(
        academic_cycle=cycle, reason="  Se activó antes de tiempo  ", actor=actor
    )

    assert reverted.status == AcademicCycle.CycleStatus.DRAFT
    cycle.refresh_from_db()
    assert cycle.status == AcademicCycle.CycleStatus.DRAFT
    assert cycle.grade_offerings.get() == offering
    assert cycle.grade_offerings.get().sections.get() == section
    assert cycle.curriculum_plans.get() == plan
    assert cycle.teaching_assignments.get() == assignment
    event = AuditEvent.objects.get(action="academics.cycle.reverted_to_draft")
    assert event.actor == actor
    assert event.context["reason"] == "Se activó antes de tiempo"
    assert event.context["previous_status"] == "active"


def test_reverted_cycle_can_be_activated_again():
    cycle = _cycle(AcademicCycle.CycleStatus.ACTIVE)
    _complete_structure(cycle)

    revert_academic_cycle_to_draft(academic_cycle=cycle, reason="Error de fechas")
    activated = activate_academic_cycle(cycle=cycle)

    assert activated.status == AcademicCycle.CycleStatus.ACTIVE


@pytest.mark.parametrize("reason", ["", "   ", None])
def test_revert_requires_reason(reason):
    cycle = _cycle(AcademicCycle.CycleStatus.ACTIVE)

    with pytest.raises(DomainError, match="motivo"):
        revert_academic_cycle_to_draft(academic_cycle=cycle, reason=reason)

    cycle.refresh_from_db()
    assert cycle.status == AcademicCycle.CycleStatus.ACTIVE


@pytest.mark.parametrize(
    "status", [AcademicCycle.CycleStatus.DRAFT, AcademicCycle.CycleStatus.CLOSED]
)
def test_revert_only_accepts_active_cycles(status):
    cycle = _cycle(status)

    with pytest.raises(
        DomainError, match="Solo se puede volver a borrador un ciclo escolar activo"
    ):
        revert_academic_cycle_to_draft(academic_cycle=cycle, reason="Motivo")


def _with_enrolment(cycle):
    _enrolment(cycle)


def _with_grade(cycle):
    enrolment = _enrolment(cycle)
    unit = EvaluationUnitFactory(academic_cycle=cycle)
    Grade.objects.create(
        enrolment=enrolment,
        subject=SubjectFactory(institution=cycle.institution),
        evaluation_unit=unit,
        value=80,
    )


def _with_attendance(cycle):
    shift = ShiftFactory(campus=CampusFactory(institution=cycle.institution))
    AttendanceEventFactory(shift=shift, event_date=cycle.starts_on + timedelta(days=3))


def _with_closed_unit(cycle):
    EvaluationUnitFactory(academic_cycle=cycle, status=EvaluationUnit.UnitStatus.CLOSED)


def _with_issued_document(cycle):
    enrolment = _enrolment(cycle)
    DocumentIssuance.objects.create(
        student=enrolment.student,
        enrolment=enrolment,
        document_type=DocumentIssuance.DocumentType.ENROLMENT_CERTIFICATE,
        folio="F-0001",
        verification_code="verificacion-0001",
        checksum="0" * 64,
        size_bytes=10,
        issued_at=timezone.now(),
    )


@pytest.mark.parametrize(
    ("arrange", "code"),
    [
        (_with_enrolment, "enrolments"),
        (_with_grade, "grades"),
        (_with_attendance, "attendance_events"),
        (_with_closed_unit, "closed_evaluation_units"),
        (_with_issued_document, "issued_documents"),
    ],
)
def test_revert_is_blocked_by_each_kind_of_activity(arrange, code):
    cycle = _cycle(AcademicCycle.CycleStatus.ACTIVE)
    arrange(cycle)

    blockers = queries.academic_cycle_revert_blockers(cycle)
    assert code in {blocker["code"] for blocker in blockers}

    with pytest.raises(DomainError, match="ya tiene actividad"):
        revert_academic_cycle_to_draft(academic_cycle=cycle, reason="Motivo")

    cycle.refresh_from_db()
    assert cycle.status == AcademicCycle.CycleStatus.ACTIVE
    assert not AuditEvent.objects.filter(action="academics.cycle.reverted_to_draft").exists()


def test_revert_blockers_count_and_message_in_spanish():
    cycle = _cycle(AcademicCycle.CycleStatus.ACTIVE)
    section = SectionFactory(academic_cycle=cycle)
    _enrolment(cycle, section)
    _enrolment(cycle, section)

    blockers = queries.academic_cycle_revert_blockers(cycle)

    assert blockers == [{"code": "enrolments", "count": 2, "message": "Tiene 2 matrículas."}]


def test_revert_blockers_singular_message():
    cycle = _cycle(AcademicCycle.CycleStatus.ACTIVE)
    _with_closed_unit(cycle)

    assert queries.academic_cycle_revert_blockers(cycle)[0]["message"] == (
        "Tiene 1 unidad de evaluación cerrada."
    )


def test_open_evaluation_unit_does_not_block_revert():
    cycle = _cycle(AcademicCycle.CycleStatus.ACTIVE)
    EvaluationUnitFactory(academic_cycle=cycle, status=EvaluationUnit.UnitStatus.OPEN)

    assert queries.academic_cycle_revert_blockers(cycle) == []


def test_attendance_outside_cycle_dates_or_institution_does_not_block_revert():
    cycle = _cycle(AcademicCycle.CycleStatus.ACTIVE)
    own_shift = ShiftFactory(campus=CampusFactory(institution=cycle.institution))
    AttendanceEventFactory(shift=own_shift, event_date=cycle.ends_on + timedelta(days=1))
    AttendanceEventFactory(shift=ShiftFactory(), event_date=cycle.starts_on)

    assert queries.academic_cycle_revert_blockers(cycle) == []


# --------------------------------------------------------------------------- #
# C7: preparación estructurada (lista de verificación)
# --------------------------------------------------------------------------- #


def test_opening_gaps_are_structured_with_references():
    cycle = _cycle(AcademicCycle.CycleStatus.DRAFT)
    offering = GradeOfferingFactory(academic_cycle=cycle)
    section = SectionFactory(academic_cycle=cycle, grade=offering.grade, shift=offering.shift)
    subject = SubjectFactory(institution=cycle.institution, name="Matemática")
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=offering.grade, subject=subject)

    gaps = queries.academic_cycle_opening_gaps(cycle)

    assert gaps == [
        {
            "code": "missing_teacher",
            "message": (
                f"Falta asignar docente para 'Matemática' en la sección '{section.name}' "
                f"del grado '{offering.grade.name}'."
            ),
            "grade": offering.grade,
            "section": section,
            "subject": subject,
        }
    ]


def test_opening_gaps_report_missing_offerings_sections_and_plan():
    empty = _cycle(AcademicCycle.CycleStatus.DRAFT)
    assert [gap["code"] for gap in queries.academic_cycle_opening_gaps(empty)] == [
        "no_grade_offerings"
    ]

    cycle = _cycle(AcademicCycle.CycleStatus.DRAFT, year=YEAR + 1)
    GradeOfferingFactory(academic_cycle=cycle)
    codes = [gap["code"] for gap in queries.academic_cycle_opening_gaps(cycle)]
    assert codes == ["missing_sections", "missing_curriculum_plan"]


def test_activation_error_message_joins_structured_gaps():
    cycle = _cycle(AcademicCycle.CycleStatus.DRAFT)
    offering = GradeOfferingFactory(academic_cycle=cycle)

    with pytest.raises(DomainError) as error:
        activate_academic_cycle(cycle=cycle)

    assert str(error.value) == (
        "La estructura del ciclo escolar está incompleta: faltan secciones del grado "
        f"'{offering.grade.name}' en la jornada '{offering.shift.name}'; falta el plan de "
        f"estudios del grado '{offering.grade.name}'."
    )


def test_closure_error_message_keeps_unit_names():
    cycle = _cycle(AcademicCycle.CycleStatus.ACTIVE)
    unit = EvaluationUnitFactory(academic_cycle=cycle, status=EvaluationUnit.UnitStatus.OPEN)

    with pytest.raises(DomainError) as error:
        close_academic_cycle(cycle=cycle)

    assert str(error.value) == (
        f"No se puede cerrar el ciclo escolar: la unidad de evaluación '{unit.name}' sigue abierta."
    )


def test_readiness_of_draft_cycle_reports_other_active_cycle():
    active = _cycle(AcademicCycle.CycleStatus.ACTIVE)
    draft = _cycle(AcademicCycle.CycleStatus.DRAFT, institution=active.institution, year=YEAR + 1)
    _complete_structure(draft)

    readiness = queries.academic_cycle_readiness(draft)

    assert readiness["active_cycle"] == active
    assert readiness["activation"]["ready"] is False
    assert [gap["code"] for gap in readiness["activation"]["gaps"]] == ["active_cycle_exists"]
    assert readiness["revert"]["allowed"] is False
    assert readiness["close"]["ready"] is False


def test_readiness_of_active_cycle_without_activity():
    cycle = _cycle(AcademicCycle.CycleStatus.ACTIVE)

    readiness = queries.academic_cycle_readiness(cycle)

    assert readiness["active_cycle"] is None
    assert readiness["activation"]["ready"] is False
    assert readiness["revert"] == {"allowed": True, "blockers": []}
    assert readiness["close"] == {"ready": True, "gaps": []}


def test_readiness_of_complete_draft_is_ready():
    cycle = _cycle(AcademicCycle.CycleStatus.DRAFT)
    _complete_structure(cycle)

    readiness = queries.academic_cycle_readiness(cycle)

    assert readiness["activation"] == {"ready": True, "gaps": []}


# --------------------------------------------------------------------------- #
# C8: días no computables (RF-JOR-010)
# --------------------------------------------------------------------------- #


def test_remove_non_computable_day_deactivates_and_audits():
    cycle = _cycle(AcademicCycle.CycleStatus.ACTIVE)
    record = declare_non_computable_day(
        academic_cycle=cycle, day=date(YEAR, 3, 2), reason="Asueto local"
    )
    actor = UserFactory()

    remove_non_computable_day(record=record, actor=actor)

    record.refresh_from_db()
    assert record.is_active is False
    assert list(queries.non_computable_days(cycle)) == []
    event = AuditEvent.objects.get(action="academics.non_computable_day.removed")
    assert event.actor == actor
    assert event.context["day"] == "2031-03-02"


def test_redeclaring_a_removed_day_reactivates_the_same_row():
    cycle = _cycle(AcademicCycle.CycleStatus.ACTIVE)
    record = declare_non_computable_day(
        academic_cycle=cycle, day=date(YEAR, 3, 2), reason="Asueto local"
    )
    remove_non_computable_day(record=record)

    again = declare_non_computable_day(
        academic_cycle=cycle, day=date(YEAR, 3, 2), reason="Feria patronal"
    )

    assert again.pk == record.pk
    assert again.is_active is True
    assert again.reason == "Feria patronal"
    assert NonComputableDay.objects.filter(academic_cycle=cycle).count() == 1


def test_declaring_an_active_day_twice_is_rejected():
    cycle = _cycle(AcademicCycle.CycleStatus.ACTIVE)
    declare_non_computable_day(academic_cycle=cycle, day=date(YEAR, 3, 2), reason="Asueto")

    with pytest.raises(DomainError, match="ya está declarado"):
        declare_non_computable_day(academic_cycle=cycle, day=date(YEAR, 3, 2), reason="Otro")


def test_remove_non_computable_day_rejects_closed_cycle():
    cycle = _cycle(AcademicCycle.CycleStatus.ACTIVE)
    record = declare_non_computable_day(
        academic_cycle=cycle, day=date(YEAR, 3, 2), reason="Asueto local"
    )
    AcademicCycle.objects.filter(pk=cycle.pk).update(status=AcademicCycle.CycleStatus.CLOSED)

    with pytest.raises(DomainError, match="ciclo escolar cerrado"):
        remove_non_computable_day(record=record)

    record.refresh_from_db()
    assert record.is_active is True


def test_non_computable_days_are_listed_by_date():
    cycle = _cycle(AcademicCycle.CycleStatus.DRAFT)
    later = declare_non_computable_day(academic_cycle=cycle, day=date(YEAR, 9, 15), reason="A")
    earlier = declare_non_computable_day(academic_cycle=cycle, day=date(YEAR, 5, 1), reason="B")

    assert list(queries.non_computable_days(cycle)) == [earlier, later]
