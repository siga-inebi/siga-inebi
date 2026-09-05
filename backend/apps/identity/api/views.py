from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.identity import queries
from apps.identity.api.permissions import ScopedAtomicPermission
from apps.identity.api.serializers import (
    AccountActivationSerializer,
    AccountDisableSerializer,
    AccountListSerializer,
    AccountProvisionSerializer,
    ActivatedAccountSerializer,
    ActivationChallengeSerializer,
    AtomicPermissionSerializer,
    MyClassSessionSerializer,
    ProvisionedAccountSerializer,
    PasswordResetConsumeSerializer,
    RoleAssignmentSerializer,
    RoleAssignmentWriteSerializer,
    RoleSerializer,
    RoleWriteSerializer,
)
from apps.identity.services import (
    activate_account,
    assign_role,
    close_account_sessions,
    create_role,
    disable_account,
    list_atomic_permissions,
    list_roles,
    my_weekly_schedule,
    provision_account_with_activation,
    issue_password_reset,
    consume_password_reset,
    reissue_activation_challenge,
    revoke_role_assignment,
    update_role,
)


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
        return Response(
            {
                "id": account.pk,
                "username": account.username,
                "status": account.status,
            }
        )


class AtomicPermissionListView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AtomicPermissionSerializer

    @extend_schema(responses={200: AtomicPermissionSerializer(many=True)})
    def get(self, request):
        queryset = list_atomic_permissions(actor=request.user)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


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


class RoleListCreateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, ScopedAtomicPermission]
    permission_codename = "role_assign"
    permission_scope = {"module_key": "identity"}
    serializer_class = RoleWriteSerializer

    @extend_schema(responses={200: RoleSerializer(many=True)})
    def get(self, request):
        queryset = list_roles(actor=request.user)
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(RoleSerializer(page, many=True).data)

    @extend_schema(request=RoleWriteSerializer, responses={201: RoleSerializer})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = create_role(actor=request.user, **serializer.validated_service_data())
        return Response(RoleSerializer(role).data, status=status.HTTP_201_CREATED)


class RoleDetailView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, ScopedAtomicPermission]
    permission_codename = "role_assign"
    permission_scope = {"module_key": "identity"}
    serializer_class = RoleWriteSerializer

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


class RoleAssignmentCreateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, ScopedAtomicPermission]
    permission_codename = "role_assign"
    permission_scope = {"module_key": "identity"}
    serializer_class = RoleAssignmentWriteSerializer

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
        return Response(RoleAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class RoleAssignmentRevokeView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, ScopedAtomicPermission]
    permission_codename = "role_assign"
    permission_scope = {"module_key": "identity"}
    serializer_class = RoleAssignmentSerializer

    @extend_schema(request=None, responses={200: RoleAssignmentSerializer})
    def delete(self, request, assignment_id):
        assignment = queries.role_assignment_or_404(assignment_id)
        revoked = revoke_role_assignment(actor=request.user, assignment=assignment)
        return Response(RoleAssignmentSerializer(revoked).data)


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
            **serializer.validated_data,
        )
        response = Response(
            {
                "id": account.pk,
                "username": account.username,
                "email": account.email,
                "status": account.status,
                "person": account.person_id,
                "activation_code": code,
                "activation_expires_at": challenge.expires_at,
            },
            status=status.HTTP_201_CREATED,
        )
        response["Cache-Control"] = "no-store"
        return response


class ActivationChallengeReissueView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ActivationChallengeSerializer

    @extend_schema(request=None, responses={201: ActivationChallengeSerializer})
    def post(self, request, account_id):
        account = queries.account_or_404(account_id)
        challenge, code = reissue_activation_challenge(actor=request.user, account=account)
        response = Response(
            {
                "account": account.pk,
                "activation_code": code,
                "activation_expires_at": challenge.expires_at,
                "max_attempts": settings.ACCOUNT_ACTIVATION_MAX_ATTEMPTS,
            },
            status=status.HTTP_201_CREATED,
        )
        response["Cache-Control"] = "no-store"
        return response


class AccountListView(GenericAPIView):
    """RF-CTA-006: Listado de cuentas con filtros por estado y búsqueda."""

    permission_classes = [permissions.IsAuthenticated, ScopedAtomicPermission]
    permission_codename = "account_disable"
    permission_scope = {"module_key": "identity"}
    serializer_class = AccountListSerializer

    def get_queryset(self):
        return queries.accounts(
            status=self.request.query_params.get("status"),
            search=self.request.query_params.get("search"),
        )

    @extend_schema(responses={200: AccountListSerializer(many=True)})
    def get(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(AccountListSerializer(page, many=True).data)


class AccountDisableView(GenericAPIView):
    """RF-CTA-006: Desactivación con verificación de dependencias."""

    permission_classes = [permissions.IsAuthenticated, ScopedAtomicPermission]
    permission_codename = "account_disable"
    permission_scope = {"module_key": "identity"}
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
    permission_scope = {"module_key": "identity"}
    serializer_class = AccountListSerializer

    @extend_schema(request=None, responses={204: OpenApiResponse(description="Sessions closed")})
    def post(self, request, account_id):
        account = queries.account_or_404(account_id)
        close_account_sessions(actor=request.user, user=account, administrative=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetIssueView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated, ScopedAtomicPermission]
    permission_codename = "account_disable"
    permission_scope = {"module_key": "identity"}

    def post(self, request, account_id):
        account = queries.account_or_404(account_id)
        challenge, token = issue_password_reset(actor=request.user, account=account)
        response = Response({"token": token, "expires_at": challenge.expires_at}, status=status.HTTP_201_CREATED)
        response["Cache-Control"] = "no-store"
        return response


class PasswordResetConsumeView(GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConsumeSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        consume_password_reset(token=serializer.validated_data["token"], new_password=serializer.validated_data["password"])
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response["Cache-Control"] = "no-store"
        return response
