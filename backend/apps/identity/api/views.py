from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.identity.api.serializers import (
    AccountActivationSerializer,
    AccountProvisionSerializer,
    ActivatedAccountSerializer,
    ActivationChallengeSerializer,
    AtomicPermissionSerializer,
    ProvisionedAccountSerializer,
    RoleAssignmentSerializer,
    RoleAssignmentWriteSerializer,
    RoleSerializer,
    RoleWriteSerializer,
)
from apps.identity.models import Role, RoleAssignment
from apps.identity.services import (
    activate_account,
    assign_role,
    create_role,
    list_atomic_permissions,
    list_roles,
    provision_account_with_activation,
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
        return Response({"id": account.pk, "username": account.username, "status": account.status})


class AtomicPermissionListView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AtomicPermissionSerializer

    @extend_schema(responses={200: AtomicPermissionSerializer(many=True)})
    def get(self, request):
        queryset = list_atomic_permissions(actor=request.user)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class RoleListCreateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
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
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RoleWriteSerializer

    @extend_schema(request=RoleWriteSerializer, responses={200: RoleSerializer})
    def patch(self, request, role_id):
        role = get_object_or_404(Role, public_id=role_id)
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
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RoleAssignmentWriteSerializer

    @extend_schema(request=RoleAssignmentWriteSerializer, responses={201: RoleAssignmentSerializer})
    def post(self, request, account_id):
        account = get_object_or_404(get_user_model(), pk=account_id)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = get_object_or_404(Role, public_id=serializer.validated_data.pop("role"))
        assignment = assign_role(
            actor=request.user,
            user=account,
            role=role,
            **serializer.validated_data,
        )
        return Response(RoleAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class RoleAssignmentRevokeView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RoleAssignmentSerializer

    @extend_schema(request=None, responses={200: RoleAssignmentSerializer})
    def delete(self, request, assignment_id):
        assignment = get_object_or_404(
            RoleAssignment.objects.select_related("role"),
            public_id=assignment_id,
        )
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
        account = get_object_or_404(get_user_model(), pk=account_id)
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
