import random
import string
from nltk.corpus import wordnet
from PIL import Image
import numpy as np

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response

from accounts.permissions import IsAuthenticatedAdult, IsAuthenticatedChild
from accounts.models import ChildProfile, AdultProfile
from .serializers import *
from .models import *
from .apps import initialize_models, azure_client, groq_client, paddleOcr


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

# TODO save each letter score in the db in some way and update the child level
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
        # check if the exercise is already submitted - if so return 403 forbidden
        if exercise.submission_date is not None:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True) 
        submitted_image = serializer.validated_data["submitted_image"]
        exercise.submitted_image = submitted_image
        # TODO verify if automatically gets set to settings.py timezone
        exercise.submission_date = timezone.now()
        # since the image is sent as a file, we need to open it and convert it to a numpy array
        # then we can use PaddleOCR to extract the text from the image
        img = Image.open(submitted_image)
        img_np = np.array(img)
        # Image.open causes the file pointer to be at the end of the file so we need to get it back to the beginning
        submitted_image.seek(0)
        exercise.save()
        exercise.submitted_text = ""
        exercise.score = 0.0
        VLM_guess = ""
        VLM_answer = None
        # if any of the models is not initialized - try to initialize them again
        if groq_client is None or paddleOcr is None or azure_client is None:
            initialize_models()
        # if azure was initialized - use it as our first choice for a VLM model
        if azure_client:
            try:
                VLM_answer = azure_client.complete(
                    messages=[
                    {
                        "role": "user",
                        "content": [
                        {
                            "type": "text",
                            "text": "write(without any more words, separate between them with a new line without numbers): 1. the text in the image - exactly what you recognize(there can be words that don't exists) in one line, 2. analyze the handwriting for his parent(talk about Letter Foundation, Letter spacing and size, Line quality, slant and cursive joinings, and any other relevant details)"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                            "url": exercise.submitted_image.url
                            }
                        }
                        ],
                    },
                ],
                    temperature=0.5,
                    top_p=1.0,
                    model= "openai/gpt-4.1-mini"
                )
                print("Azure answered successfully")
            except Exception as e:
                print("Failed to recognize the text using the Azure model")
                print(e)
        
        if groq_client and VLM_guess is None:
            try:
                VLM_answer = groq_client.chat.completions.create(
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    # adding "I have requested a child to write the following text: " + exercise.requested_text
                                    # made the model to guess what he requested instead of the text in the image
                                    "text": "write(without any more words, separate between them with a new line without numbers): 1. the text in the image - exactly what you recognize(there can be words that don't exists) in one line, 2. analyze the handwriting for his parent(talk about Letter Foundation, Letter spacing and size, Line quality, slant and cursive joinings, and any other relevant details)"
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": exercise.submitted_image.url
                                    }
                                }
                            ]
                        }
                    ],
                    temperature=0.5,
                    max_tokens=200,
                    n=1,
                    stop=None
                )
                print("groq answered successfully")
            except Exception as e:
                print("Failed to recognize the text using the groq's VLM model")
                print(e)
        
        # if any of the models was able to guess the text
        if VLM_answer:
            VLM_answer_parts = VLM_answer.choices[0].message.content.split("\n")
            for i in range(len(VLM_answer_parts)):
                print(f"VLM answer part {i}: {VLM_answer_parts[i]}")
            VLM_guess = VLM_answer_parts[0]
            # the feedback is in the rest of the answer
            exercise.feedback = "\n".join(VLM_answer_parts[1:]).strip()
        
        if paddleOcr is not None:
            results = paddleOcr.ocr(img_np, cls=True)
            print("PaddleOCR results: ", results)
        if results[0] is not None or VLM_guess != "":
            print('\nDetected characters and their confidence score: ')
            # go over each letter expected
            # if the letter has been predicted correctly - add its confidence to the score
            # TODO only fitted for letters and words with requested_text - category needs to be handled differently
            # TODO what to do when more letters are detected than expected?
            # TODO what to do when the letters are detected in a different order than expected?
            # TODO should we iterate over the whole text or only with the length of the requested text?
            for i in range(len(exercise.requested_text)):
                VLM_char_guess = ''
                paddle_char_guess = ''
                char = ''
                char_conf = 0.0
                # The VLM guessed something for that letter
                if i < len(VLM_guess):
                        VLM_char_guess = VLM_guess[i]
                        print(f"The VLM detected: {VLM_char_guess}")
                        char_conf += 1.0 # can be played with - the idea is to give more weight to the VLM guess
                        # if the guess is correct - save it
                        if exercise.requested_text[i] == VLM_char_guess:
                            char = VLM_guess[i]
                # paddle guessed something for that letter
                if results[0] and i < len(results[0][0][1]):
                    paddle_char_guess = results[0][0][1][i][0]
                    print(f"PaddleOCR detected: {paddle_char_guess}")
                    # if the guess is correct - save it
                    if exercise.requested_text[i] == paddle_char_guess:
                        char = results[0][0][1][i][0]
                    # if both models guessed the same letter - add paddle confidence to the score
                    if VLM_char_guess == paddle_char_guess:
                        char_conf += results[1][i]
                    else:
                        char_conf -= results[1][i]
                        char_conf = max(char_conf, 0.0) # if the confidence is negative - set it to 0
                # avg of the two models confidence(if both guessed the same letter if not - 0.5)
                char_conf = char_conf / 2
                # the correct character was detected by one of the models - add its confidence to the score
                if char != '':
                    exercise.score += char_conf
                else:
                    # either models guessed correctly - add the char of the one that guessed something
                    # prefer VLM guess if it is not empty
                    char = VLM_char_guess if VLM_char_guess != '' else paddle_char_guess
                exercise.submitted_text += char
                print(f"Expected: {exercise.requested_text[i]}, Detected: {char}, with Confidence: {char_conf}")
        
        # average the score
        exercise.score = exercise.score / len(exercise.requested_text) if len(exercise.requested_text) > 0 else 0.0
        
        exercise.save()
        serializer = ExerciseSubmitSerializer(exercise)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExerciseRetrieveView(generics.RetrieveAPIView):
    serializer_class = ExerciseSerializer
    permission_classes = (IsAuthenticatedAdult, )
    queryset = Exercise.objects.all()
    
    def get(self, request, pk):
        # get the exercise object by its id(provided in the url - its pk - primary key)
        exercise = self.get_object()
        # check if the exercise belongs to a child of the current adult if not return 403 forbidden
        current_adult = AdultProfile.objects.get(user=request.user)
        if exercise.child.guiding_adult != current_adult:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(exercise)
        return Response(serializer.data, status=status.HTTP_200_OK)

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

