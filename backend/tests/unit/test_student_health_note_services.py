from datetime import timedelta

import pytest
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.common.models import DomainError
from apps.students.models import StudentHealthNote
from apps.students.services import create_student_health_note, deactivate_student_health_note
from tests.factories.identity import UserFactory
from tests.factories.students import StudentFactory, StudentHealthNoteFactory


@pytest.mark.unit
@pytest.mark.django_db
def test_create_health_note_preserves_author_and_audits_without_content():
    student = StudentFactory()
    actor = UserFactory()

    note = create_student_health_note(
        student=student,
        actor=actor,
        content="  Alergia de prueba  ",
    )

    assert note.content == "Alergia de prueba"
    assert note.author == actor
    event = AuditEvent.objects.get(action="students.health_note.created")
    assert event.context["student_id"] == student.pk
    assert "Alergia" not in str(event.context)


@pytest.mark.unit
@pytest.mark.django_db
def test_create_health_note_rejects_blank_or_future_content():
    student = StudentFactory()
    actor = UserFactory()

    with pytest.raises(DomainError):
        create_student_health_note(student=student, actor=actor, content=" ")
    with pytest.raises(DomainError):
        create_student_health_note(
            student=student,
            actor=actor,
            content="Dato",
            recorded_on=timezone.localdate() + timedelta(days=1),
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_deactivate_health_note_keeps_history():
    note = StudentHealthNoteFactory()

    deactivate_student_health_note(health_note=note, actor=note.author)

    note.refresh_from_db()
    assert note.is_active is False
    assert StudentHealthNote.objects.filter(pk=note.pk).exists()
