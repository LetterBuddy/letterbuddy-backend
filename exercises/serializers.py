from rest_framework import serializers
from .models import *


class ExerciseGenerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ('child', 'requested_text', 'level', 'category')
        # the exercise object will be created with these fields
        # but they are not required to be passed in the request
        read_only_fields = ('child', 'requested_text', 'level', 'category')

class ExerciseSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ('submitted_text', 'submitted_image', 'submission_date', 'score')
        read_only_fields = ('submitted_text', 'submission_date', 'score',)


class ArticleSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Article
        fields = '__all__'

