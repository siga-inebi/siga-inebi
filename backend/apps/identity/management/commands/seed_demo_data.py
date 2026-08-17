import os
import secrets
from datetime import date
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from apps.academics.models import (
    AcademicCycle,
    Campus,
    CurriculumPlan,
    Grade,
    GradeOffering,
    Institution,
    Level,
    LevelSubject,
    Section,
    Shift,
    Subject,
)
from apps.identity.models import Role, RoleAssignment, ScopeGrant
from apps.people.models import Person

PERMISSIONS = [
    ("auth_login", "Can log in"),
    ("auth_logout", "Can log out"),
    ("account_create", "Can create accounts"),
    ("account_activate", "Can issue account activation challenges"),
    ("role_assign", "Can assign roles"),
    ("scope_assign", "Can assign scopes"),
    ("student_view_basic", "Can view student basic data"),
    ("student_view_sensitive", "Can view sensitive student data"),
    ("enrollment_create", "Can create enrollments"),
    ("document_read", "Can read documents"),
    ("audit_read", "Can read audit events"),
]

ROLES = {
    "system-administrator": [
        "auth_login",
        "auth_logout",
        "account_create",
        "account_activate",
        "role_assign",
        "scope_assign",
        "student_view_basic",
        "student_view_sensitive",
        "enrollment_create",
        "document_read",
        "audit_read",
    ],
    "director": ["auth_login", "auth_logout", "student_view_basic", "document_read", "audit_read"],
}

DEMO_ENV_KEYS = (
    "DEMO_ADMIN_USERNAME",
    "DEMO_ADMIN_EMAIL",
    "DEMO_ADMIN_PASSWORD",
)


def parse_env_file(path):
    values = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        values[key] = value.strip().strip("'\"")
    return values


def resolve_demo_admin_settings():
    backend_dir = Path(settings.BASE_DIR)
    repo_dir = backend_dir.parent
    values = {}

    for candidate in (
        repo_dir / ".env.example",
        backend_dir / ".env.example",
        backend_dir / ".env",
        repo_dir / ".env",
    ):
        values.update(parse_env_file(candidate))

    for key in DEMO_ENV_KEYS:
        env_value = os.environ.get(key)
        if env_value is not None:
            values[key] = env_value

    return {
        "username": values.get("DEMO_ADMIN_USERNAME", "").strip(),
        "email": values.get("DEMO_ADMIN_EMAIL", "").strip(),
        "password": values.get("DEMO_ADMIN_PASSWORD", "").strip(),
    }


class Command(BaseCommand):
    help = "Create demo institution, academic structure, roles and optional demo admin."

    def handle(self, *args, **options):
        institution, _ = Institution.objects.get_or_create(name="Instituto Demo SIGA-INEBI")
        cycle, _ = AcademicCycle.objects.get_or_create(
            institution=institution,
            year=2026,
            name="2026",
            defaults={
                "starts_on": date(2026, 1, 15),
                "ends_on": date(2026, 10, 30),
                "status": "active",
            },
        )

        has_main_campus = Campus.objects.filter(institution=institution, is_main=True).exists()
        campus, _ = Campus.objects.get_or_create(
            institution=institution,
            code="CENTRAL",
            defaults={"name": "Sede Central", "is_main": not has_main_campus},
        )
        if not Campus.objects.filter(institution=institution, is_main=True).exists():
            campus.is_main = True
            campus.save(update_fields=["is_main"])
        shifts = [
            Shift.objects.get_or_create(
                campus=campus,
                code="MOR",
                defaults={"name": "Matutina"},
            )[0],
            Shift.objects.get_or_create(
                campus=campus,
                code="VES",
                defaults={"name": "Vespertina"},
            )[0],
        ]
        level, _ = Level.objects.get_or_create(
            institution=institution,
            code="BAS",
            defaults={"name": "Basico", "sequence": 3},
        )
        grades = []
        for code, name, sequence in (
            ("B1", "Primero Basico", 1),
            ("B2", "Segundo Basico", 2),
            ("B3", "Tercero Basico", 3),
        ):
            grade = Grade.objects.filter(institution=institution, code=code).first()
            if grade is None:
                grade = Grade.objects.create(
                    level=level,
                    name=name,
                    code=code,
                    sequence=sequence,
                )
            else:
                updates = []
                if grade.level_id != level.id:
                    grade.level = level
                    updates.append("level")
                if grade.name != name:
                    grade.name = name
                    updates.append("name")
                if grade.sequence != sequence:
                    grade.sequence = sequence
                    updates.append("sequence")
                if updates:
                    grade.save(update_fields=updates)
            grades.append(grade)
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

        for subject in subjects:
            LevelSubject.objects.get_or_create(
                level=level,
                subject=subject,
                defaults={"is_required": True, "weekly_hours": 5},
            )

        for grade in grades:
            offering, _ = GradeOffering.objects.get_or_create(
                academic_cycle=cycle,
                shift=shifts[0],
                grade=grade,
            )
            for section_name in ["A", "B"]:
                Section.objects.get_or_create(
                    offering=offering,
                    name=section_name,
                    defaults={"capacity": 35},
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

        admin_settings = resolve_demo_admin_settings()
        username = admin_settings["username"]
        email = admin_settings["email"]
        password = admin_settings["password"]

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
            assignment, _ = RoleAssignment.objects.get_or_create(user=user, role=admin_role)
            ScopeGrant.objects.get_or_create(assignment=assignment, module_key="identity")
            self.stdout.write(self.style.SUCCESS(f"Demo admin ready: {username}"))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Demo admin not created. "
                    "Set DEMO_ADMIN_USERNAME or define it in .env/.env.example."
                )
            )

        self.stdout.write(self.style.SUCCESS("Demo data seed complete."))
