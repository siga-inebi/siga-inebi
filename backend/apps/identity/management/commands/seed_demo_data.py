import os
import secrets
from datetime import date, time
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
    TeachingAssignment,
)
from apps.attendance.models import JornadaParameters
from apps.enrolments.models import Enrolment
from apps.evaluation.models import EvaluationUnit
from apps.identity.models import Role, RoleAssignment, ScopeGrant
from apps.people.models import Person
from apps.students.models import Guardian, Student, StudentGuardianRelation
from apps.teachers.models import Teacher

# Un permiso por cada operacion que alguna vista exige. La lista se quedaba
# corta en asistencia, alertas y documentos, y el resultado era un demo donde
# modulos enteros respondian 403 sin que nada explicara por que: el
# administrador no puede ser el rol que no alcanza a administrar.
PERMISSIONS = [
    ("auth_login", "Can log in"),
    ("auth_logout", "Can log out"),
    ("account_create", "Can create accounts"),
    ("account_activate", "Can issue account activation challenges"),
    ("account_disable", "Can disable accounts"),
    ("role_assign", "Can assign roles"),
    ("scope_assign", "Can assign scopes"),
    ("student_view_basic", "Can view student basic data"),
    ("student_edit_basic", "Can edit student basic data"),
    ("student_view_sensitive", "Can view sensitive student data"),
    ("enrollment_create", "Can create enrollments"),
    ("enrollment_update", "Can update enrollments"),
    ("attendance_jornada_configure", "Can configure jornada parameters"),
    ("attendance_record_manual", "Can record attendance manually"),
    ("attendance_scan", "Can record attendance by scan"),
    ("attendance_declared_close", "Can close a jornada with declared attendance"),
    ("grade_write", "Can register grades"),
    ("reporting_alert_view", "Can view attendance alerts"),
    ("reporting_alert_acknowledge", "Can acknowledge attendance alerts"),
    ("reporting_alert_evaluate", "Can re-evaluate attendance alerts"),
    ("reporting_absence_threshold_configure", "Can configure absence thresholds"),
    ("document_read", "Can read documents"),
    ("document_issue", "Can issue official documents"),
    ("audit_read", "Can read audit events"),
]

# El administrador del sistema recibe TODO lo publicado; el director, lo que
# necesita para consultar y atender, sin configurar ni emitir.
ROLES = {
    "system-administrator": [codename for codename, _label in PERMISSIONS],
    "director": [
        "auth_login",
        "auth_logout",
        "student_view_basic",
        "student_view_sensitive",
        "reporting_alert_view",
        "reporting_alert_acknowledge",
        "document_read",
        "audit_read",
    ],
}

# Catalogos del demo. Son listas fijas y no nombres aleatorios: un seeder que
# cambia de datos en cada corrida vuelve irreproducible cualquier captura de
# pantalla, cualquier reporte de error y cualquier prueba manual.

SUBJECTS = [
    ("MAT", "Matematica"),
    ("COM", "Comunicacion y Lenguaje"),
    ("SCI", "Ciencias Naturales"),
    ("SOC", "Ciencias Sociales"),
    ("ING", "Idioma Extranjero"),
    ("EFI", "Educacion Fisica"),
    ("FCI", "Formacion Ciudadana"),
    ("PRO", "Productividad y Desarrollo"),
]

TEACHER_NAMES = [
    ("Allende Baudilio", "Bautista Godinez", "Matematica"),
    ("Marta Elena", "Xicara Tzunun", "Comunicacion y Lenguaje"),
    ("Julio Cesar", "Chavez Morales", "Ciencias Naturales"),
    ("Ana Lucia", "Ixcot Perez", "Ciencias Sociales"),
    ("Byron Estuardo", "Sarat Lopez", "Idioma Extranjero"),
    ("Silvia Maribel", "Coyoy Ajanel", "Educacion Fisica"),
    ("Otto Rene", "Tzoc Batz", "Formacion Ciudadana"),
    ("Claudia Veronica", "Alvarado Ruiz", "Productividad"),
    ("Mario Antonio", "Cifuentes Sam", "Matematica"),
    ("Delfina", "Yac Tambriz", "Comunicacion y Lenguaje"),
    ("Hector Manuel", "Rodas Barrios", "Ciencias Naturales"),
    ("Lucrecia", "Menchu Argueta", "Ciencias Sociales"),
]

STUDENT_FIRST_NAMES = [
    "Ana", "Luis", "Sofia", "Diego", "Camila", "Andres", "Valeria", "Jose",
    "Fernanda", "Carlos", "Maria", "Pablo", "Daniela", "Miguel", "Gabriela",
    "Rodrigo", "Isabel", "Javier", "Alejandra", "Emilio",
]

STUDENT_LAST_NAMES = [
    "Perez Lopez", "Garcia Tzul", "Morales Xiloj", "Ramirez Chan",
    "Hernandez Cua", "Lopez Batz", "Gonzalez Say", "Vasquez Tuy",
    "Sanchez Ixcoy", "Diaz Puac", "Torres Mejia", "Flores Us",
    "Rivera Chach", "Gomez Tzunun", "Castillo Yax",
]

