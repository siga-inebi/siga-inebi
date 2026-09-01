from django.dispatch import receiver

from apps.attendance.services import revoke_credential_for_closed_permanence
from apps.enrolments.events import student_permanence_closed


@receiver(student_permanence_closed)
def close_student_credential_access(sender, *, student, reason, effective_on, actor, **kwargs):
    return revoke_credential_for_closed_permanence(
        student=student,
        actor=actor,
        withdrawal_reason=reason,
        effective_on=effective_on,
    )
