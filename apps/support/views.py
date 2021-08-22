from django.conf import settings
from django.core.mail import send_mail
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import AllowAny

from apps.core.admin import get_change_url
from apps.core.utils import make_absolute_url
from apps.support.models import FrequentQuestion
from apps.support.serializers import SupportRequestSerializer, FrequentQuestionSerializer


class SupportRequestView(CreateAPIView):
    """
    Создать обращение в саппорт
    """

    serializer_class = SupportRequestSerializer
    permission_classes = (AllowAny,)
    throttle_scope = "create_support_request"

    def perform_create(self, serializer: serializer_class):
        data = serializer.validated_data
        email = data.get('email')
        text = data.get('text')
        phone = data.get('phone', None)
        user = self.request.user
        user_to_save = None
        if user.is_authenticated and user.is_patient:
            user_to_save = user
            if not phone:
                phone = user.phone or None

        obj = serializer.save(user=user_to_save)
        obj_url = make_absolute_url(get_change_url(obj))
        subject = f'{settings.SHORT_PREFIX}: Обращение в саппорт'
        message = f"Email: {email}\nТелефон: {phone}\n\n{text}\n\n{obj_url}"
        send_mail(subject, message, settings.SYSTEM_SENDER_EMAIL, [settings.FAQ_SUPPORT_EMAIL])


class FAQListView(ListAPIView):
    serializer_class = FrequentQuestionSerializer
    queryset = FrequentQuestion.objects.displayed()
