from constance import config
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, permissions
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clinics.constants import I_NEED_CONSULTATION
from apps.clinics.filter_serializers import (
    DoctorListFilterParamsSerializer,
    ServiceListFilterParamsSerializer,
)
from apps.clinics.models import ClinicImage, Patient
from apps.clinics.models import Promotion
from apps.clinics.paginators import DoctorPagination
from apps.clinics.permissions import IsRelationMaster
from apps.clinics.selectors import (
    DoctorSelector,
    SubsidiarySelector,
    ServiceSelector,
    PatientSelector,
)
from apps.clinics.serializers import (
    SubsidiarySerializer,
    SubsidiaryListSerializer,
    DoctorListSerializer,
    ServiceSerializer,
    PromotionSerializer,
    PromotionFilterSerializer,
    ClinicInfoSerializer,
    ApplicationConfigSerializer,
    RelatedPatientSerializer,
    DoctorSerializer,
)
from apps.clinics.utils import PatientAPIViewMixin
from apps.clinics.workflows import RelatedPatientsWorkflow
from apps.profiles.models import Relation
from apps.profiles.permissions import IsPatient


class DoctorListView(ListAPIView):
    """
    Список врачей

    Получить всех неудаленных `is_removed=False` И видимых `is_displayed=True` врачей.
    Фильтрация через параметры `?service_ids=2&service_ids=12&subsidiary_ids=55`
    """

    serializer_class = DoctorListSerializer
    pagination_class = DoctorPagination

    def get_queryset(self):
        query_params = self.request.query_params
        filter_params_serializer = DoctorListFilterParamsSerializer(data=query_params)
        filter_params_serializer.is_valid(raise_exception=True)
        qs = DoctorSelector.visible_to_patient()
        return DoctorSelector.filter_by_params(qs, **filter_params_serializer.validated_data)


class OneDoctorView(RetrieveAPIView):
    """
    Получить информацию по одному доктору
    Если врач помечен как удаленный - будет 404
    Если врач помечен как 'скрытый от всех' - будет 404
    """

    serializer_class = DoctorSerializer

    def get_queryset(self):
        # return DoctorSelector.visible_to_patient()
        return DoctorSelector.all().without_hidden()


class SubsidiaryListView(ListAPIView):
    """
    Список филиалов

    Получить все неудаленные (`is_removed=False`) И видимые `is_displayed=True` филиалы
    """

    serializer_class = SubsidiaryListSerializer

    def get_queryset(self):
        return SubsidiarySelector.visible_to_patient()


class OneSubsidiaryView(RetrieveAPIView):
    """ Позволяет получить информацию по одном филиале """

    serializer_class = SubsidiarySerializer

    def get_queryset(self):
        return SubsidiarySelector.visible_to_patient()


class ServiceListView(ListAPIView):
    """
    Список услуг

    Получить все услуги
    Фильтрация через параметры
    * `?subsidiary_ids=5&subsidiary_ids=133`
    * `?only_root=true/false`
    * `?parent_id=11`
    * `?mobile_app_section=doctors/services/create_appointment_by_patient`
    """

    serializer_class = ServiceSerializer

    def get_queryset(self):
        query_params = self.request.query_params
        filter_params_serializer = ServiceListFilterParamsSerializer(data=query_params)
        filter_params_serializer.is_valid(raise_exception=True)

        selector = ServiceSelector

        return selector.filter_by_params(
            selector.visible_to_patient(), **filter_params_serializer.validated_data
        )


class OneServiceView(RetrieveAPIView):
    """
    Информация об отдельной услуге
    """

    serializer_class = ServiceSerializer

    def get_queryset(self):
        return ServiceSelector().visible_to_patient()


class PromotionListView(ListAPIView):
    """
    Список акций

    Параметры фильтрации:
    * ?subsidiary_ids=2&subsidiary_ids=3
    """

    serializer_class = PromotionSerializer

    def get_queryset(self):
        query_params = self.request.query_params
        filter_params_serializer = PromotionFilterSerializer(data=query_params)
        filter_params_serializer.is_valid(raise_exception=True)
        data = filter_params_serializer.validated_data

        qs = Promotion.objects.displayed()
        if data and data['subsidiary_ids']:
            qs = qs.filter(subsidiaries__id__in=data['subsidiary_ids'])
        return qs


class OnePromotionView(RetrieveAPIView):
    """
    Отдельная акция
    """

    serializer_class = PromotionSerializer

    def get_queryset(self):
        return Promotion.objects.displayed()


class ClinicInfoView(APIView):
    http_method_names = ('get',)
    permission_classes = (AllowAny,)

    @swagger_auto_schema(responses={200: ClinicInfoSerializer()})
    def get(self, *args, **kwargs):
        data = {
            'images': ClinicImage.objects.all(),
            'text': config.CLINIC_INFO_TEXT,
            'empty_appointment_text': I_NEED_CONSULTATION,
        }
        serializer = ClinicInfoSerializer(instance=data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ApplicationConfigView(APIView):
    http_method_names = ('get',)
    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(responses={200: ApplicationConfigSerializer()})
    def get(self, *args, **kwargs):
        data = {
            'application_ids': {
                'android': settings.GCM_DEFAULT_APPLICATION_ID,
                'ios': settings.APNS_DEFAULT_APPLICATION_ID,
            },
        }
        serializer = ApplicationConfigSerializer(instance=data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RelatedPatientListCreateView(ListCreateAPIView, PatientAPIViewMixin):
    serializer_class = RelatedPatientSerializer
    output_serializer_class = RelatedPatientSerializer

    def get_queryset(self):
        # relations = PatientSelector.get_slave_relations(
        relations = PatientSelector.get_slave_relations__with_patients(
            patient=self._get_author_patient()
        )
        return relations.select_related("slave", "slave__patient")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # hack to avoid nested data further
        in_data = serializer.validated_data
        in_data.update(in_data.get("slave"))

        relation, patient = RelatedPatientsWorkflow.create_related_patient(
            author_patient=self._get_author_patient(), new_patient_data=in_data
        )

        output_serializer = self.output_serializer_class(instance=relation)
        headers = self.get_success_headers(serializer.data)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class RelatedPatientView(RetrieveUpdateDestroyAPIView, PatientAPIViewMixin):
    serializer_class = RelatedPatientSerializer
    permission_classes = (
        IsPatient,
        IsRelationMaster,
    )

    def get_queryset(self):
        relations = PatientSelector.get_slave_relations__with_patients(
            patient=self._get_author_patient()
        )
        return relations.select_related("slave", "slave__patient")

    def perform_update(self, serializer: RelatedPatientSerializer):
        raise NotImplementedError

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance: Relation = self.get_object()
        serializer: RelatedPatientSerializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        in_data = serializer.validated_data
        in_data.update(in_data.get("slave", {}))

        relation, patient = RelatedPatientsWorkflow.update_related_patient(
            author_patient=self._get_author_patient(),
            relation=instance,
            related_patient_data=in_data,
        )

        output_serializer = self.serializer_class(instance=relation)
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(output_serializer.data)
