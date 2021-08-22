from django.conf.urls import url

from apps.profiles import views

app_name = 'profiles'

urlpatterns = [url(r'^(?P<pk>\d+)/?$', views.ProfileView.as_view(), name='profile')]
