from rest_framework import serializers

from apps.documents.models import DocumentTemplate, DocumentTemplateVersion


class OfficialDocumentEligibilitySerializer(serializers.Serializer):
    enrolment_id = serializers.UUIDField(help_text="Public ID de la matrícula.")


class OfficialDocumentEligibilityResponseSerializer(serializers.Serializer):
    eligible = serializers.BooleanField()


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


class DocumentTemplateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    kind = serializers.ChoiceField(choices=DocumentTemplate.TemplateKind.choices, required=False)


class FieldTagSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()
    sensitive = serializers.BooleanField()


class DocumentTemplateVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentTemplateVersion
        fields = ["public_id", "sequence", "name", "kind", "description", "created_at"]
