import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError

from apps.identity.atomic_permissions import ATOMIC_PERMISSIONS, permission_codename
from apps.identity.models import Role, RoleAssignment, ScopeGrant
from apps.people.models import Person


class Command(BaseCommand):
    help = (
        "Create the initial institutional superuser (person, account and "
        "system-administrator role). Production bootstrap only; no demo data."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", default=os.environ.get("DJANGO_SUPERUSER_USERNAME", ""))
        parser.add_argument("--email", default=os.environ.get("DJANGO_SUPERUSER_EMAIL", ""))
        parser.add_argument("--password", default=os.environ.get("DJANGO_SUPERUSER_PASSWORD", ""))
        parser.add_argument(
            "--first-name", default=os.environ.get("ADMIN_FIRST_NAME", "Administrador")
        )
        parser.add_argument(
            "--last-name", default=os.environ.get("ADMIN_LAST_NAME", "Institucional")
        )

    def handle(self, *args, **options):
        username = options["username"].strip()
        email = options["email"].strip()
        password = options["password"]
        if not username or not email or not password:
            raise CommandError(
                "username, email y password son obligatorios (argumentos o "
                "DJANGO_SUPERUSER_USERNAME/DJANGO_SUPERUSER_EMAIL/DJANGO_SUPERUSER_PASSWORD)."
            )

        # El catalogo atomico lo siembran las migraciones de identity; el rol se
        # deriva de el para que el admin nunca diverja de las vistas (mismo
        # criterio que seed_demo_data: un permiso ausente deja la funcion en 403).
        role_content_type = ContentType.objects.get_for_model(Role)
        permission_map = {}
        for code, label in ATOMIC_PERMISSIONS:
            codename = permission_codename(code)
            permission_map[codename], _ = Permission.objects.get_or_create(
                codename=codename,
                content_type=role_content_type,
                defaults={"name": label},
            )
        role, _ = Role.objects.get_or_create(
            slug="system-administrator",
            defaults={"name": "System Administrator", "is_system": True},
        )
        role.permissions.set(permission_map.values())

        person, _ = Person.objects.get_or_create(
            email=email,
            defaults={
                "first_name": options["first_name"].strip(),
                "last_name": options["last_name"].strip(),
            },
        )
        user_model = get_user_model()
        user, _ = user_model.objects.get_or_create(
            username=username,
            defaults={"person": person},
        )
        # Idempotente a proposito: reejecutar el job con un secreto rotado
        # restablece la clave sin borrar la cuenta ni su historial auditable.
        user.email = email
        user.person = person
        user.is_staff = True
        user.is_superuser = True
        user.status = user_model.AccountStatus.ACTIVE
        user.set_password(password)
        user.save()

        assignment, _ = RoleAssignment.objects.get_or_create(user=user, role=role)
        for module_key in ("identity", "students", "teachers"):
            ScopeGrant.objects.get_or_create(assignment=assignment, module_key=module_key)

        self.stdout.write(self.style.SUCCESS(f"Initial admin ready: {username} <{email}>"))
