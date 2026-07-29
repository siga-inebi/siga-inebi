from django.views.decorators.csrf import ensure_csrf_cookie
from django.db import connection
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.decorators import method_decorator

from apps.identity.serializers import CurrentSessionSerializer, CurrentUserSerializer, LoginSerializer
from config.api.serializers import EmptySerializer, HealthSerializer


class HealthView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=HealthSerializer)
    def get(self, request):
        return Response({"status": "ok", "service": "api"})


class DatabaseHealthView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=HealthSerializer)
    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
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
        request.session.flush()
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
