# encoding=utf-8

from __future__ import print_function
from __future__ import unicode_literals

from rest_framework import permissions
from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle

from apps.core.constants import SYSTEM_SERVICE, SystemUserNames


class IsSystemService(permissions.IsAuthenticated):
    """
    A DRF permission to check if the remote user is in System Services group
    (reserved for remotely-talking services like message-server)
    """

    def has_permission(self, request, view):
        is_auth = super(IsSystemService, self).has_permission(request, view)
        return is_auth and request.user.groups.filter(name=SYSTEM_SERVICE).exists()


class IsSystemServiceUser(IsSystemService):
    """
    Allows access only to specified service user.

    >>> class MyPermission(IsSystemServiceUser):
    ...     username = "username@django_example.com"
    """

    username = None

    def has_permission(self, request, view):
        assert self.username

        return (
            super(IsSystemServiceUser, self).has_permission(request, view)
            and request.user.username == self.username
        )


class IsIntegrationUser(IsSystemServiceUser):
    username = SystemUserNames.INTEGRATION


class IsAnonymous(permissions.BasePermission):
    """
    Allows access only to anonymus.
    """

    def has_permission(self, request, *args, **kwargs):
        user = request.user
        return user.is_anonymous


class ResendCodeThrottle(SimpleRateThrottle):
    def __init__(self, contact_type, *args, **kwargs):
        self.scope = 'resend_code_{}'.format(contact_type)
        super(ResendCodeThrottle, self).__init__(*args, **kwargs)

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': request.user.id}


class FeedbackEmailThrottle(UserRateThrottle):
    scope = 'feedback_email'

    def parse_rate(self, rate):
        return (1, 10 * 60)


class UniqueResourceThrottle(SimpleRateThrottle):
    """
    Throttle unique resource access.
    View class should have `throttle_resource_rate` and unique `throttle_resource_name` set.
    User identity is not checked, anyone accessing the unique resource will deplete the limit.

    Usage example:

    class OrderConfirmView(GenericAPIView):
        lookup_url_kwarg = 'order_id'
        throttle_classes = (UniqueResourceThrottle,)
        throttle_resource_name = 'order_confirm'
        throttle_resource_rate = '3/hour'
    """

    scope_attr = 'throttle_resource_name'
    scope_rate_attr = 'throttle_resource_rate'

    def allow_request(self, request, view):
        # We can only determine the scope once we're called by the view.
        self.scope = getattr(view, self.scope_attr, None)
        self.rate = getattr(view, self.scope_rate_attr, None)
        self.num_requests, self.duration = self.parse_rate(self.rate)
        # If a view does not have scope attributes, always allow the request
        if not self.scope:
            return True
        return super(UniqueResourceThrottle, self).allow_request(request, view)

    def get_rate(self):
        pass

    def get_cache_key(self, request, view):
        resource_id = request.resolver_match.kwargs.get(view.lookup_url_kwarg)
        cache_key = self.cache_format % {'scope': self.scope, 'ident': resource_id}
        return cache_key
