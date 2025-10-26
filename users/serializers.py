from rest_framework import serializers
from .models import RegistrationLink

class RegistrationLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistrationLink
        fields = '__all__'

class UserSerializer(serializers.Serializer):
    user = serializers.CharField(max_length=128)

class LinkSerializer(serializers.Serializer):
    cognito_link = serializers.URLField()