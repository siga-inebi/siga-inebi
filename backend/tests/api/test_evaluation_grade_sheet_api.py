"""
API contract of the evaluation UX delivery of #631 (docs/ux-ui.md 2.11, V1-V8).

- V2: names in the grade list and its filters, the grade sheet (GET) and its
  batch save (POST), sharing bulk_register_unit_grades with the CSV upload.
- V8: the teacher is inferred from the current teaching assignment.
- V3: capture progress without N+1.
- V4: recovery eligibility of a whole section.
- V5: names in the report card grades and every frozen result in one call.
- Unit serializer: academic_cycle_id and the recovery window at creation.
"""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.academics.models import CurriculumPlan, FrozenSubjectResult, TeachingAssignment
from apps.audit.models import AuditEvent
from apps.enrolments.services import create_enrolment
from apps.evaluation.models import EvaluationUnit, Grade
from apps.evaluation.services import register_unit_grade
from tests.factories.academic import AcademicCycleFactory, SectionFactory, SubjectFactory
from tests.factories.evaluation import grant_scoped_permission, open_unit
from tests.factories.people import PersonFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

ATTENDANCE_SERVICE_PATH = "apps.attendance.services.compute_attendance_percentage"


def _enrol(cycle, section, *, first_name="Ana", last_name="Zeta"):
    student = StudentFactory(person=PersonFactory(first_name=first_name, last_name=last_name))
    return create_enrolment(
        student=student, academic_cycle=cycle, grade=section.grade, section=section
    )


def _world(user, institution, *, names=(("Ana", "Zeta"), ("Beto", "Alba"), ("Ciro", "Mora"))):
    """
    A cycle with one section, one subarea in its plan, an open unit and the
    requesting user as the teacher of the current assignment, holding
    grade.write (their scope is the teaching assignment).
    """
    cycle = AcademicCycleFactory(institution=institution)
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory(institution=institution, name="Matemática")
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=section.grade, subject=subject)
    unit = open_unit(cycle)
    enrolments = [_enrol(cycle, section, first_name=f, last_name=last) for f, last in names]
    TeachingAssignment.objects.create(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=user.person,
        starts_on=cycle.starts_on,
    )
    grant_scoped_permission(user, "grade_write")
    return SimpleNamespace(
        cycle=cycle, section=section, subject=subject, unit=unit, enrolments=enrolments
    )


def _unit_url(name, world, **extra):
    return reverse(
        name,
        kwargs={
            "cycle_public_id": str(world.cycle.public_id),
            "unit_public_id": str(world.unit.public_id),
            **extra,
        },
    )


