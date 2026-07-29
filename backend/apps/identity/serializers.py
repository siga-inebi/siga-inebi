from django.contrib.auth import authenticate, login
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


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
        user = authenticate(request=request, username=attrs["username"], password=attrs["password"])
        if user is None:
            raise serializers.ValidationError("Credenciales invalidas.")
        if user.is_locked():
            raise serializers.ValidationError("Cuenta temporalmente bloqueada.")
        attrs["user"] = user
        return attrs

    def save(self):
        request = self.context["request"]
        user = self.validated_data["user"]
        login(request, user)
        user.failed_login_attempts = 0
        user.save(update_fields=["failed_login_attempts"])
        return user


class CurrentSessionSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    user = CurrentUserSerializer(allow_null=True)
