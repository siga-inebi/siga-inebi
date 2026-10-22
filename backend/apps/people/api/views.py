from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, generics
from rest_framework.permissions import IsAuthenticated

from apps.identity.api.permissions import ScopedAtomicPermission
from apps.people import queries
from apps.people.api.serializers import PersonListQuerySerializer, PersonRegistrySerializer
from apps.people.services import create_person, deactivate_person, update_person


@extend_schema_view(get=extend_schema(parameters=[PersonListQuerySerializer]))
class PersonListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, ScopedAtomicPermission]
    permission_scope = {"module_key": "identity"}
    serializer_class = PersonRegistrySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["first_name", "last_name", "cui", "institutional_identifier"]

    def get_permissions(self):
        self.permission_codenames = (
            ("person_view", "person_edit") if self.request.method == "GET" else ("person_edit",)
        )
        return super().get_permissions()

    def get_queryset(self):
        params = PersonListQuerySerializer(data=self.request.query_params.dict())
        params.is_valid(raise_exception=True)
        return queries.people(**params.validated_data)

    def perform_create(self, serializer):
        serializer.instance = create_person(actor=self.request.user, **serializer.validated_data)


class PersonDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, ScopedAtomicPermission]
    permission_scope = {"module_key": "identity"}
    serializer_class = PersonRegistrySerializer
    lookup_field = "public_id"

    def get_permissions(self):
        self.permission_codenames = (
            ("person_view", "person_edit") if self.request.method == "GET" else ("person_edit",)
        )
        return super().get_permissions()

    def get_queryset(self):
        return queries.people()

    def perform_update(self, serializer):
        update_person(
            person=serializer.instance, actor=self.request.user, **serializer.validated_data
        )

    def perform_destroy(self, instance):
        deactivate_person(person=instance, actor=self.request.user)
