from rest_framework import serializers

from apps.people.models import Person


class PersonSerializer(serializers.ModelSerializer):
    """
    Never exposes the internal ``id``: ``public_id`` is the only identifier the
    client sees, matching the opaque-identifier convention already used by
    ``apps.academics`` (docs/architecture/api-conventions.md).
    """

    class Meta:
        model = Person
        fields = [
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
        read_only_fields = ["public_id", "is_active", "created_at", "updated_at"]
