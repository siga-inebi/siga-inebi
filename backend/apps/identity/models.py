from django.conf import settings
from django.contrib.auth.models import AbstractUser, Permission
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class UserAccount(AbstractUser):
    class AccountStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        BLOCKED = "blocked", "Blocked"
        DISABLED = "disabled", "Disabled"

    person = models.OneToOneField(
        "people.Person",
        on_delete=models.PROTECT,
        related_name="user_account",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
    )
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())

    def has_atomic_permission(self, codename, when=None):
        when = when or timezone.now()
        if not self.is_active or self.status != self.AccountStatus.ACTIVE or self.is_locked():
            return False

        return (
            RoleAssignment.objects.active_at(when)
            .filter(
                user=self,
                role__permissions__codename=codename,
            )
            .exists()
        )


class Role(TimeStampedModel):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    permissions = models.ManyToManyField(Permission, blank=True, related_name="siga_roles")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class RoleAssignmentQuerySet(models.QuerySet):
    def active_at(self, when):
        return self.filter(
            starts_at__lte=when,
        ).filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=when))


class RoleAssignment(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="assignments")
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)

    objects = RoleAssignmentQuerySet.as_manager()

    class Meta:
        unique_together = [("user", "role", "starts_at")]


class ScopeGrant(TimeStampedModel):
    assignment = models.ForeignKey(
        RoleAssignment,
        on_delete=models.CASCADE,
        related_name="scope_grants",
    )
    institution = models.ForeignKey(
        "academics.Institution",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    academic_cycle = models.ForeignKey(
        "academics.AcademicCycle",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    grade = models.ForeignKey("academics.Grade", null=True, blank=True, on_delete=models.CASCADE)
    section = models.ForeignKey(
        "academics.Section", null=True, blank=True, on_delete=models.CASCADE
    )
    subject = models.ForeignKey(
        "academics.Subject", null=True, blank=True, on_delete=models.CASCADE
    )
    teaching_assignment = models.ForeignKey(
        "academics.TeachingAssignment",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    student = models.ForeignKey("students.Student", null=True, blank=True, on_delete=models.CASCADE)
    module_key = models.CharField(max_length=100, blank=True)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
