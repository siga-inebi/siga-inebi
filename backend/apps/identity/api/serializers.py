"""
Contratos HTTP de identidad y acceso.

Ningun contrato publico de cuentas, asignaciones o alcances recibe ni devuelve
ids internos (docs/ux-ui.md U1 y RA1; ADR-0011): las cuentas se identifican por
``public_id`` y los alcances nombran institucion, ciclo, grado, seccion, curso,
asignacion docente y estudiante por su ``public_id``.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.academics.api.serializers import (
    ClassScheduleBlockRefSerializer,
    SectionRefSerializer,
    SubjectRefSerializer,
)
from apps.academics.models import (
    AcademicCycle,
    ClassSession,
    Grade,
    Institution,
    Section,
    Subject,
    TeachingAssignment,
)
from apps.identity.atomic_permissions import (
    ATOMIC_PERMISSION_CODES_BY_CODENAME,
    ATOMIC_PERMISSIONS,
    PERMISSION_DETAILS,
    PERMISSION_GROUP_LABELS,
    permission_codename,
)
from apps.identity.services import (
    SCOPE_MODULES,
    assignment_status,
    describe_scope_grant,
)
from apps.people.models import Person
from apps.students.models import Student

ASSIGNMENT_STATUS_LABELS = {
    "active": "Vigente",
    "expiring": "Por vencer",
    "scheduled": "Programada",
    "ended": "Finalizada",
}


def _full_name(person):
    if person is None:
        return ""
    return f"{person.first_name} {person.last_name}".strip()


class PersonRefSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj) -> str:
        return _full_name(obj)


class AccountProvisionSerializer(serializers.Serializer):
    ACCOUNT_KIND_CHOICES = (
        ("institutional", "Cuenta institucional"),
        ("guardian", "Cuenta de encargado"),
    )

    # U1: la persona se identifica por su public_id, el unico que `/people/`
    # expone. El contrato anterior pedia el id entero interno (`person`).
    person_public_id = serializers.SlugRelatedField(
        slug_field="public_id", queryset=Person.objects.all()
    )
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    # D9: el backend conserva las cuentas de encargado; la interfaz no las ofrece.
    account_kind = serializers.ChoiceField(
        choices=ACCOUNT_KIND_CHOICES,
        default="institutional",
        required=False,
    )

    def validate_username(self, value):
        if get_user_model().objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este usuario.")
        return value

    def validated_service_data(self):
        data = dict(self.validated_data)
        data["person"] = data.pop("person_public_id")
        return data


class ProvisionedAccountSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    username = serializers.CharField()
    email = serializers.EmailField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    person_public_id = serializers.UUIDField()
    activation_code = serializers.CharField()
    activation_expires_at = serializers.DateTimeField()


class ActivationChallengeSerializer(serializers.Serializer):
    account = serializers.UUIDField(help_text="public_id de la cuenta.")
    activation_code = serializers.CharField()
    activation_expires_at = serializers.DateTimeField()
    max_attempts = serializers.IntegerField()


class AccountActivationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    activation_code = serializers.CharField(max_length=8, trim_whitespace=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class ActivatedAccountSerializer(serializers.Serializer):
    username = serializers.CharField()
    status = serializers.CharField()


class AtomicPermissionSerializer(serializers.Serializer):
    """RO2: codigo publico, etiqueta y descripcion en espanol, y grupo funcional."""

    code = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    group = serializers.SerializerMethodField()
    group_label = serializers.SerializerMethodField()

    def _details(self, obj):
        return PERMISSION_DETAILS[ATOMIC_PERMISSION_CODES_BY_CODENAME[obj.codename]]

    def get_code(self, obj) -> str:
        return ATOMIC_PERMISSION_CODES_BY_CODENAME[obj.codename]

    def get_name(self, obj) -> str:
        return self._details(obj)["label"]

    def get_description(self, obj) -> str:
        return self._details(obj)["description"]

    def get_group(self, obj) -> str:
        return self._details(obj)["group"]

    def get_group_label(self, obj) -> str:
        return PERMISSION_GROUP_LABELS[self._details(obj)["group"]]


class RoleSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.SlugField()
    description = serializers.CharField()
    is_system = serializers.BooleanField()
    is_active = serializers.BooleanField()
    session_idle_timeout_minutes = serializers.IntegerField()
    active_account_count = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    def get_active_account_count(self, obj) -> int | None:
        return getattr(obj, "active_account_count", None)

    def get_permissions(self, obj) -> list[str]:
        return sorted(
            ATOMIC_PERMISSION_CODES_BY_CODENAME[permission.codename]
            for permission in obj.permissions.all()
            if permission.codename in ATOMIC_PERMISSION_CODES_BY_CODENAME
        )


class RoleWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    # RO3: opcional; si no se envia se deriva del nombre.
    slug = serializers.SlugField(max_length=150, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    session_idle_timeout_minutes = serializers.IntegerField(min_value=1, required=False)
    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=[code for code, _name in ATOMIC_PERMISSIONS]),
        required=False,
    )

    def validate(self, attrs):
        if not self.partial and "name" not in attrs:
            raise serializers.ValidationError({"name": "Este campo es obligatorio."})
        return attrs

    def validate_permissions(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("No se permiten permisos duplicados.")
        return value

    def validated_service_data(self):
        data = dict(self.validated_data)
        if "permissions" in data:
            data["permission_codenames"] = [
                permission_codename(code) for code in data.pop("permissions")
            ]
        return data


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(
        max_length=500, help_text="Motivo declarado de la operacion; queda en la bitacora."
    )


def _public_id_field(queryset, label):
    return serializers.SlugRelatedField(
        slug_field="public_id",
        queryset=queryset,
        required=False,
        help_text=f"public_id de {label}.",
    )


class ScopeGrantWriteSerializer(serializers.Serializer):
    """RA1: cada dimension del alcance se nombra por ``public_id``."""

    institution = _public_id_field(Institution.objects.all(), "la institucion")
    academic_cycle = _public_id_field(AcademicCycle.objects.all(), "el ciclo escolar")
    grade = _public_id_field(Grade.objects.all(), "el grado")
    section = _public_id_field(Section.objects.all(), "la seccion")
    subject = _public_id_field(Subject.objects.all(), "el curso")
    teaching_assignment = _public_id_field(
        TeachingAssignment.objects.all(), "la asignacion docente"
    )
    student = _public_id_field(Student.objects.all(), "el estudiante")
    module_key = serializers.ChoiceField(choices=SCOPE_MODULES, required=False)
    teaching_assignments = serializers.BooleanField(
        required=False,
        default=False,
        help_text=(
            "RA4: usar las asignaciones docentes vigentes de la persona como alcance. "
            "Solo para cuentas de docentes."
        ),
    )
    starts_at = serializers.DateTimeField(required=False)
    ends_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        dimensions = {
            "institution",
            "academic_cycle",
            "grade",
            "section",
            "subject",
            "teaching_assignment",
            "student",
            "module_key",
        }
        if not dimensions.intersection(attrs) and not attrs.get("teaching_assignments"):
            raise serializers.ValidationError("Debe indicar al menos una dimensión de alcance.")
        starts_at = attrs.get("starts_at")
        ends_at = attrs.get("ends_at")
        if starts_at and ends_at and ends_at < starts_at:
            raise serializers.ValidationError(
                {"ends_at": "La fecha final no puede ser anterior a la inicial."}
            )
        return attrs


class RoleAssignmentWriteSerializer(serializers.Serializer):
    role = serializers.UUIDField(help_text="public_id del rol.")
    starts_at = serializers.DateTimeField(required=False)
    ends_at = serializers.DateTimeField(required=False, allow_null=True)
    scope = ScopeGrantWriteSerializer(required=True)

    def validate(self, attrs):
        starts_at = attrs.get("starts_at")
        ends_at = attrs.get("ends_at")
        if starts_at and ends_at and ends_at < starts_at:
            raise serializers.ValidationError(
                {"ends_at": "La fecha final no puede ser anterior a la inicial."}
            )
        return attrs


class ScopeDimensionSerializer(serializers.Serializer):
    dimension = serializers.CharField()
    public_id = serializers.UUIDField(allow_null=True)
    value = serializers.CharField(required=False)
    label = serializers.CharField()


class ScopeGrantSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField(allow_null=True)
    dimensions = serializers.SerializerMethodField()

    def get_dimensions(self, obj) -> list[dict]:
        return ScopeDimensionSerializer(describe_scope_grant(obj), many=True).data


class RoleAssignmentSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    account = serializers.UUIDField(source="user.public_id")
    role = serializers.UUIDField(source="role.public_id")
    role_name = serializers.CharField(source="role.name")
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField(allow_null=True)
    status = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    scopes = serializers.SerializerMethodField()

    def get_status(self, obj) -> str:
        return assignment_status(obj)

    def get_status_display(self, obj) -> str:
        return ASSIGNMENT_STATUS_LABELS[assignment_status(obj)]

    def get_scopes(self, obj) -> list[dict]:
        return ScopeGrantSerializer(obj.scope_grants.all(), many=True).data


class AccountRoleRefSerializer(serializers.Serializer):
    public_id = serializers.UUIDField(source="role.public_id")
    name = serializers.CharField(source="role.name")
    ends_at = serializers.DateTimeField(allow_null=True)


class AccountListSerializer(serializers.ModelSerializer):
    """U4: cuenta para el listado de administracion, sin ids internos."""

    person_name = serializers.SerializerMethodField()
    person = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    roles = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = [
            "public_id",
            "username",
            "email",
            "status",
            "status_display",
            "is_active",
            "person_name",
            "person",
            "roles",
            "last_login",
            "locked_until",
            "is_locked",
        ]
        read_only_fields = fields

    def get_person_name(self, obj) -> str:
        return _full_name(obj.person)

    def get_person(self, obj) -> dict | None:
        if obj.person is None:
            return None
        return {
            "public_id": str(obj.person.public_id),
            "full_name": _full_name(obj.person),
            "email": obj.person.email,
            # RA4: el asistente solo ofrece "sus asignaciones docentes" a docentes.
            "is_teacher": hasattr(obj.person, "teacher_profile"),
        }

    def get_roles(self, obj) -> list[dict]:
        assignments = getattr(obj, "current_assignments", None)
        if assignments is None:
            return []
        return AccountRoleRefSerializer(assignments, many=True).data

    def get_is_locked(self, obj) -> bool:
        return obj.is_locked()


class AccountSessionSerializer(serializers.Serializer):
    """Sesion viva (riesgo A, ADR-0011): sin clave de sesion, por ``public_id``."""

    public_id = serializers.UUIDField()
    started_at = serializers.DateTimeField()
    last_activity_at = serializers.DateTimeField(allow_null=True)
    expires_at = serializers.DateTimeField(allow_null=True)
    ip_address = serializers.IPAddressField(allow_null=True)
    device = serializers.CharField()
    is_current = serializers.BooleanField()


class AccountActivityEventSerializer(serializers.Serializer):
    action = serializers.CharField()
    created_at = serializers.DateTimeField()
    ip_address = serializers.IPAddressField(allow_null=True)
    actor_label = serializers.CharField(allow_blank=True)
    result = serializers.SerializerMethodField()

    def get_result(self, obj) -> str:
        return (obj.context or {}).get("result", "")


class AccountDetailSerializer(AccountListSerializer):
    """U5: ficha de la cuenta."""

    class Meta(AccountListSerializer.Meta):
        fields = [
            *AccountListSerializer.Meta.fields,
            "date_joined",
            "failed_login_attempts",
        ]
        read_only_fields = fields


class AccountUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)


class AccountDisableSerializer(serializers.Serializer):
    force = serializers.BooleanField(default=False)
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Motivo declarado de la desactivacion (RF-BIT-002).",
    )


class ReactivatedAccountSerializer(serializers.Serializer):
    account = AccountListSerializer()
    activation_code = serializers.CharField()
    activation_expires_at = serializers.DateTimeField()


class PasswordResetIssueResultSerializer(serializers.Serializer):
    token = serializers.CharField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)


class PasswordResetConsumeSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, trim_whitespace=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class PasswordPolicySerializer(serializers.Serializer):
    rules = serializers.ListField(child=serializers.CharField())


class AccountCandidateSerializer(serializers.Serializer):
    """U1/D10: persona sin cuenta, para dar acceso al sistema."""

    public_id = serializers.UUIDField()
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField()
    cui_hint = serializers.SerializerMethodField()
    profiles = serializers.SerializerMethodField()

    def get_full_name(self, obj) -> str:
        return _full_name(obj)

    def get_cui_hint(self, obj) -> str:
        # Minimizacion (RNF-LEG-001): basta con los ultimos digitos para distinguir.
        return f"…{obj.cui[-4:]}" if obj.cui else ""

    def get_profiles(self, obj) -> list[str]:
        # `RelatedObjectDoesNotExist` hereda de AttributeError: hasattr basta.
        return [
            label
            for attribute, label in (
                ("teacher_profile", "teacher"),
                ("student_profile", "student"),
                ("guardian_profile", "guardian"),
            )
            if hasattr(obj, attribute)
        ]


class UsernameSuggestionSerializer(serializers.Serializer):
    username = serializers.CharField()


class RoleHolderSerializer(serializers.Serializer):
    assignment = serializers.UUIDField(source="public_id")
    account = serializers.UUIDField(source="user.public_id")
    username = serializers.CharField(source="user.username")
    person_name = serializers.SerializerMethodField()
    role = serializers.UUIDField(source="role.public_id")
    role_name = serializers.CharField(source="role.name")
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField(allow_null=True)
    status = serializers.SerializerMethodField()

    def get_person_name(self, obj) -> str:
        return _full_name(obj.user.person)

    def get_status(self, obj) -> str:
        return assignment_status(obj)


class ScopeModuleSerializer(serializers.Serializer):
    value = serializers.CharField()
    label = serializers.CharField()


class InstitutionRefSerializer(serializers.Serializer):
    public_id = serializers.UUIDField()
    name = serializers.CharField()


class ScopeOptionsSerializer(serializers.Serializer):
    modules = ScopeModuleSerializer(many=True)
    institution = InstitutionRefSerializer(allow_null=True)


class MyAccountSerializer(serializers.Serializer):
    """MC1: datos de la persona, cuenta, roles con alcances y sesiones propias."""

    account = AccountListSerializer()
    person = serializers.DictField()
    roles = RoleAssignmentSerializer(many=True)
    sessions = AccountSessionSerializer(many=True)
    session_idle_timeout_minutes = serializers.IntegerField()
    permissions = serializers.ListField(child=serializers.CharField())


class MyClassSessionSerializer(serializers.ModelSerializer):
    """RF-HOR-010: one row of the caller's own weekly schedule."""

    section = SectionRefSerializer(read_only=True)
    subject = SubjectRefSerializer(read_only=True)
    schedule_block = ClassScheduleBlockRefSerializer(read_only=True)
    day_of_week_display = serializers.CharField(source="get_day_of_week_display", read_only=True)
    teacher_id = serializers.SerializerMethodField()

    class Meta:
        model = ClassSession
        fields = [
            "public_id",
            "day_of_week",
            "day_of_week_display",
            "section",
            "subject",
            "schedule_block",
            "teacher_id",
        ]

    def get_teacher_id(self, obj):
        teacher = obj.current_teacher
        return str(teacher.teacher_profile.public_id) if teacher else None
