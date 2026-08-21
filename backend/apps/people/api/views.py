from rest_framework import generics

from apps.people import queries
from apps.people.api.serializers import PersonSerializer
from apps.people.services import create_person, deactivate_person, update_person


class PersonListCreateView(generics.ListCreateAPIView):
    serializer_class = PersonSerializer

    def get_queryset(self):
        return queries.people()

    def perform_create(self, serializer):
        serializer.instance = create_person(actor=self.request.user, **serializer.validated_data)


class PersonDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PersonSerializer
    lookup_field = "public_id"

    def get_queryset(self):
        return queries.people()

    def perform_update(self, serializer):
        update_person(
            person=serializer.instance, actor=self.request.user, **serializer.validated_data
        )

    def perform_destroy(self, instance):
        deactivate_person(person=instance, actor=self.request.user)
