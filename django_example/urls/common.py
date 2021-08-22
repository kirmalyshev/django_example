# encoding=utf-8

"""django_example URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.utils.translation import ugettext_lazy as _
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

admin.autodiscover()

admin.site.site_header = _('Администрирование django_exampleApp')
admin.site.site_title = _('Администрирование django_exampleApp')

# handler404 = 'apps.core.views.page_not_found'


schema_view = get_schema_view(
    openapi.Info(
        title="Snippets API",
        default_version='v1',
        description="API Endpoints for django_example project. You're interested in `api`",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="dev@django_example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

docs_urlpatterns = [
    url(
        r'^swagger(?P<format>\.json|\.yaml)$',
        schema_view.without_ui(cache_timeout=0),
        name='schema-json',
    ),
    url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

api = [
    url(r'^api/v1/', include('django_example.urls.v1', namespace='api.v1')),
]

urlpatterns = (
    [
        path(settings.ADMIN_PANEL_PATH + '/', admin.site.urls),
        # url(r'^accounts/', include('allauth.urls')),
        # url(r'^rest-auth/', include('rest_auth.urls')),
        # url(r'^rest-auth/registration/', include('rest_auth.registration.urls')),
        # url(r'^notification/', include('apps.notify.urls', namespace='notification')),
        # url(r'^devtools/', include('apps.devtools.urls', namespace='devtools')),
    ]
    + api
    + [path('pages/', include('django.contrib.flatpages.urls'))]
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    + docs_urlpatterns
)

if settings.DEBUG_TOOLBAR_ON:
    import debug_toolbar

    urlpatterns = [path('__debug__/', include(debug_toolbar.urls)),] + urlpatterns
