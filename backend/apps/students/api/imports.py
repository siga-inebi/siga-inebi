"""
HTTP de la importacion CSV de estudiantes (todo o nada).

Las vistas solo traducen HTTP: leer el archivo, autorizar y elegir el codigo
de estado. Toda regla vive en ``apps.students.imports`` (AGENTS.md #8). El
permiso es el mismo del alta individual (``student.edit_basic`` con alcance
``students``), porque importar es dar de alta varias veces.
"""

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.common.exceptions import AuthorizationError
from apps.students import imports

TAGS = ["students"]
CREATE_PERMISSION = "student_edit_basic"
CREATE_SCOPE = {"module_key": "students"}

ACCEPTED_VALUES = (
    "Columnas: `nombres` y `apellidos` obligatorias; `cui` (13 digitos), "
    "`fecha_nacimiento` (AAAA-MM-DD), `sexo`, `correo`, `telefono` y "
    "`codigo_estudiante` opcionales. `sexo` acepta `F`, `Femenino`, `female`, "
    "`M`, `Masculino`, `male`, `No especificado`, `not_specified` o vacio (no "
    "especificado), sin distinguir mayusculas ni tildes. Sin "
    "`codigo_estudiante` se genera el siguiente de la serie del anio. Un CUI que "
    "ya pertenece a una persona registrada es un error: esa persona se da de "
    "alta desde «Convertir persona»."
)


def _require_create_permission(user):
    if not user.has_scoped_permission(CREATE_PERMISSION, scope=CREATE_SCOPE):
        raise AuthorizationError("El actor no tiene el permiso o el alcance requerido.")


def _read_upload(uploaded):
    if uploaded.size > imports.MAX_IMPORT_BYTES:
        raise serializers.ValidationError(
            {"file": f"El archivo supera el máximo de {imports.MAX_IMPORT_BYTES // 1024} KB."}
        )
    return uploaded.read()


class StudentImportUploadSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="CSV en UTF-8 con las columnas de la plantilla.")


class StudentImportConfirmSerializer(StudentImportUploadSerializer):
    file_sha256 = serializers.CharField(
        max_length=64, help_text="Huella SHA-256 devuelta por la vista previa."
    )


class StudentImportRowDataSerializer(serializers.Serializer):
    nombres = serializers.CharField()
    apellidos = serializers.CharField()
    cui = serializers.CharField()
    fecha_nacimiento = serializers.CharField()
    sexo = serializers.CharField()
    correo = serializers.CharField()
    telefono = serializers.CharField()
    codigo_estudiante = serializers.CharField()


class StudentImportRowSerializer(serializers.Serializer):
    line = serializers.IntegerField(help_text="Linea del archivo (el encabezado es la 1).")
    data = StudentImportRowDataSerializer()
    status = serializers.ChoiceField(choices=[imports.STATUS_READY, imports.STATUS_ERROR])
    errors = serializers.ListField(child=serializers.CharField())


class StudentImportSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    ready = serializers.IntegerField()
    errors = serializers.IntegerField()


class StudentImportPreviewSerializer(serializers.Serializer):
    file_sha256 = serializers.CharField()
    summary = StudentImportSummarySerializer()
    rows = StudentImportRowSerializer(many=True)


class ImportedStudentSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    student_code = serializers.CharField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, student) -> str:
        return f"{student.person.first_name} {student.person.last_name}".strip()


class StudentImportResultSerializer(serializers.Serializer):
    created = serializers.IntegerField()
    students = ImportedStudentSerializer(many=True)


class StudentImportConflictSerializer(serializers.Serializer):
    detail = serializers.CharField()


def _preview_body(result):
    return StudentImportPreviewSerializer(
        {"file_sha256": result.file_sha256, "summary": result.summary, "rows": result.rows}
    ).data


@extend_schema_view(
    get=extend_schema(
        summary="Plantilla CSV de importacion de estudiantes",
        description=(
            "CSV en UTF-8 con BOM y solo la fila de encabezados: "
            f"`{','.join(imports.TEMPLATE_COLUMNS)}`. " + ACCEPTED_VALUES
        ),
        tags=TAGS,
        responses={(200, "text/csv"): OpenApiTypes.STR},
    )
)
class StudentImportTemplateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        _require_create_permission(request.user)
        response = HttpResponse(
            imports.import_template_csv(), content_type="text/csv; charset=utf-8"
        )
        response["Content-Disposition"] = 'attachment; filename="plantilla-estudiantes.csv"'
        response["Access-Control-Expose-Headers"] = "Content-Disposition"
        return response


@extend_schema_view(
    post=extend_schema(
        summary="Vista previa de importacion de estudiantes",
        description=(
            "Multipart con `file`. Valida cada fila con el mismo servicio del alta "
            f"y no guarda nada. Maximo {imports.MAX_IMPORT_ROWS} filas. Un archivo "
            "vacio, sin UTF-8, demasiado grande o con encabezados distintos de la "
            "plantilla responde 400. Devuelve `file_sha256`, que la confirmacion "
            "debe reenviar. " + ACCEPTED_VALUES
        ),
        tags=TAGS,
        request={"multipart/form-data": StudentImportUploadSerializer},
        responses={200: StudentImportPreviewSerializer},
    )
)
class StudentImportPreviewView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = StudentImportUploadSerializer

    def post(self, request):
        _require_create_permission(request.user)
        serializer = StudentImportUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = imports.preview_student_import(
            raw=_read_upload(serializer.validated_data["file"]), actor=request.user
        )
        return Response(_preview_body(result))


@extend_schema_view(
    post=extend_schema(
        summary="Confirmar importacion de estudiantes",
        description=(
            "Multipart con `file` y `file_sha256` de la vista previa. Todo o nada: "
            "201 con los estudiantes creados; 409 `{detail}` si el archivo no es el "
            "de la vista previa; 422 con el mismo cuerpo de la vista previa si "
            "alguna fila falla, sin crear ninguna."
        ),
        tags=TAGS,
        request={"multipart/form-data": StudentImportConfirmSerializer},
        responses={
            201: StudentImportResultSerializer,
            409: StudentImportConflictSerializer,
            422: StudentImportPreviewSerializer,
        },
    )
)
class StudentImportConfirmView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = StudentImportConfirmSerializer

    def post(self, request):
        _require_create_permission(request.user)
        serializer = StudentImportConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = imports.confirm_student_import(
                raw=_read_upload(serializer.validated_data["file"]),
                expected_sha256=serializer.validated_data["file_sha256"],
                actor=request.user,
            )
        except imports.ImportFileChanged as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        if result.has_errors:
            return Response(_preview_body(result), status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        students = result.students
        return Response(
            StudentImportResultSerializer({"created": len(students), "students": students}).data,
            status=status.HTTP_201_CREATED,
        )
