import pytest

from tests.factories.academic import InstitutionFactory
from tests.factories.identity import UserFactory


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
