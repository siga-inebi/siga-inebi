from rest_framework import serializers

from apps.people import queries
from apps.people.models import Person


def validate_institutional_person(person):
    if person is None:
        return
    required = ("cui", "birth_date", "phone_number", "sex", "nationality", "address", "department", "municipality")
    missing = [field for field in required if not person.get(field)]
    if missing:
        raise serializers.ValidationError({"person": {field: "Este campo es obligatorio." for field in missing}})
    if not person["cui"].isdigit() or len(person["cui"]) != 13:
        raise serializers.ValidationError({"person": {"cui": "El CUI debe tener exactamente 13 digitos."}})


class PersonSerializer(serializers.ModelSerializer):
    """
    Never exposes the internal ``id``: ``public_id`` is the only identifier the
    client sees, matching the opaque-identifier convention already used by
    ``apps.academics`` (docs/architecture/api-conventions.md).

    ``birth_date`` is accepted on write but never rendered back: this endpoint
    has no scoped read permission today (RNF-LEG-001), so returning the raw
    date would expose it to any authenticated user. Only the derived
    ``is_minor`` boolean is exposed for read.
    """

    is_minor = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = [
            "public_id",
            "first_name",
            "last_name",
            "cui",
            "email",
            "phone_number",
            "institutional_identifier",
            "birth_date",
            "sex",
            "nationality",
            "address",
            "department",
            "municipality",
            "is_minor",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["public_id", "is_active", "created_at", "updated_at"]
        extra_kwargs = {"birth_date": {"write_only": True}, "cui": {"write_only": True}}

    def get_is_minor(self, obj):
        return queries.is_minor(obj.birth_date)
