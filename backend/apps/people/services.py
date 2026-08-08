"""
Domain services for the people registry.

The view layer never calls the ORM directly to create or change a ``Person``:
every write goes through here so it is audited (AGENTS.md #8, audit-strategy.md).
"""

from django.db import transaction

from apps.audit.services import record_event
from apps.people.models import Person


def _audit(actor, action, person, **context):
    record_event(
        actor=actor,
        action=action,
        resource="Person",
        resource_identifier=str(person.pk),
        context=context,
    )


def create_person(
    *,
    actor=None,
    first_name,
    last_name,
    email="",
    phone_number="",
    institutional_identifier="",
):
    """Register an institutional person. Optional fields default to blank."""
    with transaction.atomic():
        person = Person.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            institutional_identifier=institutional_identifier,
        )
        _audit(actor, "people.person.created", person)
    return person


def update_person(
    *,
    person,
    actor=None,
    first_name=None,
    last_name=None,
    email=None,
    phone_number=None,
    institutional_identifier=None,
):
    """
    Apply only the fields the caller actually supplied, and audit what changed.
    ``None`` means "not supplied", never "set to null" (mirrors
    ``apps.academics.services._changed``).
    """
    candidates = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone_number": phone_number,
        "institutional_identifier": institutional_identifier,
    }
    fields = [name for name, value in candidates.items() if value is not None]
    if not fields:
        return person

    for name in fields:
        setattr(person, name, candidates[name])

    with transaction.atomic():
        person.save(update_fields=[*fields, "updated_at"])
        _audit(actor, "people.person.updated", person, fields=fields)
    return person


def deactivate_person(*, person, actor=None):
    if not person.is_active:
        return person

    with transaction.atomic():
        person.is_active = False
        person.save(update_fields=["is_active", "updated_at"])
        record_event(
            actor=actor,
            action="people.person.deactivated",
            resource="Person",
            resource_identifier=str(person.pk),
            context={"public_id": str(person.public_id)},
        )

    return person
