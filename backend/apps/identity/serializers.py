from django.contrib.auth import login
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.identity.services import (
    AccountTemporarilyLockedError,
    InvalidCredentialsError,
    authenticate_account,
)


class PersonSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()


class CurrentUserSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="pk")
    username = serializers.CharField()
    email = serializers.EmailField()
    status = serializers.CharField()
    person = serializers.SerializerMethodField()

    @extend_schema_field(PersonSummarySerializer(allow_null=True))
    def get_person(self, obj):
        if not obj.person_id:
            return None
        return {
            "id": obj.person_id,
            "first_name": obj.person.first_name,
            "last_name": obj.person.last_name,
        }


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
            raise serializers.ValidationError("Credenciales invalidas.") from None
        except AccountTemporarilyLockedError:
            raise serializers.ValidationError("Cuenta temporalmente bloqueada.") from None
        attrs["user"] = user
        return attrs

    def save(self):
        request = self.context["request"]
        user = self.validated_data["user"]
        login(request, user)
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
