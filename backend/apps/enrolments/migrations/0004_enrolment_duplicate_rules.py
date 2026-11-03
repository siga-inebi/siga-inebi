"""
Duplicate rules for enrolments.

The old rule was "one active enrolment per student PER CYCLE", which let a
student hold an active 2026 enrolment and an active 2027 one at the same time —
a record that answers "where is this person today" twice. The rule is now one
active enrolment per student, full stop, plus never the same section twice
(repeating a grade means another cycle, with another section).

Existing rows can violate the stricter rule, so the older active enrolments are
completed first. Doing that in the migration and not by hand is the point: the
constraint cannot be added over data that contradicts it, and a deploy that
stops halfway is worse than one that says what it closed.
"""

from django.db import migrations, models
from django.db.models import Q


def complete_stale_active_enrolments(apps, schema_editor):
    """
    Keep the most recent active enrolment per student, complete the rest.

    Most recent by effective date: that is the one describing where the student
    is now. The others are closed on the day the newer one started, which is
    what a re-enrolment does from now on.
    """
    Enrolment = apps.get_model("enrolments", "Enrolment")
    rows = Enrolment.objects.filter(status="active").order_by(
        "student_id", "-effective_on", "-created_at", "-pk"
    )

    current_student = None
    keeper_effective_on = None
    for enrolment in rows:
        if enrolment.student_id != current_student:
            current_student = enrolment.student_id
            keeper_effective_on = enrolment.effective_on
            continue
        enrolment.status = "completed"
        enrolment.ends_on = max(keeper_effective_on, enrolment.effective_on)
        enrolment.save(update_fields=["status", "ends_on"])


def drop_duplicate_section_enrolments(apps, schema_editor):
    """
    Cancel the surplus rows of a repeated (student, section) pair.

    Cancelled and not deleted: the institutional history is never physically
    removed (AGENTS.md #12), and a cancelled row is exactly what a duplicated
    capture was.
    """
    Enrolment = apps.get_model("enrolments", "Enrolment")
    seen = set()
    for enrolment in Enrolment.objects.order_by("student_id", "section_id", "pk"):
        key = (enrolment.student_id, enrolment.section_id)
        if key not in seen:
            seen.add(key)
            continue
        enrolment.status = "cancelled"
        enrolment.is_active = False
        enrolment.save(update_fields=["status", "is_active"])


def noop(apps, schema_editor):
    """The data step is not reversed: the closures it made are real history."""


class Migration(migrations.Migration):
    dependencies = [
        ("enrolments", "0003_enrolmentdocumentrequirement"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="enrolment",
            name="unique_active_enrolment_per_student_cycle",
        ),
        migrations.RunPython(complete_stale_active_enrolments, noop),
        migrations.RunPython(drop_duplicate_section_enrolments, noop),
        migrations.AddConstraint(
            model_name="enrolment",
            constraint=models.UniqueConstraint(
                condition=Q(status="active"),
                fields=("student",),
                name="unique_active_enrolment_per_student",
            ),
        ),
        migrations.AddConstraint(
            model_name="enrolment",
            constraint=models.UniqueConstraint(
                fields=("student", "section"),
                name="unique_enrolment_per_student_section",
            ),
        ),
    ]
