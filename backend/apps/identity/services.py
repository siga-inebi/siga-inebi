from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.audit.services import record_event
from apps.common.models import DomainError
from apps.identity.models import RoleAssignment, ScopeGrant


def assign_role(
    *,
    actor,
    user,
    role,
    starts_at=None,
    ends_at=None,
    scope=None,
):
    if actor and actor.pk == user.pk:
        raise PermissionDenied("Users cannot assign roles to themselves.")
    if actor and not (actor.is_superuser or actor.has_atomic_permission("role_assign")):
        raise PermissionDenied("Actor lacks permission to assign roles.")

    assignment, created = RoleAssignment.objects.get_or_create(
        user=user,
        role=role,
        starts_at=starts_at or timezone.now(),
        defaults={"ends_at": ends_at},
    )
    if not created and ends_at != assignment.ends_at:
        assignment.ends_at = ends_at
        assignment.save(update_fields=["ends_at", "updated_at"])

    if scope:
        ScopeGrant.objects.get_or_create(
            assignment=assignment,
            starts_at=scope.get("starts_at") or timezone.now(),
            defaults={
                "ends_at": scope.get("ends_at"),
                "institution": scope.get("institution"),
                "academic_cycle": scope.get("academic_cycle"),
                "grade": scope.get("grade"),
                "section": scope.get("section"),
                "subject": scope.get("subject"),
                "teaching_assignment": scope.get("teaching_assignment"),
                "student": scope.get("student"),
                "module_key": scope.get("module_key", ""),
            },
        )

    record_event(
        actor=actor,
        action="identity.role_assignment.created",
        resource="RoleAssignment",
        resource_identifier=str(assignment.pk),
        context={
            "target_user_id": user.pk,
            "role_slug": role.slug,
        },
    )
    return assignment


def protect_system_role(*, actor, role):
    if role.is_system and not getattr(actor, "is_superuser", False):
        raise DomainError("System roles require elevated authorization.")
    return role
