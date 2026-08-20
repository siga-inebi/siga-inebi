"""
Pre-create the four educational levels of the Guatemalan system.

Preprimaria, Primaria, Basico and Diversificado are not institutional choices —
they are the national structure every establishment reports against. Asking each
institution to type them in, with a code and an order number, produced exactly
what you would expect: one level, invented codes, and a "sequence" nobody could
explain. They exist from the start now, and the ones an establishment does not
teach are simply deactivated.

Idempotent: a level is matched by its code, so running this over a database that
already has "BAS" leaves that row untouched.
"""

from django.db import migrations

# (code, name, preferred pedagogical order)
MINEDUC_LEVELS = [
    ("PRE", "Preprimaria", 1),
    ("PRI", "Primaria", 2),
    ("BAS", "Basico", 3),
    ("DIV", "Diversificado", 4),
]


def create_levels(apps, schema_editor):
    Institution = apps.get_model("academics", "Institution")
    Level = apps.get_model("academics", "Level")

    for institution in Institution.objects.all():
        levels = Level.objects.filter(institution=institution)
        existing_codes = set(levels.values_list("code", flat=True))

        for code, name, preferred in MINEDUC_LEVELS:
            if code in existing_codes:
                continue
            # The preferred slot when it is free, otherwise the end of the list:
            # the sequence is unique per institution, and stealing a slot from a
            # level somebody already created would reorder their catalogue.
            taken = set(levels.values_list("sequence", flat=True))
            sequence = preferred if preferred not in taken else max(taken) + 1
            Level.objects.create(
                institution=institution,
                name=name,
                code=code,
                sequence=sequence,
            )


def noop(apps, schema_editor):
    """
    Not reversed on purpose.

    Deleting the levels backwards would cascade into grades, offerings and
    everything hanging off them. Reversing this migration leaves the rows in
    place, which is the same thing an establishment would get by creating them
    by hand.
    """


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0005_curriculum_plan_unique_constraint"),
    ]

    operations = [
        migrations.RunPython(create_levels, noop),
    ]
