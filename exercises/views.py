import random
import string
from nltk.corpus import wordnet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from accounts.permissions import IsAuthenticatedAdult, IsAuthenticatedChild
from accounts.models import ChildProfile, AdultProfile
from .serializers import *
from .models import *


class ExerciseGenerationView(generics.GenericAPIView):
    serializer_class = ExerciseGenerationSerializer
    permission_classes = (IsAuthenticatedChild, )
    def post(self, request):
        current_child = ChildProfile.objects.get(user=request.user)
        # check if the child already has an exercise that is not submitted - if so return it
        exercise = Exercise.objects.filter(child=current_child, submission_date=None).first()
        # if there isn't one - create a new one
        if not exercise:
            current_child_level = current_child.exercise_level
            requested_text = None
            category = None
            if current_child_level == ChildProfile.ExerciseLevel.LETTERS:
                # choose a random letter from the alphabet and duplicate it
                requested_text = random.choice(string.ascii_letters)
                requested_text = requested_text * random.randint(3, 8)

            else:
                category = random.choice([choice[0] for choice in Exercise.ExerciseCategory.choices])
                # choose a random word from the chosen category from wordnet
                if current_child_level == ChildProfile.ExerciseLevel.WORDS:
                    synsets = wordnet.synsets(category)
                    hyponyms = []
                    for synset in synsets:
                        hyponyms.extend(synset.hyponyms())
                    while True:
                        random_hyponym = random.choice(hyponyms)
                        requested_text = random.choice(random_hyponym.lemmas()).name()
                        print(requested_text)
                        if "_" not in requested_text and " " not in requested_text and "-" not in requested_text:
                            break

            exercise = Exercise.objects.create(child=current_child, requested_text=requested_text, level=current_child_level, category=category)
        serializer = ExerciseGenerationSerializer(exercise)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ExerciseSubmissionView(generics.GenericAPIView):
    # queryset will tell get_object which model to look for
    queryset = Exercise.objects.all()
    serializer_class = ExerciseSubmitSerializer
    permission_classes = (IsAuthenticatedChild, )
    
    def put(self, request, pk):
        # get the exercise object by its id(provided in the url - its pk - primary key)
        exercise = self.get_object()
        # check if the exercise belongs to the current child if not return 403 forbidden
        if exercise.child.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True) 
        submitted_image = serializer.validated_data["submitted_image"]
        exercise.submitted_image = submitted_image
        # TODO verify if automatically gets set to settings.py timezone
        exercise.submission_date = timezone.now()
        exercise.score = 0.0
        # TODO calculate the score and submitted_text based on OCR's validation
        exercise.save()
        serializer = ExerciseSubmitSerializer(exercise)
        return Response(serializer.data, status=status.HTTP_200_OK)

# both retrieve and delete methods are implemented in the same view - so they could be in the same path
class ExerciseRetrieveDeleteView(generics.RetrieveDestroyAPIView):
    serializer_class = ExerciseSerializer
    queryset = Exercise.objects.all()

    def get_permissions(self):
        # if the request is a delete request - only authenticated children can access it
        if self.request.method == 'DELETE':
            return [IsAuthenticatedChild()]
        # if the request is a get request - only authenticated adults can access it
        elif self.request.method == 'GET':
            return [IsAuthenticatedAdult()]
        return super().get_permissions()
     
    def get_object(self):
        exercise = super().get_object()
        if self.request.method == 'DELETE':
            # check if the exercise belongs to the current child if not return 403 forbidden
            if exercise.child.user != self.request.user or exercise.submission_date is not None:
                raise PermissionDenied("You are not allowed to delete this exercise.")
        elif self.request.method == 'GET':
            # check if the exercise belongs to a child of the current adult if not return 403 forbidden
            current_adult = AdultProfile.objects.get(user=self.request.user)
            if exercise.child.guiding_adult != current_adult:
                raise PermissionDenied("You are not allowed to retrieve this exercise.")
        return exercise
    
class SubmissionListOfChildView(generics.ListAPIView):
    serializer_class = SubmissionListSerializer
    permission_classes = (IsAuthenticatedAdult, )

    def get(self, request, *args, **kwargs):
        # get the child object by its id(provided in the url - its pk - primary key)
        # since ChildProfile isn't the queryset of the view, we need to get it manually
        # also ListAPIView doesn't have a get_object method
        child = get_object_or_404(ChildProfile, pk=self.kwargs['pk'])
        # check if the child belongs to the current adult if not return 403 forbidden
        current_adult = AdultProfile.objects.get(user=self.request.user)
        if child.guiding_adult != current_adult:
            return Response(status=status.HTTP_403_FORBIDDEN)
        # return all the exercises of the child that were not submitted
        exercises = Exercise.objects.filter(child=child).exclude(submission_date=None)
        serializer = self.get_serializer(exercises, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ArticlesView(generics.ListAPIView):
    serializer_class = ArticleSerializer
    permission_classes = (IsAuthenticatedAdult, )
    queryset = Article.objects.all()