GUARDIAN_RELATIONSHIPS = ["Madre", "Padre", "Abuela", "Tio"]

# Estudiantes que quedan con expediente pero sin matricula, para que la
# matriculacion por lotes tenga a quien matricular.
UNENROLLED_STUDENTS = 15

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
                code=code,
                defaults={"name": name},
            )[0]
            for code, name in SUBJECTS
        ]

        for subject in subjects:
            LevelSubject.objects.get_or_create(
                level=level,
                subject=subject,
                defaults={"is_required": True, "weekly_hours": 5},
            )

        # Secciones en las dos jornadas. La vespertina no es adorno: sin ella no
        # se puede probar que un selector de secciones distinga "Primero Basico A"
        # matutina de la vespertina, que es justo donde una interfaz se equivoca.
        sections = []
        for grade in grades:
            for shift in shifts:
                offering, _ = GradeOffering.objects.get_or_create(
                    academic_cycle=cycle,
                    shift=shift,
                    grade=grade,
                )
                section_names = ["A", "B"] if shift.code == "MOR" else ["A"]
                for section_name in section_names:
                    section, _ = Section.objects.get_or_create(
                        offering=offering,
                        name=section_name,
                        defaults={"capacity": 35},
                    )
                    sections.append(section)
            for subject in subjects:
                CurriculumPlan.objects.get_or_create(
                    academic_cycle=cycle,
                    grade=grade,
                    subject=subject,
                )

        teachers = self.seed_teachers()
        students = self.seed_students()
        self.seed_guardians(students)
        self.seed_enrolments(cycle=cycle, sections=sections, students=students)
        self.seed_teaching_assignments(
            cycle=cycle, sections=sections, subjects=subjects, teachers=teachers
        )
        self.seed_evaluation_units(cycle)
        self.seed_jornada_parameters(cycle=cycle, shifts=shifts)

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
            # Sin el alcance del modulo de estudiantes el administrador no puede
            # dar de alta a nadie, ni ver a quien todavia no tiene matricula.
            ScopeGrant.objects.get_or_create(assignment=assignment, module_key="students")
            ScopeGrant.objects.get_or_create(assignment=assignment, institution=institution)
            self.stdout.write(self.style.SUCCESS(f"Demo admin ready: {username}"))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Demo admin not created. "
                    "Set DEMO_ADMIN_USERNAME or define it in .env/.env.example."
                )
            )

        self.stdout.write(self.style.SUCCESS("Demo data seed complete."))

    # ----------------------------------------------------------------- #
    # Poblacion del demo
    #
    # Todo se crea con get_or_create sobre una clave estable (codigo de
    # empleado, codigo de estudiante, numero de unidad): correr el seeder dos
    # veces no debe duplicar nada, porque `make seed` se corre a mano y sin
    # llevar la cuenta de cuantas veces.
    # ----------------------------------------------------------------- #

    def seed_teachers(self):
        teachers = []
        for index, (first_name, last_name, specialty) in enumerate(TEACHER_NAMES, start=1):
            employee_code = f"DOC-{index:03d}"
            teacher = Teacher.objects.filter(employee_code=employee_code).first()
            if teacher is None:
                person = Person.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    email=f"docente{index:03d}@inebi.edu.gt",
                    phone_number=f"5{index:07d}",
                )
                teacher = Teacher.objects.create(
                    person=person,
                    employee_code=employee_code,
                    specialty=specialty,
                    position=Teacher.Position.DOCENTE_TITULADO,
                    appointment_date=date(2026, 1, 15),
                )
            teachers.append(teacher)

        self.stdout.write(f"Docentes: {len(teachers)}")
        return teachers

    def seed_students(self):
        students = []
        total = len(STUDENT_FIRST_NAMES) * 5

        for index in range(total):
            student_code = f"EST-2026-{index + 1:04d}"
            student = Student.objects.filter(student_code=student_code).first()
            if student is None:
                first_name = STUDENT_FIRST_NAMES[index % len(STUDENT_FIRST_NAMES)]
                last_name = STUDENT_LAST_NAMES[index % len(STUDENT_LAST_NAMES)]
                person = Person.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    email=f"estudiante{index + 1:04d}@inebi.edu.gt",
                    phone_number=f"4{index + 1:07d}",
                )
                student = Student.objects.create(
                    person=person,
                    student_code=student_code,
                    status=Student.StudentStatus.ACTIVE,
                )
            students.append(student)

        self.stdout.write(f"Estudiantes: {len(students)}")
        return students

    def seed_guardians(self, students):
        """Un encargado cada tres estudiantes, para tener casos con y sin vinculo."""
        created = 0
        for index, student in enumerate(students):
            if index % 3 != 0:
                continue
            if StudentGuardianRelation.objects.filter(student=student).exists():
                continue

            person = Person.objects.create(
                first_name=STUDENT_FIRST_NAMES[(index + 7) % len(STUDENT_FIRST_NAMES)],
                last_name=student.person.last_name,
                email=f"encargado{index + 1:04d}@inebi.edu.gt",
                phone_number=f"3{index + 1:07d}",
            )
            guardian = Guardian.objects.create(person=person)
            StudentGuardianRelation.objects.create(
                student=student,
                guardian=guardian,
                relationship_label=GUARDIAN_RELATIONSHIPS[index % len(GUARDIAN_RELATIONSHIPS)],
                is_primary=True,
                starts_at=date(2026, 1, 15),
            )
            created += 1

        self.stdout.write(f"Encargados: {created}")

    def seed_enrolments(self, *, cycle, sections, students):
        """
        Reparte los estudiantes entre las secciones sin pasar del cupo.

        Deja a proposito a los ultimos quince SIN matricula: es el estado real
        de un ciclo que arranca (hay expediente, todavia no hay seccion) y es lo
        que la matriculacion por lotes existe para resolver. Sin ese resto, la
        pantalla solo se puede probar borrando datos a mano.

        No usa el servicio de matriculacion a proposito: ese valida cupo y
        jornada consultando la base por cada alta, y aqui interesa dejar el
        estado final, no simular el tramite.
        """
        created = 0
        students = students[:-UNENROLLED_STUDENTS] if len(students) > UNENROLLED_STUDENTS else students
        capacity_left = {
            section.pk: section.capacity - section.enrolments.filter(status="active").count()
            for section in sections
        }

        pending = [
            student
            for student in students
            if not Enrolment.objects.filter(
                student=student, academic_cycle=cycle, status="active"
            ).exists()
        ]

        for student in pending:
            section = next(
                (section for section in sections if capacity_left[section.pk] > 0),
                None,
            )
            if section is None:
                break

            Enrolment.objects.create(
                student=student,
                academic_cycle=cycle,
                grade=section.grade,
                section=section,
                effective_on=cycle.starts_on,
            )
            capacity_left[section.pk] -= 1
            created += 1

        self.stdout.write(f"Matriculas: {created}")

    def seed_teaching_assignments(self, *, cycle, sections, subjects, teachers):
        """
        Un docente por seccion y curso, repartidos en rueda.

        Deja a proposito la ultima seccion SIN asignaciones: es el caso que la
        pantalla de asignacion por lotes existe para resolver, y sin un hueco
        real no hay como probarla.
        """
        created = 0
        assignable = sections[:-1] if len(sections) > 1 else sections

        for section_index, section in enumerate(assignable):
            for subject_index, subject in enumerate(subjects):
                if TeachingAssignment.objects.filter(
                    academic_cycle=cycle,
                    section=section,
                    subject=subject,
                    ends_on__isnull=True,
                ).exists():
                    continue

                teacher = teachers[
                    (section_index * len(subjects) + subject_index) % len(teachers)
                ]
                TeachingAssignment.objects.create(
                    academic_cycle=cycle,
                    section=section,
                    subject=subject,
                    teacher=teacher.person,
                    starts_on=cycle.starts_on,
                )
                created += 1

        self.stdout.write(f"Asignaciones docentes: {created}")

    def seed_evaluation_units(self, cycle):
        units = [
            (1, "Primera unidad", date(2026, 1, 15), date(2026, 3, 31)),
            (2, "Segunda unidad", date(2026, 4, 1), date(2026, 6, 15)),
            (3, "Tercera unidad", date(2026, 6, 16), date(2026, 8, 31)),
            (4, "Cuarta unidad", date(2026, 9, 1), date(2026, 10, 30)),
        ]

        for number, name, starts_on, ends_on in units:
            EvaluationUnit.objects.get_or_create(
                academic_cycle=cycle,
                number=number,
                defaults={
                    "name": name,
                    "starts_on": starts_on,
                    "ends_on": ends_on,
                    # La ventana de captura se abre con la unidad y cierra dos
                    # semanas despues: asi la unidad en curso admite notas y las
                    # anteriores no, que es el estado normal de un ciclo vivo.
                    "capture_starts_on": starts_on,
                    "capture_ends_on": ends_on,
                    "status": EvaluationUnit.UnitStatus.OPEN,
                },
            )

        self.stdout.write(f"Unidades de evaluacion: {len(units)}")

    def seed_jornada_parameters(self, *, cycle, shifts):
        schedules = {
            "MOR": (time(7, 30), time(12, 30)),
            "VES": (time(13, 0), time(18, 0)),
        }

        for shift in shifts:
            entry_limit, closing = schedules.get(shift.code, (time(7, 30), time(12, 30)))
            JornadaParameters.objects.get_or_create(
                shift=shift,
                academic_cycle=cycle,
                effective_from=cycle.starts_on,
                defaults={
                    "entry_limit_time": entry_limit,
                    "tolerance_minutes": 10,
                    "closing_time": closing,
                    "duplicate_suppression_minutes": 5,
                    "school_days": ["mon", "tue", "wed", "thu", "fri"],
                },
            )

        self.stdout.write(f"Parametros de jornada: {len(shifts)}")

