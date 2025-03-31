from rest_framework import serializers
from .models import *


class ExerciseGenerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ('requested_text', 'level', 'category', 'child')
        # the exercise object will be created with these fields, and not required to be passed in the request
        read_only_fields = ('requested_text', 'level', 'category', 'child')


class ArticleSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Article
        fields = '__all__'

