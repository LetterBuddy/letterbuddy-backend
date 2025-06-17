from rest_framework import serializers
from django.db.models import Case, When, Value, F
from django.db.models import FloatField
from .models import *


class ExerciseGenerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ('id', 'requested_text', 'level', 'category')
        # the exercise object will be created with these fields
        # but they are not required to be passed in the request
        read_only_fields = ('id', 'requested_text', 'level', 'category')

class ExerciseSubmitSerializer(serializers.ModelSerializer):
    letter_scores = serializers.SerializerMethodField()
    class Meta:
        model = Exercise
        fields = ('submitted_text', 'requested_text', 'submitted_image', 'submission_date', 'score', 'feedback', 'letter_scores')
        read_only_fields = ('submitted_text', 'requested_text', 'submission_date', 'score', 'feedback', 'letter_scores')
    def get_letter_scores(self, obj):
        # an array of the scores for each letter by position
        return list(SubmittedLetter.objects
                    .filter(exercise=obj)
                    .order_by('position')
                    .annotate(
                            new_score=Case(
                                When(submitted_letter=F('expected_letter'), then = 1 - F('score')),
                                default=Value(1),
                                output_field=FloatField()
                            )).values_list('new_score', flat=True))

class ExerciseSerializer(serializers.ModelSerializer):
    letter_scores = serializers.SerializerMethodField()
    class Meta:
        model = Exercise
        fields = '__all__'
    
    def get_letter_scores(self, obj):
        # an array of the scores for each letter by position
        scores = list(
            SubmittedLetter.objects
            .filter(exercise=obj)
            .order_by('position')
            .annotate(
                new_score=Case(
                    When(submitted_letter=F('expected_letter'), then=F('score')),
                    default=Value(0),
                    output_field=FloatField()
                )).values_list('new_score', flat=True))
        return scores

class ExerciseStatsSerializer(serializers.Serializer):
    letter_scores = serializers.ListField()
    level_scores = serializers.ListField()
    daily_scores = serializers.ListField()
    often_confused_letters = serializers.ListField()



class SubmissionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ('id', 'level', 'submission_date', 'requested_text', 'score', 'category')

class ArticleSerializer(serializers.ModelSerializer):
    class Meta: 
        model = Article
        fields = '__all__'

