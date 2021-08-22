from django.conf.urls import url
from django.urls import path

from apps.support import views

app_name = 'support'


urlpatterns = [
    path('create_request', views.SupportRequestView.as_view(), name='create_request'),
    path('faq_list', views.FAQListView.as_view(), name='faq_list'),
]
