from rest_framework import permissions


class IsProfileOwner(permissions.IsAuthenticated):
    """
    Allows access only to authenticated profile owner.
    """

    def has_object_permission(self, request, view, obj):
        # Write permissions are only allowed to the user, associated with profile
        is_auth = super(IsProfileOwner, self).has_object_permission(request, view, obj)
        return is_auth and obj.user == request.user


class IsPatient(permissions.IsAuthenticated):
    """
    Allows access only to authenticated contractor.
    """

    def has_permission(self, request, view):
        is_auth = super(IsPatient, self).has_permission(request, view)
        return is_auth and request.user.profile and request.user.profile.is_patient


class IsDoctor(permissions.IsAuthenticated):
    """
    Allows access only to authenticated contractor.
    """

    def has_permission(self, request, view):
        is_auth = super(IsDoctor, self).has_permission(request, view)
        return is_auth and request.user.profile and request.user.profile.is_doctor
