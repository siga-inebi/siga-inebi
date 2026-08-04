from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.academics.models import AcademicCycle, Grade, Section
from apps.common.models import DomainError
from apps.common.parsing import parse_uuid
from apps.enrolments.models import Enrolment
from apps.enrolments.services import change_section, create_enrolment, reenrol, withdraw
from apps.students.models import Student

from .serializers import (
    ChangeSectionSerializer,
    EnrolmentCreateSerializer,
    EnrolmentSerializer,
    ReenrolSerializer,
    WithdrawSerializer,
)


class EnrolmentListCreateView(GenericAPIView):
    """List enrolments with optional filters, or create a new one."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return EnrolmentCreateSerializer
        return EnrolmentSerializer

    @extend_schema(responses=EnrolmentSerializer(many=True))
    def get(self, request):
        qs = Enrolment.objects.select_related(
            "student__person",
            "academic_cycle",
            "grade",
            "section",
        ).order_by("-effective_on")

        student_id = parse_uuid(request.query_params.get("student"), field="student")
        if student_id:
            qs = qs.filter(student__public_id=student_id)

        cycle_id = parse_uuid(request.query_params.get("cycle"), field="cycle")
        if cycle_id:
            qs = qs.filter(academic_cycle__public_id=cycle_id)

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        serializer = EnrolmentSerializer(qs, many=True)
        return Response(serializer.data)

    @extend_schema(
        request=EnrolmentCreateSerializer,
        responses={201: EnrolmentSerializer},
    )
    def post(self, request):
        serializer = EnrolmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            student = Student.objects.get(public_id=data["student_id"])
            cycle = AcademicCycle.objects.get(public_id=data["cycle_id"])
            grade = Grade.objects.get(public_id=data["grade_id"])
            section = Section.objects.get(public_id=data["section_id"])
        except (
            Student.DoesNotExist,
            AcademicCycle.DoesNotExist,
            Grade.DoesNotExist,
            Section.DoesNotExist,
        ) as e:
            return Response(
                {"error": {"detail": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            enrolment = create_enrolment(
                student=student,
                academic_cycle=cycle,
                grade=grade,
                section=section,
                actor=request.user,
                effective_on=data.get("effective_on"),
            )
        except DomainError as e:
            return Response(
                {"error": {"detail": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enrolment = Enrolment.objects.select_related(
            "student__person", "academic_cycle", "grade", "section"
        ).get(pk=enrolment.pk)
        return Response(
            EnrolmentSerializer(enrolment).data,
            status=status.HTTP_201_CREATED,
        )


class EnrolmentWithdrawView(GenericAPIView):
    """Withdraw a student from a cycle."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WithdrawSerializer

    @extend_schema(request=WithdrawSerializer, responses={200: EnrolmentSerializer})
    def post(self, request, public_id):
        try:
            enrolment = Enrolment.objects.select_related(
                "student__person", "academic_cycle", "grade", "section"
            ).get(public_id=public_id)
        except Enrolment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = WithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            withdraw(
                enrolment=enrolment,
                reason=serializer.validated_data["reason"],
                actor=request.user,
                effective_on=serializer.validated_data.get("effective_on"),
            )
        except DomainError as e:
            return Response(
                {"error": {"detail": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enrolment.refresh_from_db()
        return Response(EnrolmentSerializer(enrolment).data)


class EnrolmentReenrolView(GenericAPIView):
    """Re-enrol a student in a new cycle."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReenrolSerializer

    @extend_schema(request=ReenrolSerializer, responses={201: EnrolmentSerializer})
    def post(self, request, public_id):
        try:
            old_enrolment = Enrolment.objects.select_related(
                "student__person",
            ).get(public_id=public_id)
        except Enrolment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = ReenrolSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            new_cycle = AcademicCycle.objects.get(public_id=data["new_cycle_id"])
            new_grade = Grade.objects.get(public_id=data["new_grade_id"])
            new_section = Section.objects.get(public_id=data["new_section_id"])
        except (AcademicCycle.DoesNotExist, Grade.DoesNotExist, Section.DoesNotExist) as e:
            return Response(
                {"error": {"detail": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_enrolment = reenrol(
                student=old_enrolment.student,
                new_cycle=new_cycle,
                new_grade=new_grade,
                new_section=new_section,
                actor=request.user,
                effective_on=data.get("effective_on"),
            )
        except DomainError as e:
            return Response(
                {"error": {"detail": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_enrolment = Enrolment.objects.select_related(
            "student__person", "academic_cycle", "grade", "section"
        ).get(pk=new_enrolment.pk)
        return Response(
            EnrolmentSerializer(new_enrolment).data,
            status=status.HTTP_201_CREATED,
        )


class EnrolmentChangeSectionView(GenericAPIView):
    """Change a student's section within the same cycle."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangeSectionSerializer

    @extend_schema(request=ChangeSectionSerializer, responses={200: EnrolmentSerializer})
    def post(self, request, public_id):
        try:
            enrolment = Enrolment.objects.select_related(
                "student__person", "academic_cycle", "grade", "section"
            ).get(public_id=public_id)
        except Enrolment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = ChangeSectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            new_section = Section.objects.get(public_id=serializer.validated_data["new_section_id"])
        except Section.DoesNotExist:
            return Response(
                {"error": {"detail": "Section not found."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            replacement = change_section(
                enrolment=enrolment,
                new_section=new_section,
                actor=request.user,
                effective_on=serializer.validated_data.get("effective_on"),
            )
        except DomainError as e:
            return Response(
                {"error": {"detail": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        replacement = Enrolment.objects.select_related(
            "student__person", "academic_cycle", "grade", "section"
        ).get(pk=replacement.pk)
        return Response(EnrolmentSerializer(replacement).data)