class TestGradeListNames:
    """V2: the grade list carries names and accepts section/subject/student filters."""

    def test_grades_include_student_subject_and_unit_ids(self, auth_client, institution):
        world = _world(auth_client.user, institution)
        enrolment = world.enrolments[0]
        Grade.objects.create(
            enrolment=enrolment, subject=world.subject, evaluation_unit=world.unit, value=88
        )

        response = auth_client.get(_unit_url("evaluation-unit-grades", world))

        assert response.status_code == 200
        grade = response.json()["results"][0]
        assert grade["enrolment"] == str(enrolment.public_id)
        assert grade["subject"] == str(world.subject.public_id)
        assert grade["student"] == {
            "public_id": str(enrolment.student.public_id),
            "student_code": enrolment.student.student_code,
            "full_name": "Ana Zeta",
        }
        assert grade["subject_detail"] == {
            "public_id": str(world.subject.public_id),
            "name": "Matemática",
        }
        assert grade["evaluation_unit_id"] == str(world.unit.public_id)
        assert grade["evaluation_unit"] == world.unit.pk

    def test_filters_by_section_subject_and_student(self, auth_client, institution):
        world = _world(auth_client.user, institution)
        other_subject = SubjectFactory(institution=institution)
        for enrolment in world.enrolments:
            Grade.objects.create(
                enrolment=enrolment, subject=world.subject, evaluation_unit=world.unit, value=70
            )
        Grade.objects.create(
            enrolment=world.enrolments[0],
            subject=other_subject,
            evaluation_unit=world.unit,
            value=60,
        )
        url = _unit_url("evaluation-unit-grades", world)

        by_subject = auth_client.get(url, {"subject_id": str(world.subject.public_id)})
        by_student = auth_client.get(
            url,
            {
                "student_id": str(world.enrolments[1].student.public_id),
                "section_id": str(world.section.public_id),
            },
        )
        unknown = auth_client.get(url, {"section_id": str(other_subject.public_id)})
        malformed = auth_client.get(url, {"section_id": "no-es-uuid"})

        assert by_subject.json()["count"] == 3
        assert by_student.json()["count"] == 1
        assert by_student.json()["results"][0]["student"]["full_name"] == "Beto Alba"
        assert unknown.json()["count"] == 0
        assert malformed.status_code == 400

    def test_listing_cost_does_not_grow_with_rows(self, auth_client, institution):
        world = _world(auth_client.user, institution, names=(("Ana", "Zeta"),))
        url = _unit_url("evaluation-unit-grades", world)
        Grade.objects.create(
            enrolment=world.enrolments[0],
            subject=world.subject,
            evaluation_unit=world.unit,
            value=70,
        )
        with CaptureQueriesContext(connection) as one_row:
            assert auth_client.get(url).status_code == 200

        for index in range(5):
            enrolment = _enrol(world.cycle, world.section, first_name=f"N{index}")
            Grade.objects.create(
                enrolment=enrolment, subject=world.subject, evaluation_unit=world.unit, value=70
            )
        with CaptureQueriesContext(connection) as six_rows:
            response = auth_client.get(url)

        assert response.json()["count"] == 6
        assert len(six_rows) == len(one_row)


class TestGradeSheet:
    """V2/V8: everything the grid needs in one call."""

    def test_sheet_rows_by_name_with_grade_or_null_and_inferred_teacher(
        self, auth_client, institution
    ):
        world = _world(auth_client.user, institution)
        ana = world.enrolments[0]
        grade = Grade.objects.create(
            enrolment=ana, subject=world.subject, evaluation_unit=world.unit, value=91
        )

        response = auth_client.get(
            _unit_url("evaluation-unit-sheet", world),
            {
                "section_id": str(world.section.public_id),
                "subject_id": str(world.subject.public_id),
            },
        )

        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["unit"] == {
            "public_id": str(world.unit.public_id),
            "name": world.unit.name,
            "status": "open",
            "window_open": True,
        }
        assert data["section"]["public_id"] == str(world.section.public_id)
        assert data["subject"] == {"public_id": str(world.subject.public_id), "name": "Matemática"}
        assert data["teacher"] == {
            "public_id": str(auth_client.user.person.public_id),
            "name": str(auth_client.user.person),
        }
        assert [row["student"]["full_name"] for row in data["rows"]] == [
            "Beto Alba",
            "Ciro Mora",
            "Ana Zeta",
        ]
        ana_row = data["rows"][2]
        assert ana_row["enrolment_id"] == str(ana.public_id)
        assert ana_row["grade"] == {"public_id": str(grade.public_id), "value": 91}
        assert data["rows"][0]["grade"] is None

    def test_sheet_cost_does_not_grow_with_students(self, auth_client, institution):
        world = _world(auth_client.user, institution, names=(("Ana", "Zeta"),))
        url = _unit_url("evaluation-unit-sheet", world)
        params = {
            "section_id": str(world.section.public_id),
            "subject_id": str(world.subject.public_id),
        }
        with CaptureQueriesContext(connection) as small:
            assert auth_client.get(url, params).status_code == 200
        for index in range(6):
            enrolment = _enrol(world.cycle, world.section, first_name=f"N{index}")
            Grade.objects.create(
                enrolment=enrolment, subject=world.subject, evaluation_unit=world.unit, value=70
            )
        with CaptureQueriesContext(connection) as large:
            response = auth_client.get(url, params)

        assert len(response.json()["rows"]) == 7
        assert len(large) == len(small)

    def test_sheet_requires_section_and_subject(self, auth_client, institution):
        world = _world(auth_client.user, institution)

        response = auth_client.get(_unit_url("evaluation-unit-sheet", world))

        assert response.status_code == 400

    def test_section_of_another_cycle_is_not_found(self, auth_client, institution):
        world = _world(auth_client.user, institution)
        foreign = SectionFactory(academic_cycle=AcademicCycleFactory())

        response = auth_client.get(
            _unit_url("evaluation-unit-sheet", world),
            {"section_id": str(foreign.public_id), "subject_id": str(world.subject.public_id)},
        )

        assert response.status_code == 404

    def test_sheet_never_truncates_silently(self, auth_client, institution):
        world = _world(auth_client.user, institution)

        with patch("apps.evaluation.services.GRADE_SHEET_MAX_ROWS", 2):
            response = auth_client.get(
                _unit_url("evaluation-unit-sheet", world),
                {
                    "section_id": str(world.section.public_id),
                    "subject_id": str(world.subject.public_id),
                },
            )

        assert response.status_code == 400
        assert "más de 2" in response.json()["error"]["detail"]


