"""
Closed catalogue of dynamic field tags document templates may reference
(RF-PLA-002).

Fixed in code, like ``apps.identity.atomic_permissions.ATOMIC_PERMISSIONS`` --
not an admin-editable table. Grounded in fields that already exist on
``apps.people.Person``, ``apps.students.Student``,
``apps.academics.{Institution,AcademicCycle,Section}`` and
``apps.enrolments.Enrolment``.

Each entry is ``(code, label, sensitive)``. ``sensitive`` tags are excluded by
default when the catalogue is listed (RF-PLA-003); none of the current
entries are medical or confidential -- ``student-records`` has not modelled
health data yet -- but the flag is the guardrail future additions must set
so they stay excluded by default without touching this ticket's code again.
"""

FIELD_TAGS = (
    ("student.full_name", "Nombre completo del estudiante", False),
    ("student.code", "Codigo del estudiante", False),
    ("institution.name", "Nombre de la institucion", False),
    ("institution.short_name", "Nombre corto de la institucion", False),
    ("academic.cycle_name", "Nombre del ciclo escolar", False),
    ("academic.section_name", "Seccion", False),
    ("enrolment.effective_on", "Fecha de inscripcion vigente", False),
    ("document.issue_date", "Fecha de emision del documento", False),
)

FIELD_TAG_CODES = tuple(code for code, _label, _sensitive in FIELD_TAGS)
