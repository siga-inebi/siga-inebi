from django.contrib.auth import login
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.identity.services import (
    AccountTemporarilyLockedError,
    InvalidCredentialsError,
    authenticate_account,
    effective_permission_codes,
    effective_session_idle_timeout_minutes,
    refresh_session_activity,
)

LOCKED_ACCOUNT_CODE = "account_locked"


def locked_account_message(locked_until):
    """L5: decir que la cuenta esta bloqueada y hasta que hora, no "credenciales invalidas"."""
    if locked_until is None:
        return "Cuenta bloqueada temporalmente por intentos fallidos."
    local = timezone.localtime(locked_until)
    return (
        "Cuenta bloqueada temporalmente por intentos fallidos. "
        f"Podrá intentarlo de nuevo a las {local:%H:%M}."
    )


class PersonSummarySerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class CurrentRoleSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()


class CurrentUserSerializer(serializers.Serializer):
    """
    Cuenta de la sesion. Incluye los permisos atomicos efectivos (1.4): el
    frontend filtra menu, rutas y acciones con ellos, y el backend sigue siendo
    la unica autoridad (cada operacion se vuelve a autorizar).
    """

    public_id = serializers.UUIDField()
    username = serializers.CharField()
    email = serializers.EmailField()
    status = serializers.CharField()
    status_display = serializers.CharField(source="get_status_display")
    is_superuser = serializers.BooleanField()
    person = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    session_idle_timeout_minutes = serializers.SerializerMethodField()

    @extend_schema_field(PersonSummarySerializer(allow_null=True))
    def get_person(self, obj):
        if not obj.person_id:
            return None
        return {
            "public_id": str(obj.person.public_id),
            "first_name": obj.person.first_name,
            "last_name": obj.person.last_name,
        }

    def get_permissions(self, obj) -> list[str]:
        return effective_permission_codes(user=obj)

    @extend_schema_field(CurrentRoleSerializer(many=True))
    def get_roles(self, obj):
        from apps.identity.queries import current_role_assignments

        seen = {}
        for assignment in current_role_assignments(obj):
            seen.setdefault(
                assignment.role.public_id,
                {
                    "public_id": str(assignment.role.public_id),
                    "name": assignment.role.name,
                    "slug": assignment.role.slug,
                },
            )
        return list(seen.values())

    def get_session_idle_timeout_minutes(self, obj) -> int:
        return effective_session_idle_timeout_minutes(user=obj)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context["request"]
        try:
            user = authenticate_account(
                request=request,
                username=attrs["username"],
                password=attrs["password"],
            )
        except InvalidCredentialsError:
            raise serializers.ValidationError("Credenciales inválidas.") from None
        except AccountTemporarilyLockedError as exc:
            raise serializers.ValidationError(
                {
                    "non_field_errors": [locked_account_message(exc.locked_until)],
                    "code": LOCKED_ACCOUNT_CODE,
                    "locked_until": exc.locked_until.isoformat() if exc.locked_until else "",
                }
            ) from None
        attrs["user"] = user
        return attrs

    def save(self):
        request = self.context["request"]
        user = self.validated_data["user"]
        login(request, user)
        refresh_session_activity(request=request, user=user)
        return user


class CurrentSessionSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    user = CurrentUserSerializer(allow_null=True)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    new_password_confirm = serializers.CharField(write_only=True, required=False)

    def validate(self, attrs):
        confirm = attrs.get("new_password_confirm")
        if confirm is not None and confirm != attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password_confirm": ["Las contraseñas no coinciden."]}
            )
        return attrs
