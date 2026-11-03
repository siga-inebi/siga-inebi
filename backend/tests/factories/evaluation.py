"""
Factory fixtures for evaluation domain tests.
"""

from datetime import timedelta

import factory
from django.utils import timezone

from apps.evaluation.models import CaptureExceptionGrant, EvaluationUnit


class EvaluationUnitFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EvaluationUnit

    academic_cycle = factory.SubFactory("tests.factories.academic.AcademicCycleFactory")
    number = factory.Sequence(lambda n: n + 1)
    name = factory.LazyAttribute(lambda obj: f"Unit {obj.number}")
    starts_on = factory.LazyAttribute(
        lambda obj: timezone.localdate() + timedelta(days=(obj.number - 1) * 65)
    )
    ends_on = factory.LazyAttribute(lambda obj: obj.starts_on + timedelta(days=60))
    # Capture window: starts 5 days before evaluation starts, ends 55 days into evaluation
    capture_starts_on = factory.LazyAttribute(lambda obj: obj.starts_on + timedelta(days=-5))
    capture_ends_on = factory.LazyAttribute(lambda obj: obj.starts_on + timedelta(days=55))
    status = EvaluationUnit.UnitStatus.OPEN


class CaptureExceptionGrantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CaptureExceptionGrant

    evaluation_unit = factory.SubFactory(EvaluationUnitFactory)
    subject = factory.SubFactory("tests.factories.academic.SubjectFactory")
    teacher = factory.SubFactory("tests.factories.people.PersonFactory")
    reason = "Docente no alcanzó a subir notas por falla de conectividad."
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=1))


def open_unit(cycle, **kwargs):
    """A unit whose capture window brackets today (the factory dates drift)."""
    today = timezone.localdate()
    kwargs.setdefault("starts_on", today - timedelta(days=5))
    kwargs.setdefault("ends_on", today + timedelta(days=5))
    kwargs.setdefault("capture_starts_on", today - timedelta(days=5))
    kwargs.setdefault("capture_ends_on", today + timedelta(days=5))
    return EvaluationUnitFactory(academic_cycle=cycle, **kwargs)


def grant_scoped_permission(user, codename, **scope):
    """
    Role with one atomic permission for ``user``; ``scope`` (``institution=``,
    ``section=``…) becomes its ScopeGrant. Without scope the role has none:
    the permission alone, as a teacher whose scope is the teaching assignment.
    """
    from tests.factories.identity import (
        PermissionFactory,
        RoleAssignmentFactory,
        RoleFactory,
        ScopeGrantFactory,
    )

    assignment = RoleAssignmentFactory(
        user=user,
        role=RoleFactory(permissions=[PermissionFactory(codename=codename)]),
        identity_scope=False,
    )
    if scope:
        ScopeGrantFactory(assignment=assignment, **scope)
    return assignment
