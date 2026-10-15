"""RF-EMI-001: permission and scope of the individual emission."""

import pytest

from apps.audit.models import AuditEvent
from apps.common.exceptions import AuthorizationError
from apps.documents.models import DocumentIssuance
from apps.documents.services import issue_individual_document, verify_issued_document
from apps.enrolments.services import create_enrolment
from tests.factories.academic import SectionFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.permissions, pytest.mark.django_db]

CONSTANCIA = DocumentIssuance.DocumentType.ENROLMENT_CERTIFICATE


def _enrolment():
    section = SectionFactory()
    return create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )


def _user(*codenames, **scope):
    user = UserFactory()
    permissions = [PermissionFactory(codename=codename) for codename in codenames]
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=permissions))
    if scope:
        ScopeGrantFactory(assignment=assignment, **scope)
    return user


def _denial_reason():
    return (
        AuditEvent.objects.filter(action="documents.official_issuance.denied")
        .latest("pk")
        .context["reason"]
    )


def test_issue_permission_with_student_scope_allows_emission():
    """RF-EMI-001: document.issue over the student's scope may emit."""
    enrolment = _enrolment()
    user = _user("document_issue", student=enrolment.student)

    issued = issue_individual_document(enrolment=enrolment, document_type=CONSTANCIA, actor=user)

    assert issued.issuance.issued_by_id == user.pk


def test_section_scope_reaches_the_enrolled_student():
    """RF-EMI-001: an administrative section grant covers its enrolled students."""
    enrolment = _enrolment()
    user = _user("document_issue", section=enrolment.section)

    assert issue_individual_document(enrolment=enrolment, document_type=CONSTANCIA, actor=user)


def test_issue_without_permission_is_denied_and_audited():
    """RF-EMI-001: no document.issue, no emission."""
    enrolment = _enrolment()
    user = _user("document_read", student=enrolment.student)

    with pytest.raises(AuthorizationError):
        issue_individual_document(enrolment=enrolment, document_type=CONSTANCIA, actor=user)
    assert _denial_reason() == "missing_permission"
    assert not DocumentIssuance.objects.exists()


def test_issue_permission_without_scope_is_denied_and_audited():
    """RF-EMI-001: the atomic permission alone does not reach a student."""
    enrolment = _enrolment()
    user = _user("document_issue")

    with pytest.raises(AuthorizationError):
        issue_individual_document(enrolment=enrolment, document_type=CONSTANCIA, actor=user)
    assert _denial_reason() == "missing_scope"


def test_issue_permission_over_another_student_is_denied():
    """RF-EMI-001: scope over one student does not reach another."""
    enrolment = _enrolment()
    user = _user("document_issue", student=StudentFactory())

    with pytest.raises(AuthorizationError):
        issue_individual_document(enrolment=enrolment, document_type=CONSTANCIA, actor=user)


def test_verifying_an_emission_requires_read_scope_over_the_student():
    """RF-EMI-001: the emission register is read under document.read + scope."""
    enrolment = _enrolment()
    issued = issue_individual_document(
        enrolment=enrolment,
        document_type=CONSTANCIA,
        actor=UserFactory(is_superuser=True),
    )
    reader = _user("document_read", student=enrolment.student)
    outsider = _user("document_read", student=StudentFactory())

    assert verify_issued_document(actor=reader, issuance=issued.issuance, payload=issued.content)
    with pytest.raises(AuthorizationError):
        verify_issued_document(actor=outsider, issuance=issued.issuance, payload=issued.content)
