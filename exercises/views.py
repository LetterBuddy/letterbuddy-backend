import random
import string
from nltk.corpus import wordnet
from PIL import Image
import numpy as np
import re

from groq import Groq
from paddleocr import PaddleOCR
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Avg, Case, When, F, Value, FloatField
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from accounts.permissions import IsAuthenticatedAdult, IsAuthenticatedChild
from accounts.models import ChildProfile, AdultProfile
from .serializers import *
from .models import *

azure_client = None
groq_client = None
paddleOcr = None

def initialize_models():
    # if any of the models is not initialized - try to initialize them
    global groq_client, paddleOcr, azure_client
    print("Initializing models")
    if azure_client == None:
        try:
            azure_client = ChatCompletionsClient(
                endpoint='https://models.github.ai/inference',
                credential=AzureKeyCredential(settings.AZURE_TOKEN)
            )
        except Exception as e:
            print("Failed to initialize the Azure client")
            print(e)

    if groq_client == None:
        try:
            groq_client = Groq(api_key=settings.GROQ_API_KEY)
        except Exception as e:
            print("Failed to initialize the Groq client")
            print(e)

    if paddleOcr == None:
        try:
            paddleOcr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        except Exception as e:
            print("Failed to initialize the PaddleOCR client")
            print(e)

# get the models analysis for the exercise
def get_models_analysis(exercise):
    # if any of the models is not initialized - try to initialize them again
    if groq_client == None or paddleOcr == None or azure_client == None:
        initialize_models()
    VLM_answer = None
    if exercise.level == ChildProfile.ExerciseLevel.CATEGORY:
        VLM_prompt = f"""A child submitted this image, write(number the parts, without **):
                                1. only what he exactly wrote? (there can be words that do not exist).
                                2. only Can it be a word from the category '{exercise.category}' (maybe with typos)? Yes/no
                                3. only If yes then write only what word could it be?
                                4. analyze the handwriting for his parent (talk about Letter Foundation, Letter spacing and size, Line quality, slant and cursive joinings, and any other relevant details)"""
    else:
        VLM_prompt = "write(without any more words or **, number the parts): 1. the text in the image - exactly what you recognize(there can be words that don't exists) in one line, 2. analyze the handwriting for his parent(talk about Letter Foundation, Letter spacing and size, Line quality, slant and cursive joinings, and any other relevant details)"
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
                        "text": VLM_prompt
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
                max_tokens=100,
                model="openai/gpt-4.1-mini"
            )
            print("Azure answered successfully")
        except Exception as e:
            print("Failed to recognize the text using the Azure model")
            print(e)
    
    if groq_client and VLM_answer == None:
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
                                "text": VLM_prompt
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
                max_tokens=100,
                n=1,
                stop=None
            )
            print("groq answered successfully")
        except Exception as e:
            print("Failed to recognize the text using the groq's VLM model")
            print(e)

    VLM_guess = ""
    # if any of the models was able to guess the text
    if VLM_answer:
        # split the answer by numberings(like 1. 2. 3.)
        # TODO think about how to score a category exercise
        # Thought about giving half the score if the word is close to the requested category
        # and half for the distance between the guessed word and that word from the category
        VLM_answer_parts = re.split(r'\d+\.\s+', VLM_answer.choices[0].message.content.strip())[1:]
        VLM_answer_parts = [re.sub(r'\s+', ' ', part).strip() for part in VLM_answer_parts]
        for i in range(len(VLM_answer_parts)):
            print(f"VLM answer part {i}: {VLM_answer_parts[i]}")
        VLM_guess = VLM_answer_parts[0]
        # the feedback is the last part of the answer
        exercise.feedback = VLM_answer_parts[-1].strip()
    results = [None]
    # since the image is sent as a file, we need to open it and convert it to a numpy array
    # then we can use PaddleOCR to extract the text from the image
    submitted_image = exercise.submitted_image
    img = Image.open(submitted_image)
    img_np = np.array(img)
    # Image.open causes the file pointer to be at the end of the file so we need to get it back to the beginning
    submitted_image.seek(0)
    if paddleOcr != None:
        try:
            results = paddleOcr.ocr(img_np, cls=True)
        except Exception as e:
            print("Failed to recognize the text using the PaddleOCR model")
            print(e)
        print("PaddleOCR results: ", results)
    return VLM_guess, results

def score_exercise(exercise, VLM_guess, results):
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
            # TODO deal with the case when only one model guessed something for the whole word
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
        # save the letter score in the db
        SubmittedLetter.objects.create(
            exercise=exercise,
            submitted_letter=char,
            expected_letter=exercise.requested_text[i],
            score=char_conf,
            position=i
        )
        print(f"Expected: {exercise.requested_text[i]}, Detected: {char}, with Confidence: {char_conf}")
    
    # average the score
    exercise.score = exercise.score / len(exercise.requested_text) if len(exercise.requested_text) > 0 else 0.0

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
        save_submission_date = timezone.now()
        submitted_image = serializer.validated_data["submitted_image"]
        exercise.submitted_image = submitted_image
        exercise.save()
        exercise.submitted_text = ""
        exercise.score = 0.0
        VLM_guess, results = get_models_analysis(exercise)

        # if any of the models was able to guess the text
        if results[0] != None or VLM_guess != "":
            score_exercise(exercise, VLM_guess, results)
        
        exercise.submission_date = save_submission_date
        exercise.save()
        serializer = ExerciseSubmitSerializer(exercise)
        
        # update the child level - based on the avg score of all the exercises in his current level
        current_child = exercise.child
        avg_score = Exercise.objects.filter(child=current_child, level=current_child.exercise_level).aggregate(Avg('score'))['score__avg']
        print(f"Avg score for child {current_child.user.username} in level {current_child.exercise_level}: {float(avg_score):.4f}")
        # if the avg score is above 0.7 - move the child to the next level
        # TODO lower the level if the avg score in the current level is low
        if avg_score >= 0.7:
            print(f"Child {current_child.user.username} has reached the next level")
            current_child.exercise_level = ChildProfile.get_next_level(current_child.exercise_level)
            current_child.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

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
            requested_text = ""
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
                        if "_" not in requested_text and " " not in requested_text and "-" not in requested_text:
                            break

            exercise = Exercise.objects.create(child=current_child, requested_text=requested_text, level=current_child_level, category=category)
            response_status = status.HTTP_201_CREATED
        else:
            response_status = status.HTTP_200_OK
        serializer = ExerciseGenerationSerializer(exercise)
        return Response(serializer.data, status=response_status)


# TODO maybe add what letters get confused with what letters
class LetterStatsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticatedAdult, ]

    def get(self, request, pk):
        child = get_object_or_404(ChildProfile, pk=pk)
        # check if the child belongs to the current adult if not return 403 forbidden
        current_adult = AdultProfile.objects.get(user=request.user)
        if child.guiding_adult != current_adult:
            return Response(status=status.HTTP_403_FORBIDDEN)
        # return the avg score of the child in each letter
        # values - group by the letter
        # the first annotate - if the letter was guessed correctly - add its score to the avg score else 0
        letter_scores = (SubmittedLetter.objects.filter(exercise__child=child).annotate(
                guessing_score=Case(
                    When(expected_letter=F('submitted_letter'), then=F('score')),
                    default=Value(0.0),
                    output_field=FloatField()
                )
            ).values('expected_letter').annotate(letter=F('expected_letter'), avg_score=Avg('guessing_score'))
            .values('letter', 'avg_score').order_by('letter'))
        return Response(letter_scores, status=status.HTTP_200_OK)
    
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

