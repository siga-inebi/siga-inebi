from django.urls import path

from apps.identity.api.views import (
    AccountActivationView,
    AccountProvisionView,
    ActivationChallengeReissueView,
    AtomicPermissionListView,
)

urlpatterns = [
    path("permissions/", AtomicPermissionListView.as_view(), name="identity-permission-list"),
    path("accounts/", AccountProvisionView.as_view(), name="identity-account-provision"),
    path("accounts/activate/", AccountActivationView.as_view(), name="identity-account-activate"),
    path(
        "accounts/<int:account_id>/activation-challenges/",
        ActivationChallengeReissueView.as_view(),
        name="identity-activation-challenge-reissue",
    ),
]
