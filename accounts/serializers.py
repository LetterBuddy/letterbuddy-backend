from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import *


# base user serializer - used for both adult and child registration
class BaseUserRegisterSerializer(serializers.ModelSerializer):
    # specify the fields in the request so there is validation
    id = serializers.IntegerField(read_only=True)
    
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
        fields = ('id', 'username', 'password', 'first_name', 'last_name')
        
        # these fields aren't required in the model, but are required in this request
        # extra_kwargs helps to make these small changes to the fields
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    def create_user(self, validated_data, role):
        user = User.objects.create_user(
            role = role, # role is passed from the child or adult register serializer
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data.get('email', ''), # email will only be for adults
            username=validated_data['username'],
            password=validated_data['password']
        )
        user.save()
        return user

# exteneds the base user serializer
class AdultRegisterSerializer(BaseUserRegisterSerializer):

    # technically email isn't unique in the User model, made it unique here
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())])
    

    class Meta(BaseUserRegisterSerializer.Meta):
        fields = BaseUserRegisterSerializer.Meta.fields + ('email',)
    
    def create(self, validated_data):
        user = self.create_user(validated_data, User.Role.ADULT)
        adult = AdultProfile.objects.create(user=user)
        adult.save()
        return user


class ChildRegisterSerializer(BaseUserRegisterSerializer):
    exercise_level = serializers.ChoiceField(
        choices=ChildProfile.ExerciseLevel.choices, default='letters'
    )
    
    class Meta(BaseUserRegisterSerializer.Meta):
        fields = BaseUserRegisterSerializer.Meta.fields + ('exercise_level',)

    def create(self, validated_data):
        user = self.create_user(validated_data, User.Role.CHILD)
        request = self.context.get("request")
        guiding_adult = AdultProfile.objects.get(user=request.user)
        child = ChildProfile.objects.create(
            user=user,
            guiding_adult=guiding_adult,
            exercise_level=validated_data['exercise_level']
        )
        child.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'role')
        # will only show when retrieving the user
        extra_kwargs = {
            'id': {'read_only': True},
            'role': {'read_only': True},
        }

class ChildSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    class Meta:
        model = ChildProfile
        fields = ('user', 'exercise_level')
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        user = representation.pop('user')
        
        for key, value in user.items():
            representation[key] = value
        
        return representation


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    
class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        return super().get_token(user)
    
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data['role'] = user.role
        data['first_name'] = user.first_name
        data['last_name'] = user.last_name
        return data
    
    
        