class TestGradeSheetSave:
    """V2: JSON batch save, all-or-nothing, same rules as the CSV upload."""

    def _post(self, client, world, grades, **extra):
        return client.post(
            _unit_url("evaluation-unit-grades-sheet", world),
            {
                "section_id": str(world.section.public_id),
                "subject_id": str(world.subject.public_id),
                "grades": grades,
                **extra,
            },
            content_type="application/json",
        )

    def test_creates_and_corrects_with_inferred_teacher(self, auth_client, institution):
        world = _world(auth_client.user, institution)
        ana, beto, ciro = world.enrolments
        register_unit_grade(
            enrolment=ana,
            subject=world.subject,
            evaluation_unit=world.unit,
            teacher=None,
            value=50,
        )

        response = self._post(
            auth_client,
            world,
            [
                {"enrolment_id": str(ana.public_id), "value": 65},
                {"enrolment_id": str(beto.public_id), "value": 80},
                {"student_code": ciro.student.student_code, "value": "90"},
            ],
        )

        assert response.status_code == 200, response.json()
        assert response.json() == {"created": 2, "updated": 1}
        assert Grade.objects.get(enrolment=ana, subject=world.subject).value == 65
        correction = AuditEvent.objects.filter(action="evaluation.grade_updated").latest(
            "created_at"
        )
        assert correction.context["teacher_id"] == str(auth_client.user.person.public_id)
        summary = AuditEvent.objects.get(action="evaluation.grades_bulk_registered")
        assert summary.context["updated"] == 1

    def test_any_invalid_entry_writes_nothing_and_reports_by_index(self, auth_client, institution):
        world = _world(auth_client.user, institution)
        ana, beto, _ciro = world.enrolments

        response = self._post(
            auth_client,
            world,
            [
                {"enrolment_id": str(ana.public_id), "value": 70},
                {"enrolment_id": str(beto.public_id), "value": 101},
                {"student_code": "NO-EXISTE", "value": 80},
                {"enrolment_id": str(ana.public_id), "value": 75},
                {"enrolment_id": str(beto.public_id), "value": 70.5},
            ],
        )

        assert response.status_code == 400
        errors = response.json()["errors"]
        assert [(e["index"], e["field"]) for e in errors] == [
            (1, "value"),
            (2, "student_code"),
            (3, "student_code"),
            (4, "student_code"),
        ]
        assert errors[0]["student_code"] == beto.student.student_code
        assert "entre 0 y 100" in errors[0]["message"]
        assert Grade.objects.filter(evaluation_unit=world.unit).count() == 0

    def test_fraction_is_rejected_not_rounded(self, auth_client, institution):
        world = _world(auth_client.user, institution)

        response = self._post(
            auth_client,
            world,
            [{"enrolment_id": str(world.enrolments[0].public_id), "value": 70.5}],
        )

        assert response.status_code == 400
        assert response.json()["errors"][0]["field"] == "value"

    def test_correction_with_closed_window_is_rejected(self, auth_client, institution):
        world = _world(auth_client.user, institution)
        enrolment = world.enrolments[0]
        register_unit_grade(
            enrolment=enrolment,
            subject=world.subject,
            evaluation_unit=world.unit,
            teacher=None,
            value=50,
        )
        yesterday = timezone.localdate() - timedelta(days=1)
        EvaluationUnit.objects.filter(pk=world.unit.pk).update(capture_ends_on=yesterday)

        response = self._post(
            auth_client, world, [{"enrolment_id": str(enrolment.public_id), "value": 99}]
        )

        assert response.status_code == 400
        assert "cerrada" in response.json()["error"]["detail"]
        assert Grade.objects.get(enrolment=enrolment).value == 50

    def test_without_teacher_and_without_assignment_is_rejected(self, auth_client, institution):
        world = _world(auth_client.user, institution)
        TeachingAssignment.objects.all().delete()
        # Administrative scope over the section instead of a teaching assignment.
        grant_scoped_permission(auth_client.user, "grade_write", section=world.section)

        response = self._post(
            auth_client, world, [{"enrolment_id": str(world.enrolments[0].public_id), "value": 70}]
        )

        assert response.status_code == 400
        assert "no tiene docente asignado" in response.json()["error"]["detail"]

    def test_explicit_teacher_still_accepted(self, auth_client, institution):
        world = _world(auth_client.user, institution)
        substitute = PersonFactory()

        response = self._post(
            auth_client,
            world,
            [{"enrolment_id": str(world.enrolments[0].public_id), "value": 70}],
            teacher_id=str(substitute.public_id),
        )

        assert response.status_code == 200
        event = AuditEvent.objects.get(action="evaluation.grade_registered")
        assert event.context["teacher_id"] == str(substitute.public_id)

    def test_empty_batch_is_rejected(self, auth_client, institution):
        world = _world(auth_client.user, institution)

        assert self._post(auth_client, world, []).status_code == 400


