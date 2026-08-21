"""Regression tests for the shared application-to-HTTP error mapping."""

import pytest
from rest_framework import status

from apps.common.exceptions import AuthorizationError, DomainError, ResourceNotFoundError
from config.api.exception_handler import api_exception_handler


@pytest.mark.unit
def test_domain_error_uses_the_standard_bad_request_envelope():
    response = api_exception_handler(DomainError("Invalid academic cycle state."), {})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {
        "error": {
            "status_code": status.HTTP_400_BAD_REQUEST,
            "detail": "Invalid academic cycle state.",
        }
    }


@pytest.mark.unit
def test_resource_not_found_preserves_drf_detail_shape():
    response = api_exception_handler(ResourceNotFoundError("Student not found."), {})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data == {
        "error": {
            "status_code": status.HTTP_404_NOT_FOUND,
            "detail": {"detail": "Student not found."},
        }
    }


@pytest.mark.unit
def test_authorization_error_preserves_drf_detail_shape():
    response = api_exception_handler(AuthorizationError("Missing scoped permission."), {})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data == {
        "error": {
            "status_code": status.HTTP_403_FORBIDDEN,
            "detail": {"detail": "Missing scoped permission."},
        }
    }
