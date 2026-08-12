from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.identity.atomic_permissions import (
    ATOMIC_PERMISSION_CODES_BY_CODENAME,
    ATOMIC_PERMISSIONS,
    permission_codename,
)
from apps.people.models import Person


class AccountProvisionSerializer(serializers.Serializer):
    person = serializers.PrimaryKeyRelatedField(queryset=Person.objects.all())
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate_username(self, value):
        if get_user_model().objects.filter(username=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este usuario.")
        return value


class ProvisionedAccountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    status = serializers.CharField()
    person = serializers.IntegerField()
    activation_code = serializers.CharField()
    activation_expires_at = serializers.DateTimeField()


class ActivationChallengeSerializer(serializers.Serializer):
    account = serializers.IntegerField()
    activation_code = serializers.CharField()
    activation_expires_at = serializers.DateTimeField()
    max_attempts = serializers.IntegerField()


class AccountActivationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    activation_code = serializers.CharField(max_length=8, trim_whitespace=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class ActivatedAccountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    status = serializers.CharField()


class AtomicPermissionSerializer(serializers.Serializer):
    code = serializers.SerializerMethodField()
    name = serializers.CharField()

    def get_code(self, obj):
        return ATOMIC_PERMISSION_CODES_BY_CODENAME[obj.codename]


class RoleSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.SlugField()
    description = serializers.CharField()
    is_system = serializers.BooleanField()
    permissions = serializers.SerializerMethodField()

    def get_permissions(self, obj):
        return sorted(
            ATOMIC_PERMISSION_CODES_BY_CODENAME[permission.codename]
            for permission in obj.permissions.all()
            if permission.codename in ATOMIC_PERMISSION_CODES_BY_CODENAME
        )


class RoleWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    slug = serializers.SlugField(max_length=150, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=[code for code, _name in ATOMIC_PERMISSIONS]),
        required=False,
    )

    def validate(self, attrs):
        if not self.partial:
            errors = {}
            if "name" not in attrs:
                errors["name"] = "Este campo es obligatorio."
            if "slug" not in attrs:
                errors["slug"] = "Este campo es obligatorio."
            if errors:
                raise serializers.ValidationError(errors)
        return attrs

    def validate_permissions(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("No se permiten permisos duplicados.")
        return value

    def validated_service_data(self):
        data = dict(self.validated_data)
        if "permissions" in data:
            data["permission_codenames"] = [
                permission_codename(code) for code in data.pop("permissions")
            ]
        return data


class RoleAssignmentWriteSerializer(serializers.Serializer):
    role = serializers.UUIDField()
    starts_at = serializers.DateTimeField(required=False)
    ends_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        starts_at = attrs.get("starts_at")
        ends_at = attrs.get("ends_at")
        if starts_at and ends_at and ends_at < starts_at:
            raise serializers.ValidationError(
                {"ends_at": "La fecha final no puede ser anterior a la inicial."}
            )
        return attrs


class RoleAssignmentSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    user = serializers.IntegerField(source="user_id")
    role = serializers.UUIDField(source="role.public_id")
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField(allow_null=True)
