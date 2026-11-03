import pytest

from apps.common.exceptions import DomainError
from apps.students import services
from tests.factories.students import (
    EmergencyContactFactory,
    StudentHealthNoteFactory,
    StudentObservationFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.django_db]
CASES = [
    (
        StudentHealthNoteFactory,
        services.update_student_health_note,
        "health_note",
        "content",
        services.deactivate_student_health_note,
    ),
    (
        StudentObservationFactory,
        services.update_student_observation,
        "observation",
        "description",
        services.deactivate_student_observation,
    ),
    (
        EmergencyContactFactory,
        services.update_emergency_contact,
        "emergency_contact",
        "name",
        services.deactivate_emergency_contact,
    ),
]


@pytest.mark.parametrize("factory,update,argument,field,deactivate", CASES)
@pytest.mark.parametrize("operation", ["edit", "deactivate"])
def test_mutation_rolls_back_if_audit_fails(
    monkeypatch, factory, update, argument, field, deactivate, operation
):
    record = factory()
    before = getattr(record, field)

    def fail(**kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(services, "record_event", fail)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        if operation == "edit":
            update(**{argument: record, field: "Correccion sintetica", "actor": None})
        else:
            deactivate(**{argument: record, "actor": None})
    record.refresh_from_db()
    assert getattr(record, field) == before and record.is_active is True


@pytest.mark.parametrize("factory,update,argument,field,deactivate", CASES)
def test_content_validation_is_in_domain(factory, update, argument, field, deactivate):
    record = factory()
    with pytest.raises(DomainError):
        update(**{argument: record, field: " ", "actor": None})
