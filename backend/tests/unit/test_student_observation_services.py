from datetime import timedelta

import pytest
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.common.models import DomainError
from apps.students.models import StudentObservation
from apps.students.services import create_student_observation, deactivate_student_observation
from tests.factories.identity import UserFactory
from tests.factories.students import StudentFactory, StudentObservationFactory


@pytest.mark.unit
@pytest.mark.django_db
def test_create_observation_preserves_author_date_and_description():
    student = StudentFactory()
    actor = UserFactory()

    observation = create_student_observation(
        student=student,
        actor=actor,
        description="  Seguimiento pedagogico  ",
    )

    assert observation.description == "Seguimiento pedagogico"
    assert observation.author == actor
    assert observation.observed_on == timezone.localdate()
    event = AuditEvent.objects.get(action="students.observation.created")
    assert event.context == {"student_id": student.pk}
    assert "Seguimiento" not in str(event.context)


@pytest.mark.unit
@pytest.mark.django_db
def test_create_observation_rejects_blank_or_future_description():
    student = StudentFactory()
    actor = UserFactory()

    with pytest.raises(DomainError):
        create_student_observation(student=student, actor=actor, description=" ")
    with pytest.raises(DomainError):
        create_student_observation(
            student=student,
            actor=actor,
            description="Dato",
            observed_on=timezone.localdate() + timedelta(days=1),
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_deactivate_observation_keeps_history():
    observation = StudentObservationFactory()

    deactivate_student_observation(observation=observation, actor=observation.author)

    observation.refresh_from_db()
    assert observation.is_active is False
    assert StudentObservation.objects.filter(pk=observation.pk).exists()
