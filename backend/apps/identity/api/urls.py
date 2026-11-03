from django.urls import path

from apps.identity.api.views import (
    AccountActivationView,
    AccountCandidateListView,
    AccountDetailView,
    AccountDisableView,
    AccountListView,
    AccountProvisionView,
    AccountReactivateView,
    AccountRoleAssignmentView,
    AccountSessionCloseView,
    AccountSingleSessionCloseView,
    AccountUnlockView,
    ActivationChallengeReissueView,
    AtomicPermissionListView,
    ExpiringRoleAssignmentListView,
    MyAccountView,
    MySessionCloseView,
    MyWeeklyScheduleView,
    PasswordPolicyView,
    PasswordResetConsumeView,
    PasswordResetIssueView,
    PermissionHolderListView,
    RoleAssignmentRevokeView,
    RoleDeactivateView,
    RoleDetailView,
    RoleHolderListView,
    RoleListCreateView,
    RoleReactivateView,
    ScopeOptionsView,
    UsernameSuggestionView,
)

# Las cuentas se direccionan por `public_id` (UUID). El id entero interno dejo
# de ser parte del contrato publico (ADR-0011, docs/architecture/api-conventions.md).
urlpatterns = [
    path("permissions/", AtomicPermissionListView.as_view(), name="identity-permission-list"),
    path(
        "permissions/<str:code>/holders/",
        PermissionHolderListView.as_view(),
        name="identity-permission-holders",
    ),
    path("password-policy/", PasswordPolicyView.as_view(), name="identity-password-policy"),
    path("scope-options/", ScopeOptionsView.as_view(), name="identity-scope-options"),
    path("me/schedule/", MyWeeklyScheduleView.as_view(), name="identity-my-schedule"),
    path("me/account/", MyAccountView.as_view(), name="identity-my-account"),
    path(
        "me/sessions/<uuid:session_id>/close/",
        MySessionCloseView.as_view(),
        name="identity-my-session-close",
    ),
    path("roles/", RoleListCreateView.as_view(), name="identity-role-list-create"),
    path("roles/<uuid:role_id>/", RoleDetailView.as_view(), name="identity-role-detail"),
    path(
        "roles/<uuid:role_id>/holders/",
        RoleHolderListView.as_view(),
        name="identity-role-holders",
    ),
    path(
        "roles/<uuid:role_id>/deactivate/",
        RoleDeactivateView.as_view(),
        name="identity-role-deactivate",
    ),
    path(
        "roles/<uuid:role_id>/reactivate/",
        RoleReactivateView.as_view(),
        name="identity-role-reactivate",
    ),
    path(
        "role-assignments/expiring/",
        ExpiringRoleAssignmentListView.as_view(),
        name="identity-role-assignment-expiring",
    ),
    path(
        "role-assignments/<uuid:assignment_id>/",
        RoleAssignmentRevokeView.as_view(),
        name="identity-role-assignment-revoke",
    ),
    path("accounts/", AccountProvisionView.as_view(), name="identity-account-provision"),
    path("accounts/list/", AccountListView.as_view(), name="identity-account-list"),
    path(
        "accounts/candidates/",
        AccountCandidateListView.as_view(),
        name="identity-account-candidates",
    ),
    path(
        "accounts/username-suggestion/",
        UsernameSuggestionView.as_view(),
        name="identity-username-suggestion",
    ),
    path("accounts/activate/", AccountActivationView.as_view(), name="identity-account-activate"),
    path(
        "accounts/<uuid:account_id>/",
        AccountDetailView.as_view(),
        name="identity-account-detail",
    ),
    path(
        "accounts/<uuid:account_id>/role-assignments/",
        AccountRoleAssignmentView.as_view(),
        name="identity-role-assignment-create",
    ),
    path(
        "accounts/<uuid:account_id>/activation-challenges/",
        ActivationChallengeReissueView.as_view(),
        name="identity-activation-challenge-reissue",
    ),
    path(
        "accounts/<uuid:account_id>/reactivate/",
        AccountReactivateView.as_view(),
        name="identity-account-reactivate",
    ),
    path(
        "accounts/<uuid:account_id>/unlock/",
        AccountUnlockView.as_view(),
        name="identity-account-unlock",
    ),
    path(
        "accounts/<uuid:account_id>/disable/",
        AccountDisableView.as_view(),
        name="identity-account-disable",
    ),
    path(
        "accounts/<uuid:account_id>/sessions/close/",
        AccountSessionCloseView.as_view(),
        name="identity-account-sessions-close",
    ),
    path(
        "accounts/<uuid:account_id>/sessions/<uuid:session_id>/close/",
        AccountSingleSessionCloseView.as_view(),
        name="identity-account-session-close",
    ),
    path(
        "accounts/<uuid:account_id>/password-resets/",
        PasswordResetIssueView.as_view(),
        name="identity-password-reset-issue",
    ),
    path(
        "password-resets/consume/",
        PasswordResetConsumeView.as_view(),
        name="identity-password-reset-consume",
    ),
]
