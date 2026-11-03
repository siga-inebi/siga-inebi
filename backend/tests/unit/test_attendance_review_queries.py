"""
#631 (AS2–AS5) — consultas de lectura de asistencia para la interfaz.

- Bandejas de justificaciones y permisos: quién ve qué (revisor con alcance,
  solicitante, revisor sin alcance), filtros, búsqueda y orden.
- Estado de la credencial sin exponer el identificador opaco.
- Motivos de registro manual: solo los vigentes por omisión.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.attendance import queries, services
from apps.attendance.models import AttendancePermit, Justification, StudentCredential
from apps.common.exceptions import ResourceNotFoundError
from tests.factories.attendance import (
    AttendancePermitFactory,
    JustificationFactory,
    ManualRegistrationReasonFactory,
    StudentCredentialFactory,
)
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.people import PersonFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]

JUSTIFICATION_RESOLVE = "attendance_justification_resolve"
PERMIT_RESOLVE = "attendance_permit_resolve"


def _grant(user, codename, student=None):
    permission = PermissionFactory(codename=codename)
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    if student is not None:
        ScopeGrantFactory(assignment=assignment, student=student)


def _ids(rows):
    return {row.public_id for row in rows}


# --------------------------------------------------------------------------- #
# Justificaciones
# --------------------------------------------------------------------------- #


def test_reviewer_sees_justifications_of_students_in_scope_and_own_submissions():
    reviewer = UserFactory()
    in_scope = StudentFactory()
    _grant(reviewer, JUSTIFICATION_RESOLVE, student=in_scope)
    visible = JustificationFactory(student=in_scope)
    out_of_scope = JustificationFactory()
    own = JustificationFactory(submitted_by=reviewer)

    rows = queries.visible_justifications(user=reviewer)

    assert _ids(rows) == {visible.public_id, own.public_id}
    assert out_of_scope.public_id not in _ids(rows)


def test_submitter_without_resolve_sees_only_own_justifications():
    guardian = UserFactory()
    own = JustificationFactory(submitted_by=guardian)
    JustificationFactory(student=own.student)

    assert _ids(queries.visible_justifications(user=guardian)) == {own.public_id}


def test_reviewer_without_scope_does_not_see_the_whole_institution():
    reviewer = UserFactory()
    _grant(reviewer, JUSTIFICATION_RESOLVE)
    JustificationFactory()

    assert not queries.visible_justifications(user=reviewer).exists()


def test_justifications_list_pending_first_then_newest():
    reviewer = UserFactory()
    resolved = JustificationFactory(submitted_by=reviewer, status=Justification.Status.APPROVED)
    older_pending = JustificationFactory(submitted_by=reviewer)
    newer_pending = JustificationFactory(submitted_by=reviewer)

    rows = list(queries.visible_justifications(user=reviewer))

    assert [row.public_id for row in rows] == [
        newer_pending.public_id,
        older_pending.public_id,
        resolved.public_id,
    ]


def test_justifications_filter_by_status_student_dates_and_search():
    reviewer = UserFactory()
    today = timezone.localdate()
    student = StudentFactory(
        student_code="STU-ZETA", person=PersonFactory(first_name="Ana", last_name="Zeta")
    )
    target = JustificationFactory(
        submitted_by=reviewer, student=student, absence_date=today - timedelta(days=2)
    )
    JustificationFactory(submitted_by=reviewer, absence_date=today - timedelta(days=10))
    JustificationFactory(
        submitted_by=reviewer, student=student, status=Justification.Status.REJECTED
    )

    def visible(**filters):
        return _ids(queries.visible_justifications(user=reviewer, **filters))

    assert target.public_id in visible(status="pending", student_id=student.public_id)
    assert len(visible(status="pending", student_id=student.public_id)) == 1
    assert visible(date_from=today - timedelta(days=3), date_to=today - timedelta(days=2)) == {
        target.public_id
    }
    assert visible(search="ana zeta", status="pending") == {target.public_id}
    assert visible(search="stu-zeta", status="pending") == {target.public_id}


def test_justifications_accept_whitelisted_ordering_only():
    reviewer = UserFactory()
    early = JustificationFactory(
        submitted_by=reviewer, absence_date=timezone.localdate() - timedelta(days=5)
    )
    late = JustificationFactory(
        submitted_by=reviewer, absence_date=timezone.localdate() - timedelta(days=1)
    )

    ordered = queries.visible_justifications(user=reviewer, ordering="absence_date")
    unknown = queries.visible_justifications(user=reviewer, ordering="reason")

    assert [row.public_id for row in ordered] == [early.public_id, late.public_id]
    assert [row.public_id for row in unknown] == [late.public_id, early.public_id]


def test_justification_detail_outside_visibility_is_not_found():
    with pytest.raises(ResourceNotFoundError):
        queries.visible_justification(
            user=UserFactory(), public_id=JustificationFactory().public_id
        )


def test_justification_rows_report_whether_they_have_an_attachment():
    reviewer = UserFactory()
    JustificationFactory(submitted_by=reviewer)

    row = queries.visible_justifications(user=reviewer).get()

    assert row.attachment_exists is False


# --------------------------------------------------------------------------- #
# Permisos de salida anticipada o ingreso tardio
# --------------------------------------------------------------------------- #


def test_permit_reviewer_sees_students_in_scope_and_own_requests():
    reviewer = UserFactory()
    in_scope = StudentFactory()
    _grant(reviewer, PERMIT_RESOLVE, student=in_scope)
    visible = AttendancePermitFactory(student=in_scope)
    own = AttendancePermitFactory(submitted_by=reviewer)
    AttendancePermitFactory()

    assert _ids(queries.visible_attendance_permits(user=reviewer)) == {
        visible.public_id,
        own.public_id,
    }


def test_permit_requester_sees_only_own_requests():
    requester = UserFactory()
    own = AttendancePermitFactory(submitted_by=requester)
    AttendancePermitFactory(student=own.student)

    assert _ids(queries.visible_attendance_permits(user=requester)) == {own.public_id}


def test_permits_filter_by_type_and_status_pending_first():
    requester = UserFactory()
    exit_pending = AttendancePermitFactory(submitted_by=requester)
    late_pending = AttendancePermitFactory(
        submitted_by=requester, permit_type=AttendancePermit.PermitType.LATE_ARRIVAL
    )
    approved = AttendancePermitFactory(
        submitted_by=requester, status=AttendancePermit.Status.APPROVED
    )

    all_rows = [row.public_id for row in queries.visible_attendance_permits(user=requester)]
    late_only = queries.visible_attendance_permits(user=requester, permit_type="late_arrival")
    approved_only = queries.visible_attendance_permits(user=requester, status="approved")

    assert all_rows[-1] == approved.public_id
    assert set(all_rows[:2]) == {exit_pending.public_id, late_pending.public_id}
    assert _ids(late_only) == {late_pending.public_id}
    assert _ids(approved_only) == {approved.public_id}


# --------------------------------------------------------------------------- #
# Estado de la credencial
# --------------------------------------------------------------------------- #


def test_credential_status_without_any_credential_is_none():
    student = StudentFactory()

    status = queries.credential_status(student=student)

    assert status == {
        "student_id": student.public_id,
        "status": "none",
        "public_id": None,
        "issued_at": None,
        "revoked_at": None,
        "revocation_reason": None,
    }


def test_credential_status_reports_the_active_one_without_its_token():
    credential = StudentCredentialFactory()

    status = queries.credential_status(student=credential.student)

    assert status["status"] == StudentCredential.Status.ACTIVE
    assert status["public_id"] == credential.public_id
    assert status["revoked_at"] is None
    assert credential.opaque_identifier not in {str(value) for value in status.values()}


def test_credential_status_reports_the_latest_revocation():
    credential = StudentCredentialFactory()
    services.revoke_credential(student=credential.student, reason="Extravío", actor=UserFactory())

    status = queries.credential_status(student=credential.student)

    assert status["status"] == StudentCredential.Status.REVOKED
    assert status["revocation_reason"] == "Extravío"
    assert status["revoked_at"] is not None


def test_credential_status_prefers_the_newest_credential():
    student = StudentFactory()
    StudentCredentialFactory(
        student=student,
        status=StudentCredential.Status.REVOKED,
        issued_at=timezone.now() - timedelta(days=30),
    )
    current = StudentCredentialFactory(student=student)

    assert queries.credential_status(student=student)["public_id"] == current.public_id


# --------------------------------------------------------------------------- #
# Motivos de registro manual
# --------------------------------------------------------------------------- #


def test_manual_registration_reasons_list_only_active_ones_by_default():
    active = ManualRegistrationReasonFactory()
    retired = ManualRegistrationReasonFactory(is_active=False)

    assert list(queries.manual_registration_reasons()) == [active]
    assert list(queries.manual_registration_reasons(is_active=False)) == [retired]
