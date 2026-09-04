from rest_framework import serializers

from apps.documents.models import DocumentDeliveryReceipt, DocumentTemplate, DocumentTemplateVersion
from apps.students.models import Guardian, Student


class InstitutionalHeaderSerializer(serializers.Serializer):
    institution_name = serializers.CharField()
    institution_short_name = serializers.CharField()
    logo_url = serializers.CharField(allow_null=True)


class DocumentTemplateSerializer(serializers.ModelSerializer):
    """``header`` is read-only and derived; it cannot be set via create/update payloads."""

    header = InstitutionalHeaderSerializer(source="institutional_header", read_only=True)

    class Meta:
        model = DocumentTemplate
        fields = [
            "public_id",
            "name",
            "code",
            "kind",
            "description",
            "content",
            "is_active",
            "header",
        ]


class DocumentTemplateCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, help_text="Nombre visible de la plantilla.")
    code = serializers.CharField(
        max_length=30,
        help_text="Codigo corto, unico por institucion. Se normaliza a mayusculas.",
    )
    kind = serializers.ChoiceField(
        choices=DocumentTemplate.TemplateKind.choices,
        required=False,
        default=DocumentTemplate.TemplateKind.OTHER,
        help_text="Tipo de plantilla: certificado, reporte u otro.",
    )
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    content = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Contenido base de la plantilla con marcadores cerrados.",
    )


class DocumentTemplateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    kind = serializers.ChoiceField(choices=DocumentTemplate.TemplateKind.choices, required=False)
    content = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Nuevo contenido de la plantilla antes de publicar.",
    )


class FieldTagSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()
    sensitive = serializers.BooleanField()


class DocumentTemplateTypeSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()


class DocumentTemplateVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentTemplateVersion
        fields = ["public_id", "sequence", "name", "kind", "description", "content", "created_at"]


class DocumentDeliveryReceiptSerializer(serializers.ModelSerializer):
    student_id = serializers.UUIDField(source="student.public_id", read_only=True)
    guardian_id = serializers.UUIDField(source="guardian.public_id", read_only=True)

    class Meta:
        model = DocumentDeliveryReceipt
        fields = [
            "public_id",
            "student_id",
            "guardian_id",
            "document_type",
            "folio",
            "recipient_name",
            "delivered_at",
            "notes",
        ]


class DocumentDeliveryReceiptCreateSerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    guardian_id = serializers.UUIDField()
    document_type = serializers.CharField(max_length=100)
    folio = serializers.CharField(max_length=100, required=False, allow_blank=True)
    recipient_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        student_id = attrs["student_id"]
        guardian_id = attrs["guardian_id"]
        student = Student.objects.filter(public_id=student_id).first()
        guardian = Guardian.objects.filter(public_id=guardian_id).first()
        if student is None:
            raise serializers.ValidationError({"student_id": "No existe el estudiante indicado."})
        if guardian is None:
            raise serializers.ValidationError({"guardian_id": "No existe el encargado indicado."})
        attrs["student"] = student
        attrs["guardian"] = guardian
        return attrs


class OfficialDocumentEligibilityQuerySerializer(serializers.Serializer):
    enrolment_id = serializers.UUIDField(help_text="Public ID de la matrícula.")


class OfficialDocumentEligibilityResponseSerializer(serializers.Serializer):
    eligible = serializers.BooleanField()
    blocking_document_codes = serializers.ListField(
        child=serializers.CharField(),
        help_text="Codigos de los documentos obligatorios pendientes que bloquean la emision.",
    )


class DocumentTemplatePreviewSerializer(serializers.Serializer):
    payload = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        default=dict,
        help_text="Mapa de marcadores permitidos a valores a interpolar.",
    )


class DocumentTemplatePreviewResponseSerializer(serializers.Serializer):
    content = serializers.CharField()
    markers = serializers.ListField(child=serializers.CharField())
    marker_count = serializers.IntegerField()
