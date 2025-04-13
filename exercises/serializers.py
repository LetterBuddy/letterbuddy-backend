from rest_framework import serializers
from .models import *


class ExerciseGenerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ('id', 'requested_text', 'level', 'category')
        # the exercise object will be created with these fields
        # but they are not required to be passed in the request
        read_only_fields = ('id', 'requested_text', 'level', 'category')

class ExerciseSubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ('submitted_text', 'submitted_image', 'submission_date', 'score')
        read_only_fields = ('submitted_text', 'submission_date', 'score',)

class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = '__all__'

class SubmissionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ('id', 'level', 'submission_date', 'requested_text', 'score')

class ArticleSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Article
        fields = '__all__'

