from django.conf.urls import url
from django.urls import path

from apps.appointments import views

app_name = 'appointments'

urlpatterns = [
    path('', views.AppointmentListView.as_view(), name='list'),
    path('<int:pk>', views.OneAppointmentView.as_view(), name='item'),
    url(r'^requests/create$', views.CreateAppointmentRequestView.as_view(), name='request_create',),
    path('mixed', views.MixedAppointmentsView.as_view(), name='mixed_list'),
    path('available_status_list', views.AppointmentStatusListView.as_view(), name='status_list'),
    path(
        'finished/mixed', views.FinishedAppointmentsMixedView.as_view(), name='finished_list_mixed'
    ),
    path(
        'available_time_slot_dates', views.TimeSlotDatesView.as_view(), name='time_slot_date_list',
    ),
    path(
        'available_time_slots',
        views.TimeSlotViewSet.as_view({'get': 'list'}),
        name='time_slot_list',
    ),
    path(
        'available_time_slots/<int:pk>',
        views.TimeSlotViewSet.as_view({'get': 'retrieve'}),
        name='time_slot_item',
    ),
]
