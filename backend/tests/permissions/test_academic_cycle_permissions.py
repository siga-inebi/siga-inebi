"""
#631, PR 1: denegación por defecto en las acciones nuevas del ciclo escolar.

Volver a borrador exige ``academic_cycle.revert`` con alcance sobre la
institución (D6). Ni ``scope.assign`` ni ``academic_cycle.reopen`` lo
sustituyen, y un alcance sobre otra institución no autoriza nada.
"""

from datetime import date

import pytest
from django.urls import reverse

from apps.academics.models import AcademicCycle
from apps.audit.models import AuditEvent
from apps.identity.atomic_permissions import permission_codename
from tests.factories.academic import AcademicCycleFactory, InstitutionFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)

pytestmark = [pytest.mark.permissions, pytest.mark.django_db]


def _active_cycle(institution):
    return AcademicCycleFactory(
        institution=institution,
        year=2031,
        starts_on=date(2031, 1, 15),
        ends_on=date(2031, 10, 31),
        status=AcademicCycle.CycleStatus.ACTIVE,
    )


def _grant(user, institution, atomic):
    permission = PermissionFactory(codename=permission_codename(atomic))
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    return ScopeGrantFactory(assignment=assignment, institution=institution)


def _revert(client, cycle):
    return client.post(
        reverse("academic-cycle-revert-to-draft", args=[cycle.public_id]),
        {"reason": "Se activó por error"},
        content_type="application/json",
    )


def test_revert_permission_codename_is_the_seeded_one():
    assert permission_codename("academic_cycle.revert") == "academic_cycle_revert"


def test_revert_requires_authentication(client, institution):
    cycle = _active_cycle(institution)

    assert _revert(client, cycle).status_code == 403


@pytest.mark.parametrize("atomic", [None, "scope.assign", "academic_cycle.reopen"])
def test_revert_is_denied_without_the_revert_permission(auth_client, institution, atomic):
    cycle = _active_cycle(institution)
    if atomic:
        _grant(auth_client.user, institution, atomic)

    response = _revert(auth_client, cycle)

    assert response.status_code == 403
    cycle.refresh_from_db()
    assert cycle.status == AcademicCycle.CycleStatus.ACTIVE
    assert not AuditEvent.objects.filter(action="academics.cycle.reverted_to_draft").exists()


def test_revert_scope_over_another_institution_is_denied(auth_client, institution):
    cycle = _active_cycle(institution)
    _grant(auth_client.user, InstitutionFactory(), "academic_cycle.revert")

    assert _revert(auth_client, cycle).status_code == 403


def test_revert_with_permission_and_institution_scope_is_allowed(auth_client, institution):
    cycle = _active_cycle(institution)
    _grant(auth_client.user, institution, "academic_cycle.revert")

    assert _revert(auth_client, cycle).status_code == 200


@pytest.mark.parametrize(
    ("method", "route"),
    [
        ("get", "teaching-assignment-list-create"),
        ("get", "cycle-assignment-matrix"),
        ("get", "cycle-teaching-assignment-clone-preview"),
        ("post", "cycle-teaching-assignment-batch"),
    ],
)
def test_assignment_planning_endpoints_require_assignment_scope(
    auth_client, institution, method, route
):
    cycle = _active_cycle(institution)
    args = [] if route == "teaching-assignment-list-create" else [cycle.public_id]

    response = getattr(auth_client, method)(
        reverse(route, args=args), content_type="application/json"
    )

    assert response.status_code == 403
