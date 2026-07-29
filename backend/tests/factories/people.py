import factory

from apps.people.models import Person


class PersonFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Person

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Sequence(lambda n: f"person{n}@example.test")
    phone_number = factory.Sequence(lambda n: f"555{n:06d}")
