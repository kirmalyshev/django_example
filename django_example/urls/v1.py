from django.conf.urls import url
from django.urls import path, include

from apps.clinics import views

app_name = 'api.v1'

urlpatterns = [
    url(r'^clinic_info$', views.ClinicInfoView.as_view(), name='clinic_info'),
    url(
        r'^clinic_application_config',
        views.ApplicationConfigView.as_view(),
        name='clinic_application_config',
    ),
    url(r'^services$', views.ServiceListView.as_view(), name='service_list'),
    url(r'^services/(?P<pk>\d+)$', views.OneServiceView.as_view(), name='service_item'),
    url(r'^subsidiaries$', views.SubsidiaryListView.as_view(), name='subsidiary_list'),
    url(r'^subsidiaries/(?P<pk>\d+)$', views.OneSubsidiaryView.as_view(), name='subsidiary_item'),
    url(r'^doctors$', views.DoctorListView.as_view(), name='doctor_list'),
    url(r'^doctors/(?P<pk>\d+)$', views.OneDoctorView.as_view(), name='doctor_item'),
    url(r'^promotions$', views.PromotionListView.as_view(), name='promotion_list'),
    url(r'^promotions/(?P<pk>\d+)$', views.OnePromotionView.as_view(), name='promotion_item'),
    url(
        r'^related_patients$',
        views.RelatedPatientListCreateView.as_view(),
        name='related_patient_list',
    ),
    url(
        r'^related_patients/(?P<pk>\d+)$',
        views.RelatedPatientView.as_view(),
        name='related_patient_item',
    ),
    path('appointments/', include('apps.appointments.urls', namespace='appointments')),
    path('auth/', include('apps.auth.urls', namespace='auth')),
    path('profiles/', include('apps.profiles.urls', namespace='profiles')),
    path('integration/', include('apps.integration.urls', namespace='integration')),
    path(
        'mobile_notifications/',
        include('apps.mobile_notifications.urls', namespace='mobile_notifications'),
    ),
    url(r'^support/', include('apps.support.urls', namespace='support')),
    url(r'^features/', include('apps.feature_toggles.urls', namespace='feature_toggles')),
    url(r'^notify/', include('apps.notify.urls', namespace='notify')),
    url(r'^reviews/', include('apps.reviews.urls', namespace='reviews')),
]
