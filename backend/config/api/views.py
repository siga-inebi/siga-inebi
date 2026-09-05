import logging

from django.contrib.auth import logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError, connection
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import DomainError
from apps.identity.serializers import (
    CurrentSessionSerializer,
    CurrentUserSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
)
from apps.identity.services import (
    change_password,
    close_account_sessions,
    record_current_session_logout,
)
from config.api.serializers import EmptySerializer, HealthSerializer

logger = logging.getLogger(__name__)


class HealthView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=HealthSerializer)
    def get(self, request):
        return Response({"status": "ok", "service": "api"})


class DatabaseHealthView(APIView):
    """
    Reports whether the database answers.

    A probe whose job is to report a dependency being down must not fall over
    with it: letting the driver error escape produced an unhandled 500 and an
    HTML debug page, which monitoring cannot read. The failure is caught and
    reported as 503 with the same JSON shape as the healthy answer.
    """

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses={
            200: HealthSerializer,
            503: OpenApiResponse(
                response=HealthSerializer, description="La base de datos no responde."
            ),
        }
    )
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            logger.exception("Database health probe failed")
            return Response(
                {"status": "unavailable", "service": "database"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok", "service": "database"})


class LoginView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    @method_decorator(ensure_csrf_cookie)
    @extend_schema(responses={200: OpenApiResponse(description="CSRF cookie set")})
    def get(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=LoginSerializer, responses=CurrentUserSerializer)
    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(CurrentUserSerializer(user).data, status=status.HTTP_200_OK)


class LogoutView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmptySerializer

    @extend_schema(responses={204: OpenApiResponse(description="Session closed")})
    def post(self, request):
        record_current_session_logout(user=request.user)
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutAllSessionsView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmptySerializer

    @extend_schema(responses={204: OpenApiResponse(description="All sessions closed")})
    def post(self, request):
        close_account_sessions(
            actor=request.user,
            user=request.user,
            current_session_key=request.session.session_key,
        )
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CurrentSessionSerializer

    @extend_schema(responses=CurrentSessionSerializer)
    def get(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"authenticated": False, "user": None},
                status=status.HTTP_200_OK,
            )
        return Response(
            {
                "authenticated": True,
                "user": CurrentUserSerializer(request.user).data,
            },
            status=status.HTTP_200_OK,
        )


class PasswordChangeView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PasswordChangeSerializer

    @extend_schema(
        request=PasswordChangeSerializer,
        responses={200: OpenApiResponse(description="Contraseña actualizada exitosamente")},
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            change_password(
                user=request.user,
                current_password=serializer.validated_data["current_password"],
                new_password=serializer.validated_data["new_password"],
                request=request,
            )
        except DomainError as exc:
            return Response(
                {
                    "error": {
                        "code": "domain_error",
                        "message": str(exc),
                        "detail": {"current_password": [str(exc)]},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DjangoValidationError as exc:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "Contraseña no cumple con los requisitos de seguridad.",
                        "detail": {"new_password": list(exc.messages)},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"status": "ok", "message": "Contraseña actualizada exitosamente."},
            status=status.HTTP_200_OK,
        )
