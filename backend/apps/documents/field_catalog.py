"""
Closed catalogue of dynamic field tags document templates may reference
(RF-PLA-002).

Fixed in code, like ``apps.identity.atomic_permissions.ATOMIC_PERMISSIONS`` --
not an admin-editable table. Grounded in fields that already exist on
``apps.people.Person``, ``apps.students.Student``,
``apps.academics.{Institution,AcademicCycle,Section}`` and
``apps.enrolments.Enrolment``.
"""

FIELD_TAGS = (
    ("student.full_name", "Nombre completo del estudiante"),
    ("student.code", "Codigo del estudiante"),
    ("institution.name", "Nombre de la institucion"),
    ("institution.short_name", "Nombre corto de la institucion"),
    ("academic.cycle_name", "Nombre del ciclo escolar"),
    ("academic.section_name", "Seccion"),
    ("enrolment.effective_on", "Fecha de inscripcion vigente"),
    ("document.issue_date", "Fecha de emision del documento"),
)

FIELD_TAG_CODES = tuple(code for code, _label in FIELD_TAGS)