class TestTeacherInference:
    """V8: single grade and CSV upload no longer need the teacher."""

    def test_single_grade_without_teacher(self, auth_client, institution):
        world = _world(auth_client.user, institution)

        response = auth_client.post(
            _unit_url("evaluation-unit-grades", world),
            {
                "enrolment": str(world.enrolments[0].public_id),
                "subject": str(world.subject.public_id),
                "value": 77,
            },
            content_type="application/json",
        )

        assert response.status_code == 201, response.json()
        assert response.json()["student"]["full_name"] == "Ana Zeta"
        event = AuditEvent.objects.get(action="evaluation.grade_registered")
        assert event.context["teacher_id"] == str(auth_client.user.person.public_id)

    def test_csv_without_teacher(self, auth_client, institution):
        from django.core.files.uploadedfile import SimpleUploadedFile

        world = _world(auth_client.user, institution)
        body = "student_code,value\n" + "\n".join(
            f"{enrolment.student.student_code},80" for enrolment in world.enrolments
        )

        response = auth_client.post(
            _unit_url("evaluation-unit-grades-bulk", world),
            {
                "file": SimpleUploadedFile("notas.csv", body.encode(), content_type="text/csv"),
                "subject": str(world.subject.public_id),
                "section": str(world.section.public_id),
            },
        )

        assert response.status_code == 200, response.json()
        assert response.json() == {"created": 3, "updated": 0}

    def test_csv_errors_keep_their_row_shape(self, auth_client, institution):
        from django.core.files.uploadedfile import SimpleUploadedFile

        world = _world(auth_client.user, institution)
        body = "student_code,value\nNO-EXISTE,80\n"

        response = auth_client.post(
            _unit_url("evaluation-unit-grades-bulk", world),
            {
                "file": SimpleUploadedFile("notas.csv", body.encode(), content_type="text/csv"),
                "subject": str(world.subject.public_id),
                "section": str(world.section.public_id),
            },
        )

        assert response.status_code == 400
        assert response.json()["created"] == 0
        assert set(response.json()["errors"][0]) == {"row", "field", "message"}
        assert response.json()["errors"][0]["row"] == 1


