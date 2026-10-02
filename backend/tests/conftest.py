import pytest

from apps.identity.atomic_permissions import permission_codename
from tests.factories.academic import InstitutionFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
    UserFactory,
)


@pytest.fixture
def institution(db):
    """The single institution the API resolves for the current request."""
    return InstitutionFactory(name="Instituto Demo", short_name="DEMO")


@pytest.fixture
def auth_client(db, client):
    """A logged-in DRF-capable Django test client."""
    user = UserFactory(password="demo-pass-123")
    client.force_login(user)
    client.user = user
    return client


@pytest.fixture
def admin_client(auth_client, institution):
    """
    ``auth_client`` granted ``scope.assign`` over ``institution`` — the level
    the academics/documents catalogue views require for writes
    (``CatalogueView.require_assignment_scope``), mirroring the pattern
    ``TeachingAssignment*`` views already used before this grant existed
    anywhere else.
    """
    permission = PermissionFactory(codename=permission_codename("scope.assign"))
    assignment = RoleAssignmentFactory(
        user=auth_client.user, role=RoleFactory(permissions=[permission])
    )
    ScopeGrantFactory(assignment=assignment, institution=institution)
    return auth_client
