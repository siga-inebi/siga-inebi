from django.conf import settings
from django.contrib.auth.models import AbstractUser, Permission
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class UserAccount(AbstractUser):
    class AccountStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        BLOCKED = "blocked", "Blocked"
        DISABLED = "disabled", "Disabled"

    person = models.OneToOneField(
        "people.Person",
        on_delete=models.PROTECT,
        related_name="user_account",
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
        student = getattr(getattr(self, "person", None), "student_profile", None)
        if student is not None and student.status != student.StudentStatus.ACTIVE:
            return False
        return (
            RoleAssignment.objects.active_at(when)
            .filter(
                is_active=True,
                user=self,
                role__permissions__codename=codename,
            )
            .exists()
        )

    def has_scoped_permission(self, codename, *, scope=None, when=None):
        if not scope or not self.has_atomic_permission(codename, when=when):
            return False

        from apps.identity.scopes import scope_matches

        return scope_matches(user=self, codename=codename, scope=scope, when=when)


class ActivationChallenge(TimeStampedModel):
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="activation_challenges",
    )
    token_digest = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    failed_attempts = models.PositiveIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def is_usable(self, when=None):
        when = when or timezone.now()
        return bool(
            self.is_active
            and self.used_at is None
            and self.revoked_at is None
            and self.expires_at > when
            and self.failed_attempts < settings.ACCOUNT_ACTIVATION_MAX_ATTEMPTS
        )


class Role(TimeStampedModel):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    session_idle_timeout_minutes = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text="Minutos máximos de inactividad antes de cerrar la sesión.",
    )
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
    SCOPE_FIELDS = (
        "institution",
        "academic_cycle",
        "grade",
        "section",
        "subject",
        "teaching_assignment",
        "student",
        "module_key",
    )

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

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(is_active=False)
                    | models.Q(institution__isnull=False)
                    | models.Q(academic_cycle__isnull=False)
                    | models.Q(grade__isnull=False)
                    | models.Q(section__isnull=False)
                    | models.Q(subject__isnull=False)
                    | models.Q(teaching_assignment__isnull=False)
                    | models.Q(student__isnull=False)
                    | ~models.Q(module_key="")
                ),
                name="identity_scope_grant_has_dimension",
            )
        ]

    def is_active_at(self, when):
        return (
            self.is_active
            and self.starts_at <= when
            and (self.ends_at is None or self.ends_at >= when)
        )

    def has_effective_scope(self):
        return any(getattr(self, field_name) not in (None, "") for field_name in self.SCOPE_FIELDS)

    def matches(self, scope, *, when=None):
        from apps.identity.scopes import grant_matches_scope

        return grant_matches_scope(self, scope, when=when)
