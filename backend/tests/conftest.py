from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

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


# RF-JOR-001: hour of the day ``operating_window_clock`` moves the clock to --
# inside the factory's default window (00:00 to 16:00), after its entry limit.
OPERATING_WINDOW_CLOCK_HOUR = 10


@pytest.fixture
def operating_window_clock(monkeypatch):
    """
    RF-JOR-001: scans and manual registrations are only accepted on a school
    day inside the jornada's operating window. Tests that capture "now" must
    not depend on the weekday or hour the suite happens to run at, so this
    moves Django's clock forward to the next Tuesday to Friday at
    ``OPERATING_WINDOW_CLOCK_HOUR`` in the configured time zone -- never a
    Monday, so the "yesterday" that late-event tests use is a school day too.

    Only an offset is applied, so the clock keeps ticking; and it only ever
    moves forward, so rows stamped with the real time before the shift (role
    assignments, for instance) are still in the past for the shifted clock.
    """
    real_now = timezone.now
    local = timezone.localtime(real_now())
    target_date = local.date()
    while True:
        target = timezone.make_aware(
            datetime.combine(target_date, time(OPERATING_WINDOW_CLOCK_HOUR, 0))
        )
        if target > local and 2 <= target.isoweekday() <= 5:
            break
        target_date += timedelta(days=1)
    offset = target - local
    monkeypatch.setattr(timezone, "now", lambda: real_now() + offset)
    return target
