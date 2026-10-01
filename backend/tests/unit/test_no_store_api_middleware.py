"""
RNF-PRI-003 — la regla de no persistencia en aislamiento: `no-store` por
defecto en la API, y solo una vista que fija su propio `Cache-Control` lo
conserva.
"""

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from apps.common.middleware import NoStoreApiResponseMiddleware

pytestmark = pytest.mark.unit


def _run(path, response):
    middleware = NoStoreApiResponseMiddleware(lambda request: response)
    return middleware(RequestFactory().get(path))


def test_api_response_without_cache_control_is_marked_no_store():
    response = _run("/api/v1/attendance/presence/", HttpResponse())

    assert response["Cache-Control"] == "no-store"


def test_api_response_that_opted_into_caching_keeps_its_own_header():
    opted_in = HttpResponse()
    opted_in["Cache-Control"] = "private, max-age=300"

    response = _run("/api/v1/academics/levels/", opted_in)

    assert response["Cache-Control"] == "private, max-age=300"


def test_error_responses_are_marked_no_store_too():
    response = _run("/api/v1/attendance/presence/", HttpResponse(status=403))

    assert response["Cache-Control"] == "no-store"


def test_non_api_paths_are_left_untouched():
    response = _run("/admin/login/", HttpResponse())

    assert not response.has_header("Cache-Control")
