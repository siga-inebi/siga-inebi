from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.identity.models import Role, RoleAssignment, ScopeGrant, UserAccount


@admin.register(UserAccount)
class UserAccountAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("SIGA", {"fields": ("person", "status", "failed_login_attempts", "locked_until")}),
    )


admin.site.register(Role)
admin.site.register(RoleAssignment)
admin.site.register(ScopeGrant)
