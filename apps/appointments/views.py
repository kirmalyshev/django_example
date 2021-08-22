import warnings

from django.db.models import Func, F
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import (
    ListAPIView,
    CreateAPIView,
    RetrieveDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.appointments import selectors, managers
from apps.appointments.constants import AppointmentStatus
from apps.appointments.managers import AppointmentQuerySet
from apps.appointments.models import Appointment
from apps.appointments.selectors import PatientAppointments
from apps.appointments.serializers import (
    AppointmentListSerializer,
    AppointmentSerializer,
    CreateAppointmentRequestSerializer,
    MixedAppointmentListSerializer,
    TimeSlotSerializer,
    TimeSlotDateSerializer,
    AppointmentStatusSerializer,
)
from apps.appointments.serializers_filter import (
    AppointmentsFilterParamsSerializer,
    AvailableTimeSlotsFilterSerializer,
    TimeSlotDateFilterSerializer,
)
from apps.appointments.workflows import AppointmentWorkflow
from apps.profiles.permissions import IsPatient


class CreateAppointmentRequestView(CreateAPIView):
    """
    Создать запись на прием - к выбранному доктору, или на услугу, или по определенной жалобе
    """

    serializer_class = CreateAppointmentRequestSerializer  # incoming params
    output_serializer_class = AppointmentListSerializer
    permission_classes = (IsPatient,)
    workflow = AppointmentWorkflow
    throttle_scope = 'create_appointment_request'

    def perform_create(self, serializer: CreateAppointmentRequestSerializer) -> Appointment:
        data = serializer.validated_data
        author_patient = self.request.user.profile.patient
        print(f"CreateAppointmentRequestView.perform_create {data=}")
        appointment = self.workflow.create_by_patient(author_patient, data)

        return appointment

    def create(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = self.perform_create(serializer)

        output_serializer = self.output_serializer_class(instance=appointment)
        headers = self.get_success_headers(output_serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class AppointmentListView(ListAPIView):
    """
    Записи на прием

    Получить все записи на прием для авторизованного пациента
    GET-параметры фильтрации:
    * ?service_ids=2&service_ids=12&doctor_ids=1
    * subsidiary_ids=3
    * only_past=1/true/false
    * only_future=1/true/false
    * only_active=1/true/false
    * only_archived=1/true/false
    * status_code=10&status_code=50
    * related_patient_id=13
    """

    serializer_class = AppointmentListSerializer

    permission_classes = (IsPatient,)

    def get_selector(self) -> PatientAppointments:
        patient = self.request.user.profile.patient
        return PatientAppointments(patient)

    def get_queryset(self) -> AppointmentQuerySet:
        query_params = self.request.query_params
        params_serializer = AppointmentsFilterParamsSerializer(data=query_params)
        params_serializer.is_valid(raise_exception=True)

        selector = self.get_selector()
        return selector.filter_by_params(
            selector.visible_by_patient(), **params_serializer.validated_data
        )


class OneAppointmentView(RetrieveDestroyAPIView):
    """
    Запись на прием
    Точка доступна только для авторизованного пациента

    * Получить информацию о конкретной записи на прием - GET
    * Отменить _запланированную_ запись на прием - DELETE
    """

    serializer_class = AppointmentSerializer
    permission_classes = (IsPatient,)
    workflow = AppointmentWorkflow

    def get_queryset(self) -> AppointmentQuerySet:
        patient = self.request.user.profile.patient
        return PatientAppointments(patient).visible_by_patient()

    def perform_destroy(self, instance: Appointment) -> None:
        patient = self.request.user.profile.patient
        appointment = self.workflow.cancel_by_patient(instance, patient)


class MixedAppointmentsView(APIView):
    """
    Получить Заявки и Записи пациента.
    Отображаются на главном экране приложения.
    Фильтрации данных на этой точке нет.
    """

    http_method_names = ('get',)
    serializer_class = MixedAppointmentListSerializer
    permission_classes = (IsPatient,)

    def _get_appointments(self) -> AppointmentQuerySet:
        query_params = self.request.query_params
        params_serializer = AppointmentsFilterParamsSerializer(data=query_params)
        params_serializer.is_valid(raise_exception=True)

        patient = self.request.user.profile.patient
        selector = PatientAppointments(patient)
        qs = selector.visible_by_patient__active()
        return selector.filter_by_params(qs, **params_serializer.validated_data)

    @swagger_auto_schema(responses={200: MixedAppointmentListSerializer()})
    def get(self, *args, **kwargs):
        warnings.warn("MixedAppointmentsView is deprecated", DeprecationWarning)
        data = {
            'appointments': self._get_appointments(),
            'appointment_requests': [],
        }
        serializer = MixedAppointmentListSerializer(
            instance=data, context={'request': self.request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class FinishedAppointmentsMixedView(ListAPIView):
    """
    Архивные Записи - отмененные, завершенные

    Получить отмененные/завершенные Записи пациента.
    Отображаются на экране "История".
    Фильтрации данных на этой точке нет.
    """

    serializer_class = MixedAppointmentListSerializer
    permission_classes = (IsPatient,)

    def _get_archived_appointments(self) -> AppointmentQuerySet:
        query_params = self.request.query_params
        params_serializer = AppointmentsFilterParamsSerializer(data=query_params)
        params_serializer.is_valid(raise_exception=True)

        patient = self.request.user.profile.patient
        selector = PatientAppointments(patient)
        qs = selector.visible_by_patient__archived()
        return selector.filter_by_params(qs, **params_serializer.validated_data)

    @swagger_auto_schema(responses={200: MixedAppointmentListSerializer()})
    def get(self, *args, **kwargs):
        data = {
            'appointments': self._get_archived_appointments(),
            'appointment_requests': [],
        }
        serializer = MixedAppointmentListSerializer(
            instance=data, context={'request': self.request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class TimeSlotViewSet(ReadOnlyModelViewSet):
    """
    Доступные таймслоты/талоны врачей. Только доступные (is_available=True), только будущие.

    GET-параметры фильтрации:
    * `doctor_id=1`
    * `start_date=2020-03-05`
    """

    serializer_class = TimeSlotSerializer
    permission_classes = (IsPatient,)

    def get_selector(self) -> selectors.TimeSlots:
        patient = self.request.user.profile.patient
        return selectors.TimeSlots()

    def get_queryset(self) -> managers.TimeSlotQuerySet:
        query_params = self.request.query_params
        params_serializer = AvailableTimeSlotsFilterSerializer(data=query_params)
        params_serializer.is_valid(raise_exception=True)

        selector = self.get_selector()

        return selector.filter_by_params(selector.free_future(), **params_serializer.validated_data)


class TimeSlotDatesView(ListAPIView):
    """
    Доступные даты талонов у врачей. Только доступные (is_available=True), только будущие.

    GET-параметры фильтрации:
    * `doctor_id=3`
    * `subsidiary_id=3`
    """

    permission_classes = (IsPatient,)
    serializer_class = TimeSlotDateSerializer

    def get_selector(self) -> selectors.TimeSlots:
        patient = self.request.user.profile.patient
        return selectors.TimeSlots()

    def get_queryset(self) -> managers.TimeSlotQuerySet:
        query_params = self.request.query_params
        params_serializer = TimeSlotDateFilterSerializer(data=query_params)
        params_serializer.is_valid(raise_exception=True)

        selector = self.get_selector()
        time_slots = selector.filter_by_params(
            selector.free_future(), **params_serializer.validated_data
        )
        dates = (
            time_slots.annotate(start_date=Func(F('start'), function='date'))
            .values('start_date')
            .order_by('start_date')
            .distinct('start_date')
        )
        return dates


class AppointmentStatusListView(APIView):
    """
    Все возможные статусы Записи в системе
    """

    permission_classes = (IsPatient,)
    http_method_names = ('get',)

    @swagger_auto_schema(responses={200: AppointmentStatusSerializer()})
    def get(self, *args, **kwargs):
        data = [{'code': code, 'value': value} for code, value in AppointmentStatus.VALUES.items()]
        return Response(data, status=status.HTTP_200_OK)
