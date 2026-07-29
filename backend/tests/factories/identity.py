import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import ContentType, Permission
from django.utils import timezone

from apps.identity.models import Role, RoleAssignment, ScopeGrant
from tests.factories.people import PersonFactory


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        skip_postgeneration_save = True

    person = factory.SubFactory(PersonFactory)
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.test")
    status = get_user_model().AccountStatus.ACTIVE
    is_active = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        if not create:
            return
        obj.set_password(extracted or "test-pass-123")
        obj.save(update_fields=["password"])


class PermissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Permission

    name = factory.Sequence(lambda n: f"Permission {n}")
    codename = factory.Sequence(lambda n: f"perm_{n}")
    content_type = factory.LazyFunction(lambda: ContentType.objects.get_for_model(Role))


class RoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Role
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"Role {n}")
    slug = factory.Sequence(lambda n: f"role-{n}")
    is_system = False

    @factory.post_generation
    def permissions(obj, create, extracted, **kwargs):
        if create and extracted:
            obj.permissions.set(extracted)


class RoleAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RoleAssignment

    user = factory.SubFactory(UserFactory)
    role = factory.SubFactory(RoleFactory)
    starts_at = factory.LazyFunction(timezone.now)
    ends_at = None


class ScopeGrantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScopeGrant

    assignment = factory.SubFactory(RoleAssignmentFactory)
    starts_at = factory.LazyFunction(timezone.now)
    ends_at = None
