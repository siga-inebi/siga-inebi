from rest_framework import serializers

from apps.people.models import Person


class PersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Person
        fields = [
            "id",
            "public_id",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "institutional_identifier",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "is_active", "created_at", "updated_at"]
