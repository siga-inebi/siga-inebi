"""
HTTP de identidad y acceso. Las vistas solo traducen: las reglas (quien puede,
que estados admiten cada operacion, que se audita) viven en
``apps.identity.services`` y las lecturas en ``apps.identity.queries``.

Las cuentas se direccionan por ``public_id`` (ADR-0011): ninguna ruta ni
respuesta de este modulo usa el id entero interno.
"""

from django.conf import settings
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.academics import queries as academic_queries
from apps.audit import queries as audit_queries
from apps.common.exceptions import ResourceNotFoundError
from apps.identity import queries
from apps.identity.api.permissions import ScopedAtomicPermission
from apps.identity.api.serializers import (
    AccountActivationSerializer,
    AccountActivityEventSerializer,
    AccountCandidateSerializer,
    AccountDetailSerializer,
    AccountDisableSerializer,
    AccountListSerializer,
    AccountProvisionSerializer,
    AccountSessionSerializer,
    AccountUpdateSerializer,
    ActivatedAccountSerializer,
    ActivationChallengeSerializer,
    AtomicPermissionSerializer,
    MyAccountSerializer,
    MyClassSessionSerializer,
    PasswordPolicySerializer,
    PasswordResetConsumeSerializer,
    PasswordResetIssueResultSerializer,
    ProvisionedAccountSerializer,
    ReactivatedAccountSerializer,
    ReasonSerializer,
    RoleAssignmentSerializer,
    RoleAssignmentWriteSerializer,
    RoleHolderSerializer,
    RoleSerializer,
    RoleWriteSerializer,
    ScopeOptionsSerializer,
    UsernameSuggestionSerializer,
)
from apps.identity.atomic_permissions import ATOMIC_PERMISSION_CODES_BY_CODENAME
from apps.identity.services import (
    ACCOUNT_CREATE_PERMISSION,
    EXPIRING_ASSIGNMENT_DAYS,
    SCOPE_MODULES,
    account_sessions,
    activate_account,
    assign_role,
    close_account_sessions,
    consume_password_reset,
    create_role,
    deactivate_role,
    disable_account,
    effective_permission_codes,
    effective_session_idle_timeout_minutes,
    issue_password_reset,
    list_atomic_permissions,
    list_roles,
    my_weekly_schedule,
    password_policy_rules,
    provision_account_with_activation,
    reactivate_account,
    reactivate_role,
    reissue_activation_challenge,
    revoke_role_assignment,
    suggest_username,
    unlock_account,
    update_account,
    update_role,
)

IDENTITY_SCOPE = {"module_key": "identity"}

#: Cualquiera de estos permisos habilita la consulta de cuentas: quien crea,
#: activa o desactiva cuentas necesita encontrarlas.
ACCOUNT_ADMIN_CODENAMES = ("account_disable", "account_create", "account_activate")


def _no_store(response):
    response["Cache-Control"] = "no-store"
    return response


def _bool_param(value):
    return str(value).lower() in {"1", "true", "yes"}


class AccountAdminView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, ScopedAtomicPermission]
    permission_codenames = ACCOUNT_ADMIN_CODENAMES
    permission_scope = IDENTITY_SCOPE


class RoleAdminView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, ScopedAtomicPermission]
    permission_codename = "role_assign"
    permission_scope = IDENTITY_SCOPE


# --------------------------------------------------------------------------- #
# Publicos: activacion, restablecimiento y reglas de contraseña
# --------------------------------------------------------------------------- #


