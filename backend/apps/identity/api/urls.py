from django.urls import path

from apps.identity.api.views import AccountProvisionView, ActivationChallengeReissueView

urlpatterns = [
    path("accounts/", AccountProvisionView.as_view(), name="identity-account-provision"),
    path(
        "accounts/<int:account_id>/activation-challenges/",
        ActivationChallengeReissueView.as_view(),
        name="identity-activation-challenge-reissue",
    ),
]
