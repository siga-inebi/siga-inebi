from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.identity.atomic_permissions import ATOMIC_PERMISSION_CODES_BY_CODENAME
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