class AccountActivationView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = AccountActivationSerializer

    @extend_schema(
        request=AccountActivationSerializer,
        responses={200: ActivatedAccountSerializer},
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = activate_account(**serializer.validated_data)
        return _no_store(Response({"username": account.username, "status": account.status}))


class PasswordResetConsumeView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConsumeSerializer

    @extend_schema(
        request=PasswordResetConsumeSerializer,
        responses={204: OpenApiResponse(description="Contraseña restablecida")},
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        consume_password_reset(
            token=serializer.validated_data["token"],
            new_password=serializer.validated_data["password"],
        )
        return _no_store(Response(status=status.HTTP_204_NO_CONTENT))


class PasswordPolicyView(GenericAPIView):
    """MC2: reglas reales de contraseña, publicas porque las usan activar y restablecer."""

    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordPolicySerializer

    @extend_schema(responses={200: PasswordPolicySerializer})
    def get(self, request):
        return Response({"rules": password_policy_rules()})


# --------------------------------------------------------------------------- #
# Cuenta propia
# --------------------------------------------------------------------------- #


class MyWeeklyScheduleView(GenericAPIView):
    """
    RF-HOR-010: the caller's own weekly schedule -- their teaching sessions,
    or their wards' sections' sessions, from published cycles only.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MyClassSessionSerializer

    @extend_schema(responses={200: MyClassSessionSerializer(many=True)})
    def get(self, request):
        queryset = my_weekly_schedule(actor=request.user)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class MyAccountView(GenericAPIView):
    """MC1: datos de la persona, cuenta, roles con alcances y sesiones propias."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MyAccountSerializer

    @extend_schema(responses={200: MyAccountSerializer})
    def get(self, request):
        user = request.user
        account = queries.account_detail(user.public_id)
        person = user.person
        payload = {
            "account": AccountListSerializer(account).data,
            "person": {
                "public_id": str(person.public_id),
                "first_name": person.first_name,
                "last_name": person.last_name,
                "email": person.email,
                "phone_number": person.phone_number,
            },
            "roles": RoleAssignmentSerializer(
                queries.current_role_assignments(user), many=True
            ).data,
            "sessions": AccountSessionSerializer(
                account_sessions(user=user, current_session_key=request.session.session_key),
                many=True,
            ).data,
            "session_idle_timeout_minutes": effective_session_idle_timeout_minutes(user=user),
            "permissions": effective_permission_codes(user=user),
        }
        return _no_store(Response(payload))


# --------------------------------------------------------------------------- #
# Permisos y roles (RF-PER, RO1-RO6)
# --------------------------------------------------------------------------- #


class AtomicPermissionListView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AtomicPermissionSerializer

    @extend_schema(responses={200: AtomicPermissionSerializer(many=True)})
    def get(self, request):
        queryset = list_atomic_permissions(actor=request.user)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class PermissionHolderListView(RoleAdminView):
    """RO5: quien tiene un permiso, a traves de que rol."""

    serializer_class = RoleHolderSerializer

    @extend_schema(responses={200: RoleHolderSerializer(many=True)})
    def get(self, request, code):
        codename = code.replace(".", "_")
        if codename not in ATOMIC_PERMISSION_CODES_BY_CODENAME:
            raise ResourceNotFoundError("No se encontró el permiso.")
        page = self.paginate_queryset(queries.permission_holders(codename))
        return self.get_paginated_response(RoleHolderSerializer(page, many=True).data)


class ScopeOptionsView(RoleAdminView):
    """
    RA3: lo que el asistente necesita para armar un alcance sin ids internos:
    los modulos que un alcance puede nombrar y la institucion (una sola por
    despliegue), con su ``public_id``.
    """

    serializer_class = ScopeOptionsSerializer

    @extend_schema(responses={200: ScopeOptionsSerializer})
    def get(self, request):
        try:
            institution = academic_queries.resolve_institution()
        except ResourceNotFoundError:
            institution = None
        return Response(
            {
                "modules": [{"value": value, "label": label} for value, label in SCOPE_MODULES],
                "institution": (
                    {"public_id": str(institution.public_id), "name": institution.name}
                    if institution
                    else None
                ),
            }
        )


class RoleListCreateView(RoleAdminView):
    serializer_class = RoleWriteSerializer

    @extend_schema(
        parameters=[OpenApiParameter("include_inactive", OpenApiTypes.BOOL)],
        responses={200: RoleSerializer(many=True)},
    )
    def get(self, request):
        include_inactive = request.query_params.get("include_inactive")
        queryset = list_roles(
            actor=request.user,
            include_inactive=True if include_inactive is None else _bool_param(include_inactive),
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(RoleSerializer(page, many=True).data)

    @extend_schema(request=RoleWriteSerializer, responses={201: RoleSerializer})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = create_role(actor=request.user, **serializer.validated_service_data())
        return Response(RoleSerializer(role).data, status=status.HTTP_201_CREATED)


class RoleDetailView(RoleAdminView):
    serializer_class = RoleWriteSerializer

    @extend_schema(responses={200: RoleSerializer})
    def get(self, request, role_id):
        role = queries.role_or_404(role_id)
        annotated = list_roles(actor=request.user).get(pk=role.pk)
        return Response(RoleSerializer(annotated).data)

    @extend_schema(request=RoleWriteSerializer, responses={200: RoleSerializer})
    def patch(self, request, role_id):
        role = queries.role_or_404(role_id)
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data.pop("slug", None)
        updated_role = update_role(
            actor=request.user,
            role=role,
            **serializer.validated_service_data(),
        )
        return Response(RoleSerializer(updated_role).data)


class RoleHolderListView(RoleAdminView):
    """RO5: cuentas que tienen el rol vigente."""

    serializer_class = RoleHolderSerializer

    @extend_schema(responses={200: RoleHolderSerializer(many=True)})
    def get(self, request, role_id):
        role = queries.role_or_404(role_id)
        page = self.paginate_queryset(queries.role_holders(role))
        return self.get_paginated_response(RoleHolderSerializer(page, many=True).data)


class RoleDeactivateView(RoleAdminView):
    """RO6: retiro seguro del rol, con motivo."""

    serializer_class = ReasonSerializer

    @extend_schema(request=ReasonSerializer, responses={200: RoleSerializer})
    def post(self, request, role_id):
        role = queries.role_or_404(role_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = deactivate_role(
            actor=request.user, role=role, reason=serializer.validated_data["reason"]
        )
        return Response(RoleSerializer(updated).data)


class RoleReactivateView(RoleAdminView):
    serializer_class = ReasonSerializer

    @extend_schema(request=ReasonSerializer, responses={200: RoleSerializer})
    def post(self, request, role_id):
        role = queries.role_or_404(role_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = reactivate_role(
            actor=request.user, role=role, reason=serializer.validated_data["reason"]
        )
        return Response(RoleSerializer(updated).data)


# --------------------------------------------------------------------------- #
# Asignaciones de rol y alcances (RA1-RA5)
# --------------------------------------------------------------------------- #


class AccountRoleAssignmentView(RoleAdminView):
    serializer_class = RoleAssignmentWriteSerializer

    @extend_schema(responses={200: RoleAssignmentSerializer(many=True)})
    def get(self, request, account_id):
        account = queries.account_or_404(account_id)
        page = self.paginate_queryset(queries.role_assignments_for_account(account))
        return self.get_paginated_response(RoleAssignmentSerializer(page, many=True).data)

    @extend_schema(request=RoleAssignmentWriteSerializer, responses={201: RoleAssignmentSerializer})
    def post(self, request, account_id):
        account = queries.account_or_404(account_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = queries.role_or_404(serializer.validated_data.pop("role"))
        scope = serializer.validated_data.pop("scope")
        assignment = assign_role(
            actor=request.user,
            user=account,
            role=role,
            scope=scope,
            **serializer.validated_data,
        )
        created = queries.role_assignments_for_account(account).get(pk=assignment.pk)
        return Response(RoleAssignmentSerializer(created).data, status=status.HTTP_201_CREATED)


class RoleAssignmentRevokeView(RoleAdminView):
    serializer_class = RoleAssignmentSerializer

    @extend_schema(request=None, responses={200: RoleAssignmentSerializer})
    def delete(self, request, assignment_id):
        assignment = queries.role_assignment_or_404(assignment_id)
        revoked = revoke_role_assignment(actor=request.user, assignment=assignment)
        refreshed = queries.role_assignments_for_account(revoked.user).get(pk=revoked.pk)
        return Response(RoleAssignmentSerializer(refreshed).data)


class ExpiringRoleAssignmentListView(RoleAdminView):
    """RA5: asignaciones por vencer y vencidas recientemente."""

    serializer_class = RoleHolderSerializer

    @extend_schema(
        parameters=[OpenApiParameter("days", OpenApiTypes.INT)],
        responses={200: RoleHolderSerializer(many=True)},
    )
    def get(self, request):
        try:
            days = max(1, min(int(request.query_params.get("days", EXPIRING_ASSIGNMENT_DAYS)), 90))
        except (TypeError, ValueError):
            days = EXPIRING_ASSIGNMENT_DAYS
        page = self.paginate_queryset(queries.expiring_role_assignments(days=days))
        return self.get_paginated_response(RoleHolderSerializer(page, many=True).data)


# --------------------------------------------------------------------------- #
# Cuentas (U1-U9, D8)
# --------------------------------------------------------------------------- #


class AccountProvisionView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AccountProvisionSerializer

    @extend_schema(
        request=AccountProvisionSerializer,
        responses={201: ProvisionedAccountSerializer},
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account, challenge, code = provision_account_with_activation(
            actor=request.user,
            **serializer.validated_service_data(),
        )
        response = Response(
            {
                "public_id": str(account.public_id),
                "username": account.username,
                "email": account.email,
                "status": account.status,
                "status_display": account.get_status_display(),
                "person_public_id": str(account.person.public_id),
                "activation_code": code,
                "activation_expires_at": challenge.expires_at,
            },
            status=status.HTTP_201_CREATED,
        )
        return _no_store(response)


class AccountCandidateListView(GenericAPIView):
    """U1/D10: personas sin cuenta, buscables por nombre, CUI o correo."""

    permission_classes = [permissions.IsAuthenticated, ScopedAtomicPermission]
    permission_codename = ACCOUNT_CREATE_PERMISSION
    permission_scope = IDENTITY_SCOPE
    serializer_class = AccountCandidateSerializer

    @extend_schema(
        parameters=[OpenApiParameter("search", OpenApiTypes.STR)],
        responses={200: AccountCandidateSerializer(many=True)},
    )
    def get(self, request):
        page = self.paginate_queryset(
            queries.account_candidates(search=request.query_params.get("search"))
        )
        return self.get_paginated_response(AccountCandidateSerializer(page, many=True).data)


class UsernameSuggestionView(GenericAPIView):
    """U1: usuario sugerido ``nombre.apellido`` para una persona."""

    permission_classes = [permissions.IsAuthenticated, ScopedAtomicPermission]
    permission_codename = ACCOUNT_CREATE_PERMISSION
    permission_scope = IDENTITY_SCOPE
    serializer_class = UsernameSuggestionSerializer

    @extend_schema(
        parameters=[OpenApiParameter("person", OpenApiTypes.UUID, required=True)],
        responses={200: UsernameSuggestionSerializer},
    )
    def get(self, request):
        person = queries.person_or_404(request.query_params.get("person"))
        return Response({"username": suggest_username(person=person)})


class AccountListView(AccountAdminView):
    """RF-CTA-006 / U4: listado con buscador, filtros y orden."""

    serializer_class = AccountListSerializer

    def get_queryset(self):
        params = self.request.query_params
        return queries.accounts(
            status=params.get("status"),
            search=params.get("search"),
            role=params.get("role"),
            locked=True if _bool_param(params.get("locked", "")) else None,
            ordering=params.get("ordering"),
        )

    @extend_schema(
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR),
            OpenApiParameter("search", OpenApiTypes.STR),
            OpenApiParameter("role", OpenApiTypes.UUID),
            OpenApiParameter("locked", OpenApiTypes.BOOL),
            OpenApiParameter("ordering", OpenApiTypes.STR),
        ],
        responses={200: AccountListSerializer(many=True)},
    )
    def get(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(AccountListSerializer(page, many=True).data)


class AccountDetailView(AccountAdminView):
    """U5: ficha de la cuenta; U7: edicion de usuario y correo."""

    serializer_class = AccountUpdateSerializer

    def _payload(self, request, account):
        data = AccountDetailSerializer(account).data
        data["sessions"] = AccountSessionSerializer(account_sessions(user=account), many=True).data
        data["recent_activity"] = AccountActivityEventSerializer(
            audit_queries.account_activity(account_pk=account.pk), many=True
        ).data
        data["activation_expires_at"] = queries.pending_activation_expiry(account)
        return data

    @extend_schema(responses={200: AccountDetailSerializer})
    def get(self, request, account_id):
        account = queries.account_detail(account_id)
        return _no_store(Response(self._payload(request, account)))

    @extend_schema(request=AccountUpdateSerializer, responses={200: AccountDetailSerializer})
    def patch(self, request, account_id):
        account = queries.account_or_404(account_id)
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        update_account(actor=request.user, account=account, **serializer.validated_data)
        refreshed = queries.account_detail(account_id)
        return _no_store(Response(self._payload(request, refreshed)))


class ActivationChallengeReissueView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ActivationChallengeSerializer

    @extend_schema(request=None, responses={201: ActivationChallengeSerializer})
    def post(self, request, account_id):
        account = queries.account_or_404(account_id)
        challenge, code = reissue_activation_challenge(actor=request.user, account=account)
        response = Response(
            {
                "account": str(account.public_id),
                "activation_code": code,
                "activation_expires_at": challenge.expires_at,
                "max_attempts": settings.ACCOUNT_ACTIVATION_MAX_ATTEMPTS,
            },
            status=status.HTTP_201_CREATED,
        )
        return _no_store(response)


class AccountReactivateView(GenericAPIView):
    """D8: reactivar una cuenta desactivada (vuelve a pendiente con codigo nuevo)."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReasonSerializer

    @extend_schema(request=ReasonSerializer, responses={200: ReactivatedAccountSerializer})
    def post(self, request, account_id):
        account = queries.account_or_404(account_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reactivated, challenge, code = reactivate_account(
            actor=request.user, account=account, reason=serializer.validated_data["reason"]
        )
        return _no_store(
            Response(
                {
                    "account": AccountListSerializer(
                        queries.account_detail(reactivated.public_id)
                    ).data,
                    "activation_code": code,
                    "activation_expires_at": challenge.expires_at,
                }
            )
        )


class AccountUnlockView(GenericAPIView):
    """D8: levantar el bloqueo temporal por intentos fallidos."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReasonSerializer

    @extend_schema(request=ReasonSerializer, responses={200: AccountListSerializer})
    def post(self, request, account_id):
        account = queries.account_or_404(account_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        unlocked = unlock_account(
            actor=request.user, account=account, reason=serializer.validated_data["reason"]
        )
        return Response(AccountListSerializer(queries.account_detail(unlocked.public_id)).data)


class AccountDisableView(GenericAPIView):
    """RF-CTA-006: Desactivación con verificación de dependencias."""

    permission_classes = [permissions.IsAuthenticated, ScopedAtomicPermission]
    permission_codename = "account_disable"
    permission_scope = IDENTITY_SCOPE
    serializer_class = AccountDisableSerializer

    @extend_schema(request=AccountDisableSerializer, responses={200: AccountListSerializer})
    def post(self, request, account_id):
        account = queries.account_or_404(account_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = disable_account(
            actor=request.user,
            user=account,
            force=serializer.validated_data["force"],
            reason=serializer.validated_data["reason"],
        )
        if not result["disabled"]:
            return Response(result, status=status.HTTP_409_CONFLICT)
        return Response(AccountListSerializer(result["account"]).data)


class AccountSessionCloseView(GenericAPIView):
    """Account administrators can invalidate every active session of another account."""

    permission_classes = [permissions.IsAuthenticated, ScopedAtomicPermission]
    permission_codename = "account_disable"
    permission_scope = IDENTITY_SCOPE
    serializer_class = AccountListSerializer

    @extend_schema(request=None, responses={204: OpenApiResponse(description="Sesiones cerradas")})
    def post(self, request, account_id):
        account = queries.account_or_404(account_id)
        close_account_sessions(actor=request.user, user=account, administrative=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetIssueView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, ScopedAtomicPermission]
    permission_codename = "account_disable"
    permission_scope = IDENTITY_SCOPE
    serializer_class = PasswordResetIssueResultSerializer

    @extend_schema(request=None, responses={201: PasswordResetIssueResultSerializer})
    def post(self, request, account_id):
        account = queries.account_or_404(account_id)
        challenge, token = issue_password_reset(actor=request.user, account=account)
        response = Response(
            {"token": token, "expires_at": challenge.expires_at}, status=status.HTTP_201_CREATED
        )
        return _no_store(response)
