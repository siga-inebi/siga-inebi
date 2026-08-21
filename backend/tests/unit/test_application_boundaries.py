"""Architecture guardrails for the modular-monolith application boundaries."""

from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
APPS_ROOT = BACKEND_ROOT / "apps"


@pytest.mark.unit
def test_domain_query_modules_do_not_depend_on_http_frameworks():
    query_modules = sorted(APPS_ROOT.glob("*/queries.py"))

    assert query_modules, "Expected each extracted read model to have a query module."
    forbidden_imports = ("rest_framework", "django.http", "Request")
    for module in query_modules:
        source = module.read_text(encoding="utf-8")
        assert not any(item in source for item in forbidden_imports), module


@pytest.mark.unit
def test_api_views_do_not_execute_orm_queries_directly():
    view_modules = sorted(APPS_ROOT.glob("*/api/views.py"))

    assert view_modules, "Expected API views in the modular applications."
    for module in view_modules:
        source = module.read_text(encoding="utf-8")
        assert ".objects." not in source, module
