from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response

from apps.profiles.models import Profile
from apps.profiles.permissions import IsProfileOwner
from apps.profiles.serializers import GetUpdateProfileSerializer


class ProfileView(RetrieveUpdateAPIView):
    """
    Получить/обновить данные профиля

    GET - получить
    PUT - обновить полностью запись о профиле
    PATCH - обновить запись частично
    Доступна только для владельца профиля
    """

    serializer_class = GetUpdateProfileSerializer
    permission_classes = (IsProfileOwner,)
    queryset = Profile.objects.all()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer: GetUpdateProfileSerializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        print(f"{serializer.validated_data=}")
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        print(f"{serializer.data=}")
        return Response(serializer.data)
