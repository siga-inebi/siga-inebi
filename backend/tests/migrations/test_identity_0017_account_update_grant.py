"""
ADR-0011: al separar `account.update` de `account.create`, ningun rol pierde la
edicion de cuentas. La migracion 0017 concede `account_update` a todo rol que ya
tiene `account_create`, no toca a los demas y puede correr dos veces.
"""

import importlib

import pytest
from django.apps import apps as django_apps

from tests.factories.identity import PermissionFactory, RoleFactory

migration = importlib.import_module(
    "apps.identity.migrations.0017_grant_account_update_to_account_creators"
)

pytestmark = [pytest.mark.migration, pytest.mark.postgres, pytest.mark.django_db]


def codenames(role):
    return set(role.permissions.values_list("codename", flat=True))


def test_roles_with_account_create_receive_account_update_once():
    account_create = PermissionFactory(codename="account_create")
    creator = RoleFactory(permissions=[account_create])
    other = RoleFactory(permissions=[PermissionFactory(codename="audit_read")])
    PermissionFactory(codename="account_update")  # sembrado por 0015; get_or_create
    for role in (creator, other):
        role.permissions.remove(*role.permissions.filter(codename="account_update"))

    migration.grant_account_update_to_account_creators(django_apps, None)
    migration.grant_account_update_to_account_creators(django_apps, None)

    assert codenames(creator) == {"account_create", "account_update"}
    assert codenames(other) == {"audit_read"}
    assert creator.permissions.filter(codename="account_update").count() == 1


def test_reverse_is_a_noop_and_keeps_grants():
    operation = migration.Migration.operations[0]
    assert operation.reverse_code is operation.noop
