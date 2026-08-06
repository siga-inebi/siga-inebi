from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.identity.api.serializers import (
    AccountProvisionSerializer,
    ActivationChallengeSerializer,
    ProvisionedAccountSerializer,
)
from apps.identity.services import (
    provision_account_with_activation,
    reissue_activation_challenge,
)


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
