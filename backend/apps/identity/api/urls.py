from django.urls import path

from apps.identity.api.views import (
    AccountActivationView,
    AccountDisableView,
    AccountListView,
    AccountProvisionView,
    ActivationChallengeReissueView,
    AtomicPermissionListView,
    RoleAssignmentCreateView,
    RoleAssignmentRevokeView,
    RoleDetailView,
    RoleListCreateView,
)

urlpatterns = [
    path("permissions/", AtomicPermissionListView.as_view(), name="identity-permission-list"),
    path("roles/", RoleListCreateView.as_view(), name="identity-role-list-create"),
    path("roles/<uuid:role_id>/", RoleDetailView.as_view(), name="identity-role-detail"),
    path(
        "accounts/<int:account_id>/role-assignments/",
        RoleAssignmentCreateView.as_view(),
        name="identity-role-assignment-create",
    ),
    path(
        "role-assignments/<uuid:assignment_id>/",
        RoleAssignmentRevokeView.as_view(),
        name="identity-role-assignment-revoke",
    ),
    path("accounts/", AccountProvisionView.as_view(), name="identity-account-provision"),
    path("accounts/list/", AccountListView.as_view(), name="identity-account-list"),
    path("accounts/activate/", AccountActivationView.as_view(), name="identity-account-activate"),
    path(
        "accounts/<int:account_id>/activation-challenges/",
        ActivationChallengeReissueView.as_view(),
        name="identity-activation-challenge-reissue",
    ),
    path(
        "accounts/<int:account_id>/disable/",
        AccountDisableView.as_view(),
        name="identity-account-disable",
    ),
]
