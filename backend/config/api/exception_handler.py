from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.common.models import DomainError


def api_exception_handler(exc, context):
    """
    Wrap every API error in a single envelope.

    Domain invariants raise ``DomainError`` from the service layer; they are
    business rule violations, so they map to 400 with the rule message as
    detail. Views therefore never need to catch them (AGENTS.md #8).
    """
    if isinstance(exc, DomainError):
        return Response(
            {
                "error": {
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "detail": str(exc),
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        return response

    detail = response.data
    response.data = {
        "error": {
            "status_code": response.status_code,
            "detail": detail,
        }
    }
    return response
