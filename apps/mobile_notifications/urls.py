from django.conf.urls import url

from apps.mobile_notifications import views

app_name = 'mobile_notifications'

urlpatterns = [
    # APNS
    url(r'^apns_devices/?$', views.APNSDeviceView.as_view({'post': 'create'}), name='apns_devices'),
    url(
        r'^apns_devices/(?P<registration_id>[0-9a-fA-F]{64})$',
        views.APNSDeviceView.as_view({'delete': 'destroy'}),
        name='apns_device_detail',
    ),
    # GCM
    url(r'^gcm_devices/?$', views.GCMDeviceView.as_view({'post': 'create'}), name='gcm_devices'),
    url(
        r'^gcm_devices/(?P<registration_id>\S+)$',
        views.GCMDeviceView.as_view({'delete': 'destroy'}),
        name='gcm_device_detail',
    ),
    # FCM
    url(r'^fcm_devices/?$', views.FCMDeviceView.as_view({'post': 'create'}), name='fcm_devices'),
    url(
        r'^fcm_devices/(?P<registration_id>\S+)$',
        views.FCMDeviceView.as_view({'delete': 'destroy'}),
        name='fcm_device_detail',
    ),
    # Notification log
    url(r'^notifications/$', views.NotificationView.as_view(), name='notifications'),
    url(r'^event/(?P<push_uuid>[\w\d-]+)$', views.NotificationEventView.as_view(), name='events'),
]
