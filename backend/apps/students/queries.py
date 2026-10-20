"""Read-side queries for the student-records domain."""

from apps.common.exceptions import ResourceNotFoundError
from apps.students.models import EmergencyContact, Student, StudentHealthNote, StudentObservation


def _filter_active(queryset, *, include_inactive=False):
    return queryset if include_inactive else queryset.filter(is_active=True)


def _get(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except queryset.model.DoesNotExist as exc:
        raise ResourceNotFoundError(f"No se encontró {label}.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError(f"No se encontró {label}.") from exc


def student_or_404(public_id):
    return _get(Student.objects.all(), public_id, "el estudiante")


def students(*, include_inactive=True, status=None):
    queryset = _filter_active(
        Student.objects.select_related("person"), include_inactive=include_inactive
    )
    return queryset if status is None else queryset.filter(status=status)


def student_dossier_queryset(*, actor):
    from django.db.models import Exists, OuterRef

    from apps.identity.scopes import authorized_student_queryset, effective_student_queryset

    readable = authorized_student_queryset(
        user=actor, codename="student_view_basic", queryset=students(include_inactive=True)
    )
    editable = (
        effective_student_queryset(user=actor, codename="student_edit_basic")
        if actor.has_atomic_permission("student_edit_basic")
        else Student.objects.none()
    )
    return readable.annotate(record_can_manage=Exists(editable.filter(pk=OuterRef("pk"))))


def guardians(*, include_inactive=True):
    from apps.students.models import Guardian

    return _filter_active(
        Guardian.objects.select_related("person"), include_inactive=include_inactive
    )


def guardian_relations(*, student_public_id=None):
    from apps.students.models import StudentGuardianRelation

    queryset = StudentGuardianRelation.objects.select_related("student", "guardian__person")
    if student_public_id is not None:
        queryset = queryset.filter(student__public_id=student_public_id)
    return queryset


def guardian_relations_for_record(*, actor, student_public_id, replacement_for=None):
    from django.db.models import BooleanField, Value
    from django.utils import timezone

    from apps.identity.scopes import authorized_student_queryset

    student = _get(
        authorized_student_queryset(user=actor, codename="student_view_basic"),
        student_public_id,
        "Student",
    )
    queryset = guardian_relations().filter(student=student)
    if replacement_for is not None:
        if not queryset.filter(pk=replacement_for).exists():
            raise ResourceNotFoundError("No se encontró la relación con el encargado.")
        queryset = queryset.filter(
            ends_at__isnull=True, is_active=True, starts_at__lte=timezone.localdate()
        ).exclude(pk=replacement_for)
    can_manage = student_record_can_manage(actor=actor, student=student)
    return queryset.annotate(
        record_can_manage=Value(can_manage, output_field=BooleanField())
    ).order_by("-is_primary", "pk")


def emergency_contacts(student, *, include_inactive=False):
    # Orden explicito: el listado se pagina, y sin el dos paginas pueden repetir u
    # omitir contactos (INC-009). `id` desempata nombres iguales.
    return _filter_active(
        EmergencyContact.objects.filter(student=student).select_related("student"),
        include_inactive=include_inactive,
    ).order_by("name", "id")


def with_student_record_actions(queryset, *, actor, student):
    from django.db.models import BooleanField, Value

    can_manage = student_record_can_manage(actor=actor, student=student)
    return queryset.annotate(record_can_manage=Value(can_manage, output_field=BooleanField()))


def student_record_can_manage(*, actor, student):
    """Read capabilities without auditing a write that was never attempted."""
    from apps.identity.scopes import effective_student_queryset

    return (
        actor.has_atomic_permission("student_edit_basic")
        and effective_student_queryset(user=actor, codename="student_edit_basic")
        .filter(pk=student.pk)
        .exists()
    )


def emergency_contact_or_404(public_id):
    return _get(
        EmergencyContact.objects.select_related("student").all(),
        public_id,
        "el contacto de emergencia",
    )


def health_notes(student, *, include_inactive=False):
    return _filter_active(
        StudentHealthNote.objects.filter(student=student).select_related("student", "author"),
        include_inactive=include_inactive,
    ).order_by("-recorded_on", "-created_at", "-pk")


def health_note_or_404(public_id):
    return _get(
        StudentHealthNote.objects.select_related("student", "author").all(),
        public_id,
        "la nota de salud",
    )


def observations(student, *, include_inactive=False):
    return _filter_active(
        StudentObservation.objects.filter(student=student).select_related("student", "author"),
        include_inactive=include_inactive,
    ).order_by("-observed_on", "-created_at", "-pk")


def observation_or_404(public_id):
    return _get(
        StudentObservation.objects.select_related("student", "author"),
        public_id,
        "la observación",
    )


def student_record_for_action(*, actor, public_id, permission="student_edit_basic"):
    from apps.identity.scopes import authorized_student_queryset

    return _get(
        authorized_student_queryset(user=actor, codename=permission, queryset=students()),
        public_id,
        "Student",
    )


def guardian_for_link(guardian_id):
    from apps.students.models import Guardian

    try:
        return Guardian.objects.select_related("person").get(pk=guardian_id)
    except Guardian.DoesNotExist as exc:
        raise ResourceNotFoundError("Encargado no encontrado.") from exc


def student_status_context(*, student, actor, selected_status=None):
    from django.db.models import F, Q

    from apps.audit.models import AuditEvent
    from apps.enrolments.services import active_enrolments
    from apps.students.services import student_status_warnings

    has_active_enrolment = active_enrolments(student=student).exists()
    event = (
        AuditEvent.objects.filter(resource="Student", resource_identifier=str(student.pk))
        .filter(
            Q(action="students.student.status_changed")
            | (
                Q(
                    action="students.student.updated",
                    context__fields__contains=["status"],
                    context__before__has_key="status",
                    context__after__has_key="status",
                )
                & ~Q(context__before__status=F("context__after__status"))
            )
            | Q(action="students.student.deactivated")
        )
        .order_by("-created_at", "-pk")
        .first()
    )
    last_change = None
    if event is not None:
        last_change = {
            "previous_status": event.context.get("before", {}).get("status"),
            "status": event.context.get("after", {}).get("status", "inactive"),
            "actor_label": event.actor_label or "Autor no registrado",
            "changed_at": event.created_at,
        }
    labels = {
        "pre_enrolled": "Preinscrito",
        "active": "Activo",
        "inactive": "Inactivo",
        "withdrawn": "Retirado",
        "graduated": "Graduado",
        "transferred": "Trasladado",
    }
    return {
        "status": student.status,
        "can_change": student.is_active and student_record_can_manage(actor=actor, student=student),
        "options": [
            {"value": value, "label": labels[value]} for value in Student.StudentStatus.values
        ],
        "has_active_enrolment": has_active_enrolment,
        "warnings": student_status_warnings(
            status=selected_status or student.status, has_active_enrolment=has_active_enrolment
        ),
        "last_change": last_change,
    }
