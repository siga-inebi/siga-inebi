from django.db import transaction

from apps.audit.services import record_event


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
