import os
import secrets
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from apps.academics.models import (
    AcademicCycle,
    CurriculumPlan,
    Grade,
    Institution,
    Section,
    Shift,
    Subject,
)
from apps.identity.models import Role, RoleAssignment
from apps.people.models import Person

PERMISSIONS = [
    ("auth_login", "Can log in"),
    ("auth_logout", "Can log out"),
    ("account_create", "Can create accounts"),
    ("role_assign", "Can assign roles"),
    ("scope_assign", "Can assign scopes"),
    ("student_view_basic", "Can view student basic data"),
    ("student_view_sensitive", "Can view sensitive student data"),
    ("enrolment_create", "Can create enrolments"),
    ("document_read", "Can read documents"),
    ("audit_read", "Can read audit events"),
]

ROLES = {
    "system-administrator": [
        "auth_login",
        "auth_logout",
        "account_create",
        "role_assign",
        "scope_assign",
        "student_view_basic",
        "student_view_sensitive",
        "enrolment_create",
        "document_read",
        "audit_read",
    ],
    "director": ["auth_login", "auth_logout", "student_view_basic", "document_read", "audit_read"],
}


class Command(BaseCommand):
    help = "Create demo institution, academic structure, roles and optional demo admin."

    def handle(self, *args, **options):
        institution, _ = Institution.objects.get_or_create(name="Instituto Demo SIGA-INEBI")
        cycle, _ = AcademicCycle.objects.get_or_create(
            institution=institution,
            name="2026",
            defaults={
                "starts_on": date(2026, 1, 15),
                "ends_on": date(2026, 10, 30),
                "status": "active",
            },
        )

        shifts = [
            Shift.objects.get_or_create(
                institution=institution,
                code="MOR",
                defaults={"name": "Matutina"},
            )[0],
            Shift.objects.get_or_create(
                institution=institution,
                code="VES",
                defaults={"name": "Vespertina"},
            )[0],
        ]
        grades = [
            Grade.objects.get_or_create(
                institution=institution,
                code="B1",
                defaults={"name": "Basico 1"},
            )[0],
            Grade.objects.get_or_create(
                institution=institution,
                code="B2",
                defaults={"name": "Basico 2"},
            )[0],
            Grade.objects.get_or_create(
                institution=institution,
                code="B3",
                defaults={"name": "Basico 3"},
            )[0],
        ]
        subjects = [
            Subject.objects.get_or_create(
                institution=institution,
                code="MAT",
                defaults={"name": "Matematica"},
            )[0],
            Subject.objects.get_or_create(
                institution=institution,
                code="COM",
                defaults={"name": "Comunicacion y Lenguaje"},
            )[0],
            Subject.objects.get_or_create(
                institution=institution,
                code="SCI",
                defaults={"name": "Ciencias Naturales"},
            )[0],
        ]

        for grade in grades:
            for section_name in ["A", "B"]:
                Section.objects.get_or_create(
                    academic_cycle=cycle,
                    grade=grade,
                    name=section_name,
                    defaults={"shift": shifts[0], "capacity": 35},
                )
            for subject in subjects:
                CurriculumPlan.objects.get_or_create(
                    academic_cycle=cycle,
                    grade=grade,
                    subject=subject,
                )

        role_content_type = ContentType.objects.get_for_model(Role)
        permission_map = {}
        for codename, label in PERMISSIONS:
            permission_map[codename], _ = Permission.objects.get_or_create(
                codename=codename,
                content_type=role_content_type,
                defaults={"name": label},
            )

        for slug, codenames in ROLES.items():
            role, _ = Role.objects.get_or_create(
                slug=slug,
                defaults={"name": slug.replace("-", " ").title(), "is_system": True},
            )
            role.permissions.set([permission_map[codename] for codename in codenames])

        username = os.environ.get("DEMO_ADMIN_USERNAME", "").strip()
        email = os.environ.get("DEMO_ADMIN_EMAIL", "").strip()
        password = os.environ.get("DEMO_ADMIN_PASSWORD", "").strip()

        if username:
            person, _ = Person.objects.get_or_create(
                email=email or f"{username}@example.invalid",
                defaults={"first_name": "Demo", "last_name": "Admin"},
            )
            user_model = get_user_model()
            user, created = user_model.objects.get_or_create(
                username=username,
                defaults={
                    "email": email,
                    "person": person,
                    "status": user_model.AccountStatus.ACTIVE,
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
            if user.person_id != person.id:
                user.person = person
            if email and user.email != email:
                user.email = email
            if user.status != user_model.AccountStatus.ACTIVE:
                user.status = user_model.AccountStatus.ACTIVE
            if not user.is_staff:
                user.is_staff = True
            if not user.is_superuser:
                user.is_superuser = True

            generated_password = None
            if created and not password:
                generated_password = secrets.token_urlsafe(16)
                password = generated_password

            if password:
                user.set_password(password)

            user.save()

            if generated_password:
                self.stdout.write(
                    self.style.WARNING(
                        "DEMO_ADMIN_PASSWORD not provided. Generated password shown once:"
                    )
                )
                self.stdout.write(generated_password)
            admin_role = Role.objects.get(slug="system-administrator")
            RoleAssignment.objects.get_or_create(user=user, role=admin_role)

        self.stdout.write(self.style.SUCCESS("Demo data seed complete."))
