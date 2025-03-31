import random
from nltk.corpus import wordnet
from rest_framework import generics, status
from rest_framework.response import Response

from accounts.permissions import IsAuthenticatedAdult, IsAuthenticatedChild
from accounts.models import ChildProfile
from .serializers import *
from .models import *


class ExerciseGenerationView(generics.GenericAPIView):
    serializer_class = ExerciseGenerationSerializer
    permission_classes = (IsAuthenticatedChild, )
    def post(self, request):
        current_child = ChildProfile.objects.get(user=request.user)
        current_child_level = current_child.exercise_level
        requested_text = None
        category = None
        if current_child_level == ChildProfile.ExerciseLevel.LETTERS:
            # TODO generate a random letter from the alphabet
            requested_text = "aaaaaa"

        else:
            category = random.choice([choice[0] for choice in Exercise.ExerciseCategory.choices])
            # choose a random word from the chosen category from wordnet
            if current_child_level == ChildProfile.ExerciseLevel.WORDS:
                synsets = wordnet.synsets(category)
                hyponyms = []
                for synset in synsets:
                    hyponyms.extend(synset.hyponyms())
                random_hyponym = random.choice(hyponyms)
                requested_text = random.choice(random_hyponym.lemmas()).name()

        exercise = Exercise.objects.create(child=current_child, requested_text=requested_text, level=current_child_level, category=category)
        serializer = ExerciseGenerationSerializer(exercise)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        

class ArticlesView(generics.ListAPIView):
    serializer_class = ArticleSerializer
    permission_classes = (IsAuthenticatedAdult, )
    queryset = Article.objects.all()

