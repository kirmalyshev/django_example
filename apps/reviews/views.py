from rest_framework import status
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.clinics.models import Patient
from apps.clinics.utils import PatientAPIViewMixin
from apps.profiles.permissions import IsPatient
from apps.reviews.models import Review
from apps.reviews.selectors import ReviewSelector
from apps.reviews.serializers import (
    ReviewPrivateSerializer,
    ReviewPublicSerializer,
    CreateAppointmentReviewSerializer,
    ReviewListFilterParamsSerializer,
)
from apps.reviews.workflow import ReviewWorkflow


class ReviewListView(ListAPIView):
    """
    Фильтрация:
    * ?doctor_id=23
    """

    serializer_class = ReviewPublicSerializer
    permission_classes = (IsAuthenticated, IsPatient)

    def get_patient(self) -> Patient:
        patient = self.request.user.profile.patient
        return patient

    def get_initial_queryset(self):
        return ReviewSelector.visible_to_patient()

    def get_queryset(self):
        query_params = self.request.query_params
        filter_params_serializer = ReviewListFilterParamsSerializer(data=query_params)
        filter_params_serializer.is_valid(raise_exception=True)
        initial_qs = self.get_initial_queryset()
        return ReviewSelector.filter_by_params(
            initial_qs, **filter_params_serializer.validated_data
        )


class PatientReviewListView(ReviewListView):
    permission_classes = (IsAuthenticated, IsPatient)
    serializer_class = ReviewPrivateSerializer

    def get_initial_queryset(self):
        patient = self.get_patient()
        return ReviewSelector.created_by_patient(patient_id=patient.id)


class SinglePatientReviewView(RetrieveAPIView):
    permission_classes = (IsAuthenticated, IsPatient)
    serializer_class = ReviewPrivateSerializer

    def get_patient(self) -> Patient:
        patient = self.request.user.profile.patient
        return patient

    def get_queryset(self):
        patient = self.get_patient()
        return ReviewSelector.created_by_patient(patient_id=patient.id)


class CreateReviewView(CreateAPIView, PatientAPIViewMixin):
    workflow = ReviewWorkflow

    serializer_class = CreateAppointmentReviewSerializer

    def perform_create(self, serializer: CreateAppointmentReviewSerializer) -> Review:
        data = serializer.validated_data
        patient = self.request.user.profile.patient
        review = self.workflow.create_by_patient(patient, data)

        return review

    def create(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = self.perform_create(serializer)

        output_serializer = ReviewPrivateSerializer(instance=review)
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
