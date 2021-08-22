from rest_framework import serializers

from apps.profiles.serializers import PhoneField
from apps.support import models


class SupportRequestSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    phone = PhoneField(required=False)
    text = serializers.CharField(required=True)

    class Meta:
        model = models.SupportRequest
        fields = ('id', 'email', 'phone', 'text')
        read_only_fields = ('id',)


class FrequentQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FrequentQuestion
        read_only_fields = fields = ('id', 'question', 'answer')
