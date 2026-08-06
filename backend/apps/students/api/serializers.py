from rest_framework import serializers

from apps.people.api.serializers import PersonRefSerializer
from apps.students.models import EmergencyContact, Guardian, Student, StudentGuardianRelation

# --------------------------------------------------------------------------- #
# compact references, used whenever a payload needs to name a parent record
# without dragging in a full nested representation.
# --------------------------------------------------------------------------- #


class StudentRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ["public_id", "student_code"]


class GuardianRefSerializer(serializers.ModelSerializer):
    person = PersonRefSerializer(read_only=True)

    class Meta:
        model = Guardian
        fields = ["public_id", "person"]


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            "id",
            "person",
            "student_code",
            "status",
            "photo_path",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]


class GuardianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardian
        fields = [
            "id",
            "person",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_active", "created_at", "updated_at"]


class StudentGuardianRelationSerializer(serializers.ModelSerializer):
    """Never exposes the internal ``id``: only ``public_id``, like ``people``."""

    student = StudentRefSerializer(read_only=True)
    guardian = GuardianRefSerializer(read_only=True)

    class Meta:
        model = StudentGuardianRelation
        fields = [
            "public_id",
            "student",
            "guardian",
            "relationship_label",
            "is_primary",
            "starts_at",
            "ends_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["public_id", "ends_at", "created_at", "updated_at"]


class StudentGuardianRelationCreateSerializer(serializers.Serializer):
    """The student is resolved from the URL; the guardian is named by id."""

    guardian_id = serializers.UUIDField(help_text="public_id of an existing, active guardian.")
    relationship_label = serializers.CharField(max_length=100)
    is_primary = serializers.BooleanField(required=False, default=False)
    starts_at = serializers.DateField(required=False)


class StudentGuardianRelationUpdateSerializer(serializers.Serializer):
    """
    ``starts_at``/``ends_at`` are not editable here: closing a relation is
    exclusively the job of the dedicated end-relation action.
    """

    relationship_label = serializers.CharField(max_length=100, required=False)
    is_primary = serializers.BooleanField(required=False)


class EmergencyContactSerializer(serializers.ModelSerializer):
    """Never exposes the internal ``id``: only ``public_id``, like ``people``."""

    student = StudentRefSerializer(read_only=True)

    class Meta:
        model = EmergencyContact
        fields = [
            "public_id",
            "student",
            "name",
            "phone_number",
            "relationship_label",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["public_id", "is_active", "created_at", "updated_at"]


class EmergencyContactCreateSerializer(serializers.Serializer):
    """The student is resolved from the URL, not from the payload."""

    name = serializers.CharField(max_length=255)
    phone_number = serializers.CharField(max_length=30)
    relationship_label = serializers.CharField(max_length=100)


class EmergencyContactUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    phone_number = serializers.CharField(max_length=30, required=False)
    relationship_label = serializers.CharField(max_length=100, required=False)
