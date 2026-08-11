from rest_framework import serializers

from apps.documents.models import DocumentTemplate


class DocumentTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentTemplate
        fields = [
            "public_id",
            "name",
            "code",
            "kind",
            "description",
            "is_active",
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
