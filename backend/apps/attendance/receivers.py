from django.dispatch import receiver

from apps.attendance.services import (
    restore_credential_for_reopened_permanence,
    revoke_credential_for_closed_permanence,
)
from apps.enrolments.events import (
    student_permanence_closed,
    student_permanence_reopened,
)


@receiver(student_permanence_closed)
def close_student_credential_access(
    sender, *, student, reason, effective_on, movement, actor, **kwargs
):
    return revoke_credential_for_closed_permanence(
        student=student,
        actor=actor,
        withdrawal_reason=reason,
        effective_on=effective_on,
        movement=movement,
    )


@receiver(student_permanence_reopened)
def reopen_student_credential_access(sender, *, student, movement, actor, **kwargs):
    return restore_credential_for_reopened_permanence(
        student=student,
        movement=movement,
        actor=actor,
    )
