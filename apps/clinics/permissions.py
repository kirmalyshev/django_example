from rest_framework import permissions

from apps.profiles.models import Relation


class IsRelationMaster(permissions.IsAuthenticated):
    """
    Allows access only to authenticated profile owner.
    """

    def has_object_permission(self, request, view, obj: Relation):
        # Write permissions are only allowed to the user, associated with profile
        is_auth = super(IsRelationMaster, self).has_object_permission(request, view, obj)
        return is_auth and obj.master_id == request.user.profile.id