class TestCaptureProgressCost:
    """V3: the panel reads a fixed number of queries whatever the cycle size."""

    def test_capture_progress_cost_does_not_grow(self, auth_client, institution):
        grant_scoped_permission(
            auth_client.user, "evaluation_configure_units", institution=institution
        )
        world = _world(auth_client.user, institution, names=(("Ana", "Zeta"),))
        url = _unit_url("evaluation-unit-capture-progress", world)
        with CaptureQueriesContext(connection) as small:
            assert auth_client.get(url).status_code == 200

        for _ in range(3):
            section = SectionFactory(academic_cycle=world.cycle, grade=world.section.grade)
            enrolment = _enrol(world.cycle, section)
            TeachingAssignment.objects.create(
                academic_cycle=world.cycle,
                section=section,
                subject=world.subject,
                teacher=PersonFactory(),
                starts_on=world.cycle.starts_on,
            )
            Grade.objects.create(
                enrolment=enrolment, subject=world.subject, evaluation_unit=world.unit, value=70
            )
        with CaptureQueriesContext(connection) as large:
            response = auth_client.get(url)

        assert len(response.json()["rows"]) == 4
        assert len(large) == len(small)
        graded = [row for row in response.json()["rows"] if row["students_graded"] == 1]
        assert len(graded) == 3
        assert all(row["teacher"] is not None for row in response.json()["rows"])


class TestSectionRecoveryEligibility:
    """V4: eligibility of a whole section, reusing the per-enrolment rules."""

    def test_rows_with_failed_subjects(self, auth_client, institution):
        world = _world(auth_client.user, institution)
        grant_scoped_permission(auth_client.user, "student_view_basic", institution=institution)
        failing = world.enrolments[0]
        register_unit_grade(
            enrolment=failing,
            subject=world.subject,
            evaluation_unit=world.unit,
            teacher=None,
            value=40,
        )
        for enrolment in world.enrolments[1:]:
            register_unit_grade(
                enrolment=enrolment,
                subject=world.subject,
                evaluation_unit=world.unit,
                teacher=None,
                value=80,
            )

        with patch(ATTENDANCE_SERVICE_PATH, return_value=SimpleNamespace(percentage=90.0)):
            response = auth_client.get(
                reverse(
                    "section-recovery-eligibility",
                    kwargs={
                        "cycle_public_id": str(world.cycle.public_id),
                        "section_id": str(world.section.public_id),
                    },
                ),
                {"page_size": 2},
            )

        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["count"] == 3
        assert len(data["results"]) == 2
        names = [row["student"]["full_name"] for row in data["results"]]
        assert names == ["Beto Alba", "Ciro Mora"]
        assert data["results"][0]["failed_subjects"] == []

        last = auth_client.get(
            reverse(
                "section-recovery-eligibility",
                kwargs={
                    "cycle_public_id": str(world.cycle.public_id),
                    "section_id": str(world.section.public_id),
                },
            ),
            {"page_size": 2, "page": 2},
        ).json()["results"][0]
        assert last["enrolment_id"] == str(failing.public_id)
        assert last["failed_subjects"] == [
            {"public_id": str(world.subject.public_id), "name": "Matemática", "final_grade": 40}
        ]
        assert last["failed_count"] == 1
        assert "eligible" in last
        assert "reasons" in last


