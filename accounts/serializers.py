from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password
from .models import *

class AdultRegisterSerializer(serializers.ModelSerializer):
    # specify the fields in the request so there is validation

    # technically email isn't unique in the model, made it unique here
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())])
    
    username = serializers.CharField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())])
    
    # write_only - so that the password won't show in the response
    password = serializers.CharField(
        write_only=True, required=True, 
        validators=[validate_password]) # password validation according to AUTH_PASSWORD_VALIDATORS in settings
    
    class Meta:
        model = User
        # fields that will be shown in the response and in the request
        fields = ('email', 'username', 'password', 'first_name', 'last_name')
        # these fields aren't required in the model, but are required in this request
        # extra_kwargs helps to make these small changes to the fields
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def create(self, validated_data):
        user = User.objects.create_user(
            role = User.Role.ADULT,
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password']
        )
        adult = AdultProfile.objects.create(user=user)
        adult.save()
        user.save()
        return user
    
class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()