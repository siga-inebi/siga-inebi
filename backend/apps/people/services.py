"""
Domain services for the people registry.

The view layer never calls the ORM directly to create or change a ``Person``:
every write goes through here so it is audited (AGENTS.md #8, audit-strategy.md).
"""

from django.db import transaction

from apps.audit.services import record_event
from apps.common.exceptions import AuthorizationError, DomainError, ResourceNotFoundError
from apps.people.models import Person

INSTITUTIONAL_FIELDS = (
    "cui",
    "birth_date",
    "phone_number",
    "sex",
    "nationality",
    "address",
    "department",
    "municipality",
)
COMPLETION_FIELDS = (
    "first_name",
    "last_name",
    "cui",
    "email",
    "phone_number",
    "birth_date",
    "sex",
    "nationality",
    "address",
    "department",
    "municipality",
)


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
    birth_date=None,
):
    """Register an institutional person. Optional fields default to blank."""
    with transaction.atomic():
        person = Person.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            institutional_identifier=institutional_identifier,
            birth_date=birth_date,
        )
        _audit(actor, "people.person.created", person)
    return person


def complete_person_for_profile(*, person_public_id, person_data=None, actor):
    """Lock and complete an existing person inside the caller's transaction."""
    if not actor or not (
        actor.is_superuser
        or actor.has_scoped_permission("person_edit", scope={"module_key": "identity"})
    ):
        raise AuthorizationError("Se requiere person.edit con alcance identity.")
    try:
        person = Person.objects.select_for_update().get(public_id=person_public_id)
    except Person.DoesNotExist as exc:
        raise ResourceNotFoundError("La persona no existe.") from exc
    if not person.is_active:
        raise DomainError("No se puede convertir una persona desactivada.")
    changes = {
        name: value
        for name, value in (person_data or {}).items()
        if name in COMPLETION_FIELDS and value not in (None, "")
    }
    values = {name: changes.get(name, getattr(person, name)) for name in INSTITUTIONAL_FIELDS}
    missing = [
        name for name, value in values.items() if not value or value == Person.Sex.NOT_SPECIFIED
    ]
    if missing:
        raise DomainError("Complete los datos institucionales: " + ", ".join(missing) + ".")
    if not values["cui"].isdigit() or len(values["cui"]) != 13:
        raise DomainError("El CUI debe tener exactamente 13 digitos.")
    if not changes:
        return person
    for name, value in changes.items():
        setattr(person, name, value)
    person.save(update_fields=[*changes, "updated_at"])
    _audit(actor, "people.person.profile_completed", person, fields=sorted(changes))
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
    birth_date=None,
    sex=None,
    nationality=None,
    address=None,
    department=None,
    municipality=None,
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
        "birth_date": birth_date,
        "sex": sex,
        "nationality": nationality,
        "address": address,
        "department": department,
        "municipality": municipality,
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