class TestReportCard:
    """V5: names in the student's grades and every frozen result in one call."""

    def test_enrolment_grades_include_names(self, auth_client, institution):
        world = _world(auth_client.user, institution)
        grant_scoped_permission(auth_client.user, "student_view_basic", institution=institution)
        enrolment = world.enrolments[0]
        Grade.objects.create(
            enrolment=enrolment, subject=world.subject, evaluation_unit=world.unit, value=75
        )

        response = auth_client.get(
            reverse(
                "enrolment-grades",
                kwargs={
                    "cycle_public_id": str(world.cycle.public_id),
                    "enrolment_id": str(enrolment.public_id),
                },
            )
        )

        assert response.status_code == 200
        grade = response.json()[0]
        assert grade["subject_detail"]["name"] == "Matemática"
        assert grade["student"]["full_name"] == "Ana Zeta"

    def test_frozen_results_lists_current_value_per_subject(self, auth_client, institution):
        world = _world(auth_client.user, institution)
        enrolment = world.enrolments[0]
        biology = SubjectFactory(institution=institution, name="Biología")
        FrozenSubjectResult.objects.create(
            enrolment=enrolment, subject=world.subject, final_grade=55, condition="failed"
        )
        corrected = FrozenSubjectResult.objects.create(
            enrolment=enrolment,
            subject=world.subject,
            final_grade=61,
            condition="approved",
            is_correction=True,
            correction_reason="Error de digitación.",
        )
        FrozenSubjectResult.objects.create(
            enrolment=enrolment, subject=biology, final_grade=80, condition="approved"
        )

        response = auth_client.get(
            reverse(
                "frozen-subject-results",
                kwargs={
                    "cycle_public_id": str(world.cycle.public_id),
                    "enrolment_id": str(enrolment.public_id),
                },
            )
        )

        assert response.status_code == 200
        data = response.json()
        assert [row["subject_name"] for row in data] == ["Biología", "Matemática"]
        assert data[1]["public_id"] == str(corrected.public_id)
        assert data[1]["final_grade"] == 61

    def test_frozen_results_empty_before_close(self, auth_client, institution):
        world = _world(auth_client.user, institution)

        response = auth_client.get(
            reverse(
                "frozen-subject-results",
                kwargs={
                    "cycle_public_id": str(world.cycle.public_id),
                    "enrolment_id": str(world.enrolments[0].public_id),
                },
            )
        )

        assert response.status_code == 200
        assert response.json() == []


class TestEvaluationUnitContract:
    """academic_cycle_id and the recovery window at creation."""

    @pytest.fixture(autouse=True)
    def _configurator(self, auth_client, institution):
        grant_scoped_permission(
            auth_client.user, "evaluation_configure_units", institution=institution
        )

    def _payload(self, **extra):
        return {
            "number": 1,
            "name": "Unidad 1",
            "starts_on": "2026-01-15",
            "ends_on": "2026-03-15",
            "capture_starts_on": "2026-01-15",
            "capture_ends_on": "2026-03-20",
            **extra,
        }

    def _url(self, cycle):
        return reverse("evaluation-unit-list", kwargs={"cycle_public_id": str(cycle.public_id)})

    def test_recovery_window_is_kept_at_creation(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)

        response = auth_client.post(
            self._url(cycle),
            self._payload(recovery_starts_on="2026-03-21", recovery_ends_on="2026-03-28"),
            content_type="application/json",
        )

        assert response.status_code == 201, response.json()
        data = response.json()
        assert data["recovery_starts_on"] == "2026-03-21"
        assert data["recovery_ends_on"] == "2026-03-28"
        assert data["academic_cycle_id"] == str(cycle.public_id)
        assert AuditEvent.objects.filter(action="evaluation.unit_recovery_window_set").exists()

    def test_only_one_recovery_date_is_rejected_and_nothing_created(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)

        response = auth_client.post(
            self._url(cycle),
            self._payload(recovery_starts_on="2026-03-21"),
            content_type="application/json",
        )

        assert response.status_code == 400
        assert not EvaluationUnit.objects.filter(academic_cycle=cycle).exists()

    def test_inverted_recovery_window_is_rejected(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)

        response = auth_client.post(
            self._url(cycle),
            self._payload(recovery_starts_on="2026-03-28", recovery_ends_on="2026-03-21"),
            content_type="application/json",
        )

        assert response.status_code == 400
        assert "recovery_ends_on" in str(response.json())

    def test_without_recovery_window_still_works(self, auth_client, institution):
        cycle = AcademicCycleFactory(institution=institution)

        response = auth_client.post(
            self._url(cycle), self._payload(), content_type="application/json"
        )

        assert response.status_code == 201
        assert response.json()["recovery_starts_on"] is None
