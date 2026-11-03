from rest_framework import serializers

from apps.people import queries
from apps.people.models import Person


class PersonListQuerySerializer(serializers.Serializer):
    include_inactive = serializers.BooleanField(default=False)


def validate_institutional_person(person):
    if person is None:
        return
    required = (
        "cui",
        "birth_date",
        "phone_number",
        "sex",
        "nationality",
        "address",
        "department",
        "municipality",
    )
    missing = [field for field in required if not person.get(field)]
    if missing:
        raise serializers.ValidationError(
            {"person": dict.fromkeys(missing, "Este campo es obligatorio.")}
        )
    if not person["cui"].isdigit() or len(person["cui"]) != 13:
        raise serializers.ValidationError(
            {"person": {"cui": "El CUI debe tener exactamente 13 digitos."}}
        )


class PersonSerializer(serializers.ModelSerializer):
    """
    Never exposes the internal ``id``: ``public_id`` is the only identifier the
    client sees, matching the opaque-identifier convention already used by
    ``apps.academics`` (docs/architecture/api-conventions.md).

    ``birth_date`` and ``cui`` are accepted on write but never rendered back.
    The scoped registry exposes only the derived ``is_minor`` indicator.
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
        extra_kwargs = {
            "birth_date": {"write_only": True},
            "cui": {"write_only": True, "validators": []},
        }

    def validate_cui(self, value):
        existing = Person.objects.filter(cui=value)
        if self.instance is not None:
            existing = existing.exclude(pk=self.instance.pk)
        elif isinstance(getattr(self.root, "initial_data", None), dict):
            person_id = self.root.initial_data.get("person_public_id")
            if person_id:
                existing = existing.exclude(public_id=person_id)
        if existing.exists():
            raise serializers.ValidationError("El CUI ya pertenece a otra persona.")
        return value

    def get_is_minor(self, obj):
        return queries.is_minor(obj.birth_date)


class PersonRegistrySerializer(PersonSerializer):
    """Profile indicators are visible only in the scoped people registry."""

    profiles = serializers.SerializerMethodField()

    class Meta(PersonSerializer.Meta):
        fields = [*PersonSerializer.Meta.fields, "profiles"]

    def get_profiles(self, obj):
        return {
            "student": hasattr(obj, "student_profile"),
            "teacher": hasattr(obj, "teacher_profile"),
            "guardian": hasattr(obj, "guardian_profile"),
            "account": hasattr(obj, "user_account"),
        }
