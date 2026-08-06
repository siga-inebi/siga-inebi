from rest_framework import serializers

from apps.people.models import Person


class PersonRefSerializer(serializers.ModelSerializer):
    """
    Compact reference for nesting inside another domain's serializer (e.g. a
    ``Student`` or ``Guardian`` naming the person behind it), so that domain
    does not need its own copy of a person's identity.
    """

    class Meta:
        model = Person
        fields = ["public_id", "first_name", "last_name"]


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
