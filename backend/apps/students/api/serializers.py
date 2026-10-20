from rest_framework import serializers

from apps.people.api.serializers import PersonSerializer, validate_institutional_person
from apps.students import services
from apps.students.models import (
    EmergencyContact,
    Guardian,
    Student,
    StudentGuardianRelation,
    StudentHealthNote,
    StudentObservation,
)
from apps.students.services import (
    create_guardian,
    create_student,
    create_student_guardian_relation,
    guardian_relation_actions,
    student_record_actions,
    update_student,
)


class StudentListQuerySerializer(serializers.Serializer):
    include_inactive = serializers.BooleanField(default=False)
    status = serializers.ChoiceField(choices=Student.StudentStatus.choices, required=False)


class GuardianListQuerySerializer(serializers.Serializer):
    include_inactive = serializers.BooleanField(default=False)


# --------------------------------------------------------------------------- #
# compact references, used whenever a payload needs to name a parent record
# without dragging in a full nested representation.
# --------------------------------------------------------------------------- #


class StudentRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ["public_id", "student_code"]


class SuggestedStudentCodeSerializer(serializers.Serializer):
    """Siguiente codigo de estudiante libre, para prellenar el formulario."""

    student_code = serializers.CharField()


class StudentSerializer(serializers.ModelSerializer):
    person = PersonSerializer()

    class Meta:
        model = Student
        fields = [
            "id",
            "public_id",
            "person",
            "student_code",
            "status",
            "photo",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "is_active", "created_at", "updated_at"]
        extra_kwargs = {
            # Opcional al crear: el servicio genera el siguiente de la serie del
            # anio ("EST-2026-0043"). Se sigue aceptando uno explicito porque un
            # traslado llega con el codigo ya impreso en sus papeles.
            "student_code": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data):
        person_data = validated_data.pop("person")
        actor = getattr(self.context.get("request"), "user", None)
        return create_student(
            person_data=person_data,
            student_code=validated_data.get("student_code"),
            status=validated_data.get("status"),
            actor=actor,
        )

    def validate(self, attrs):
        if self.instance is None:
            validate_institutional_person(attrs.get("person"))
        return attrs

    def update(self, instance, validated_data):
        # Nested person edits aren't supported yet — edit via /api/v1/people/<id>/.
        validated_data.pop("person", None)
        actor = getattr(self.context.get("request"), "user", None)
        return update_student(student=instance, actor=actor, **validated_data)


class StudentDossierSerializer(StudentSerializer):
    actions = serializers.SerializerMethodField()

    class Meta(StudentSerializer.Meta):
        fields = [*StudentSerializer.Meta.fields, "actions"]

    def get_actions(self, instance) -> dict[str, bool]:
        return services.student_dossier_actions(
            student=instance, can_manage=instance.record_can_manage
        )


class GuardianSerializer(serializers.ModelSerializer):
    person = PersonSerializer()

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

    def create(self, validated_data):
        person_data = validated_data.pop("person")
        actor = getattr(self.context.get("request"), "user", None)
        return create_guardian(person_data=person_data, actor=actor)

    def validate(self, attrs):
        if self.instance is None:
            validate_institutional_person(attrs.get("person"))
        return attrs

    def update(self, instance, validated_data):
        # Nested person edits aren't supported yet — edit via /api/v1/people/<id>/.
        validated_data.pop("person", None)
        return super().update(instance, validated_data)


class StudentGuardianRelationQuerySerializer(serializers.Serializer):
    student_id = serializers.UUIDField(required=False)


class StudentGuardianRelationSerializer(serializers.ModelSerializer):
    guardian_detail = GuardianSerializer(source="guardian", read_only=True)

    class Meta:
        model = StudentGuardianRelation
        fields = [
            "id",
            "student",
            "guardian",
            "guardian_detail",
            "relationship_label",
            "is_primary",
            "starts_at",
            "ends_at",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "is_primary",
            "ends_at",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        actor = getattr(self.context.get("request"), "user", None)
        return create_student_guardian_relation(actor=actor, **validated_data)


class StudentRecordGuardianRelationSerializer(StudentGuardianRelationSerializer):
    actions = serializers.SerializerMethodField()

    class Meta(StudentGuardianRelationSerializer.Meta):
        fields = [*StudentGuardianRelationSerializer.Meta.fields, "actions"]

    def get_actions(self, instance) -> dict[str, bool]:
        return guardian_relation_actions(relation=instance, can_manage=instance.record_can_manage)


class StudentRecordGuardiansQuerySerializer(serializers.Serializer):
    replacement_for = serializers.IntegerField(min_value=1, required=False)


class StudentGuardianRelationUpdateSerializer(serializers.Serializer):
    relationship_label = serializers.CharField(max_length=100)

    def validate(self, attrs):
        if set(self.initial_data) - {"relationship_label"}:
            raise serializers.ValidationError(
                "Solo se puede editar el parentesco o responsabilidad."
            )
        return attrs


class StudentGuardianRelationEndSerializer(serializers.Serializer):
    replacement_relation = serializers.PrimaryKeyRelatedField(
        queryset=StudentGuardianRelation.objects.all(),
        required=False,
        allow_null=True,
    )


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


class StudentHealthNoteSerializer(serializers.ModelSerializer):
    student = StudentRefSerializer(read_only=True)
    author = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = StudentHealthNote
        fields = [
            "public_id",
            "student",
            "author",
            "content",
            "recorded_on",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class StudentHealthNoteCreateSerializer(serializers.Serializer):
    content = serializers.CharField()
    recorded_on = serializers.DateField(required=False)


class StudentObservationSerializer(serializers.ModelSerializer):
    student = StudentRefSerializer(read_only=True)
    author = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = StudentObservation
        fields = [
            "public_id",
            "student",
            "author",
            "description",
            "observed_on",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class StudentObservationCreateSerializer(serializers.Serializer):
    description = serializers.CharField()
    observed_on = serializers.DateField(required=False)


class StudentRecordContentUpdateSerializer(serializers.Serializer):
    """Corrections may not rewrite author, dates, owner or active state."""

    def validate(self, attrs):
        if set(self.initial_data) - set(self.fields):
            raise serializers.ValidationError("Solo se puede corregir el contenido del registro.")
        return attrs


class StudentHealthNoteUpdateSerializer(StudentRecordContentUpdateSerializer):
    content = serializers.CharField()


class StudentObservationUpdateSerializer(StudentRecordContentUpdateSerializer):
    description = serializers.CharField()


class StudentRecordActionsMixin:
    def get_actions(self, instance) -> dict[str, bool]:
        return student_record_actions(record=instance, can_manage=instance.record_can_manage)


class StudentHealthNoteListSerializer(StudentRecordActionsMixin, StudentHealthNoteSerializer):
    actions = serializers.SerializerMethodField()

    class Meta(StudentHealthNoteSerializer.Meta):
        fields = [*StudentHealthNoteSerializer.Meta.fields, "actions"]


class StudentObservationListSerializer(StudentRecordActionsMixin, StudentObservationSerializer):
    actions = serializers.SerializerMethodField()

    class Meta(StudentObservationSerializer.Meta):
        fields = [*StudentObservationSerializer.Meta.fields, "actions"]


class EmergencyContactListSerializer(StudentRecordActionsMixin, EmergencyContactSerializer):
    actions = serializers.SerializerMethodField()

    class Meta(EmergencyContactSerializer.Meta):
        fields = [*EmergencyContactSerializer.Meta.fields, "actions"]
