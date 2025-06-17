from collections import defaultdict
import random
import string
from PIL import Image
import numpy as np
import re
from difflib import SequenceMatcher
import Levenshtein

from groq import Groq
from paddleocr import PaddleOCR
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Avg, Case, When, F, Value, FloatField, Count, Func
from django.db.models.functions import TruncDate
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from accounts.permissions import IsAuthenticatedAdult, IsAuthenticatedChild
from accounts.models import ChildProfile, AdultProfile
from .serializers import *
from .models import *


HANDWRITTEN_CONFUSING_LETTER_PAIRS = [
    ('b', 'd'), ('b', 'p'), ('b', 'q'), ('d', 'g'), ('d', 'q'),
    ('e', 'a'), ('g', 'a'), ('g', 'y'), ('i', 'j'), ('i', 'l'),
    ('k', 'x'), ('m', 'n'), ('n', 'c'), ('n', 'h'), ('p', 'q'),
    ('u', 'v'), ('u', 'w'), ('u', 'y'), ('w', 'm'), ('y', 'v'),
    ('C', 'c'), ('K', 'k'), ('O', 'o'), ('P', 'p'), ('S', 's'),
    ('U', 'u'), ('V', 'v'), ('W', 'w'), ('X', 'x'), ('Y', 'y'),
    ('l', 'I'), ('O', 'Q'), ('f', 'F'), ('z', 'Z'), ('q', 'a')
]

# build a two way map of visually confusing letters
LETTERS_CONFUSION_MAP = defaultdict(set)
for a, b in HANDWRITTEN_CONFUSING_LETTER_PAIRS:
    LETTERS_CONFUSION_MAP[a].add(b)
    LETTERS_CONFUSION_MAP[b].add(a)


azure_client = None
groq_client = None
paddleOcr = None

def initialize_models():
    # if any of the models is not initialized - try to initialize them
    global groq_client, paddleOcr, azure_client
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
       VLM_prompt = f"""
                    A child submitted this image. Please follow the instructions exactly. 
                    Do NOT explain your answers. ONLY output what is requested. Do not add arrows, symbols, or comments.
                    Number the parts clearly
                    1. What did the child write exactly? Transcribe ALL the visible words or text the child wrote, in order, even if the words are misspelled or made-up. Do NOT correct them. Do NOT skip any. Do NOT explain.
                    2. Could it be a word from the category '{exercise.category}' (possibly with typos)? Answer only "Yes" or "No".
                    3. If yes, what is the corrected word? Write ONLY the single corrected word. Do NOT show the original. Do NOT explain.
                    4. Provide an analysis of the handwriting for the parent. Discuss:
                    - Letter formation
                    - Spacing and size
                    - Line quality
                    - Any other relevant features
                    """
    elif exercise.level == ChildProfile.ExerciseLevel.WORDS:
        VLM_prompt = f"""
                    A child submitted this image. Please follow the instructions exactly. 
                    Do NOT explain your answers. ONLY output what is requested. Do not add arrows, symbols, or comments.
                    Number the parts clearly
                    1. What did the child write exactly? Transcribe ALL the visible words or text the child wrote, in order, even if the words are misspelled or made-up. Do NOT correct them. Do NOT skip any. Do NOT explain.
                    2. Provide an analysis of the handwriting for the parent. Discuss:
                    - Letter formation
                    - Spacing and size
                    - Line quality
                    - Any other relevant features
                    """
    elif exercise.level == ChildProfile.ExerciseLevel.LETTERS:
        VLM_prompt = f"""
                    A child submitted this image. Please follow the instructions exactly. 
                    Do NOT explain your answers. ONLY output what is requested. Do not add arrows, symbols, or comments.
                    Number the parts clearly

                    1. What is written in the image — transcribe the text *exactly* as it appears.
                    - The child only writes alphabetic characters (A–Z or a–z). There are no numbers, punctuation, or special symbols.
                    - This includes case changes *within words* (e.g., "hElLo" must be transcribed exactly like that).
                    - DO NOT normalize capitalization — this is critical.
                    - Ignore spaces between repeated letters (e.g., "A A A" → "AAA").

                    2. Provide an analysis of the handwriting for the parent. Discuss:
                    - Letter formation
                    - Spacing and size
                    - Line quality
                    - Any other relevant features
                    """
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
                max_tokens=150,
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
                max_tokens=150,
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
        # Thought about giving half the score if the word is close to the requested category
        # and half for the distance between the guessed word and that word from the category
        VLM_answer_parts = re.split(r'\d+\.\s+', VLM_answer.choices[0].message.content.strip())[1:]
        VLM_answer_parts = [re.sub(r'\s+', ' ', part).strip() for part in VLM_answer_parts]
        for i in range(len(VLM_answer_parts)):
            print(f"VLM answer part {i}: {VLM_answer_parts[i]}")
        if len(VLM_answer_parts) > 0:
            VLM_guess = VLM_answer_parts[0]
            # the feedback is the last part of the answer
            exercise.feedback = VLM_answer_parts[-1].strip()
            if exercise.level == ChildProfile.ExerciseLevel.CATEGORY:
                # if the second part is "yes" - it means that the word is from that category
                if len(VLM_answer_parts) > 1 and VLM_answer_parts[1].lower() == "yes":
                    # if it is close to a word from the category - will we want to see how close it is
                    exercise.requested_text = VLM_answer_parts[2].strip().split(" ")[0]
                elif len(VLM_answer_parts) > 1 and VLM_answer_parts[1].lower() == "no":
                    # if the second part is "no" - it means that the word is not from that category
                    exercise.submitted_text = VLM_guess
    results = [None]
    # if the exercise is a category exercise, but the VLM didn't think it is a word from that category - no need to use PaddleOCR
    if exercise.submitted_text == "":
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


def compare_expected_with_recognized(expected, recognized, scores):
    matcher = SequenceMatcher(None, expected, recognized)
    ops = matcher.get_opcodes()
    results = []
    for tag, i1, i2, j1, j2 in ops:
        if tag == 'equal':
            for i in range(i1, i2):
                results.append((expected[i], recognized[j1 + (i - i1)], scores[j1 + (i - i1)]))
        elif tag == 'replace':
            for i in range(i1, i2):
                recognized_char = recognized[j1 + (i - i1)] if j1 + (i - i1) < len(recognized) else ''
                recognized_score = scores[j1 + (i - i1)] if j1 + (i - i1) < len(scores) else 0.0
                results.append((expected[i], recognized_char, recognized_score))
        elif tag == 'delete':
            for i in range(i1, i2):
                results.append((expected[i], '', 0.0))
    
    return results

def score_exercise(exercise, VLM_guess, paddleocr_analysis):
    print('\nDetected characters and their confidence score: ')
    expected_text = exercise.requested_text
    VLM_comparison = compare_expected_with_recognized(exercise.requested_text, VLM_guess, [1.0] * len(VLM_guess))
    paddleocr_text = ''.join([paddleocr_analysis[0][0][1][i][0] for i in range(len(paddleocr_analysis[0][0][1]))] if paddleocr_analysis[0] else [])
    paddleocr_scores = [paddleocr_analysis[1][i] for i in range(len(paddleocr_analysis[1]))] if paddleocr_analysis and len(paddleocr_analysis) > 1  else []
    print(f"VLM guess: {VLM_guess}, PaddleOCR text: {paddleocr_text}, PaddleOCR scores: {paddleocr_scores}")
    paddleocr_comparison = compare_expected_with_recognized(exercise.requested_text, paddleocr_text, paddleocr_scores)
    print(f"PaddleOCR comparison: {paddleocr_comparison}")
    print(f"VLM comparison: {VLM_comparison}")
    # evaluation for debugging
    evaluation = []
    avg_correctly_guessed_score = 0.0
    for i in range(len(expected_text)):
        VLM_char = VLM_comparison[i][1]
        VLM_score = VLM_comparison[i][2] 
        paddleocr_char = paddleocr_comparison[i][1]
        paddleocr_score = paddleocr_comparison[i][2]
        current_char_score = 0.0
        submitted_char = ''
        expected_char = expected_text[i]
        if VLM_char == paddleocr_char and VLM_char != '':
            submitted_char = VLM_char
            current_char_score = VLM_score * 0.7 + paddleocr_score * 0.3
        # the models recognized different chars - if one is correct, use it and take into account that only one model is correct
        elif VLM_char == expected_char:
            submitted_char = VLM_char
            current_char_score = (1 - paddleocr_score * 0.3) if paddleocr_score != 0 else 0.7
        elif paddleocr_char == expected_char:
            submitted_char = paddleocr_char
            current_char_score = paddleocr_score * 0.3
        # no model recognized the expected char - use VLM if it is not empty, otherwise use PaddleOCR
        elif VLM_char != '':
            submitted_char = VLM_char
            current_char_score = (1 - paddleocr_score * 0.3) if paddleocr_score != 0 else 0.7
        elif paddleocr_char != '':
            submitted_char = paddleocr_char
            current_char_score = paddleocr_score * 0.3
        
        # the correct character was detected by one of the models - add its confidence to the score
        if submitted_char == expected_char:
            avg_correctly_guessed_score += current_char_score
        elif submitted_char in LETTERS_CONFUSION_MAP.get(expected_char, set()):
            # if the submitted char is often confused with the expected char - make it contribute to the score
            avg_correctly_guessed_score += (0.5 * current_char_score)
        
        evaluation.append((expected_char, submitted_char, current_char_score))

        exercise.submitted_text += submitted_char
        # save the letter score in the db
        SubmittedLetter.objects.create(
            exercise=exercise,
            submitted_letter=submitted_char,
            expected_letter=expected_char,
            score=current_char_score,
            position=i
        )
        print(f"Expected: {expected_char}, Detected: {submitted_char}, with Confidence: {current_char_score}")
    # average the score
    print("Evaluation of the exercise: ", evaluation)
    avg_correctly_guessed_score /= len(expected_text) if len(expected_text) > 0 else 1.0
    VLM_levenshtein_ratio = Levenshtein.ratio(expected_text, VLM_guess) if VLM_guess else 0.0
    paddleocr_levenshtein_ratio = Levenshtein.ratio(expected_text, paddleocr_text) if paddleocr_text else 0.0
    levenshtein_ratio = max(VLM_levenshtein_ratio, paddleocr_levenshtein_ratio)
    exercise.score = (avg_correctly_guessed_score + levenshtein_ratio) / 2
    print("submitted: " + exercise.submitted_text + " Average score:", avg_correctly_guessed_score, "Levenshtein ratio:", levenshtein_ratio, "Final score:", exercise.score)

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
        
        current_child = exercise.child
        # get the last 10 exercises of the child
        recent_exercises = (Exercise.objects.filter(child=current_child).order_by('-submission_date')[:10])
        # make sure that the last 10 exercises were in the current level
        recent_current_level_exercises = [ex for ex in recent_exercises if ex.level == current_child.exercise_level]
        print(f"Child {current_child.user.username} has done {len(recent_current_level_exercises)} exercises recently in his current level {current_child.exercise_level}")
        if len(recent_current_level_exercises) == 10:
            # if there are 10 exercises in the current level - calculate their avg score
            avg_score = sum(float(ex.score) for ex in recent_current_level_exercises) / 10.0
            print(f"Avg score for child {current_child.user.username} in level {current_child.exercise_level} (the last 10 ex): {float(avg_score):.4f}")
            # if the avg score is above 0.7 - move the child to the next level
            if avg_score >= 0.7:
                print(f"Child {current_child.user.username} has reached the next level")
                current_child.exercise_level = ChildProfile.get_next_level(current_child.exercise_level)
                current_child.save()
            elif avg_score <= 0.3:
                print(f"Child {current_child.user.username} has been lowered to the previous level")
                current_child.exercise_level = ChildProfile.get_previous_level(current_child.exercise_level)
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
                # choose a random word from the chosen category from the categorized words
                if current_child_level == ChildProfile.ExerciseLevel.WORDS:
                    requested_text = random.choice(
                        CategorizedWord.objects.filter(category=category).values_list('word', flat=True)
                    )

            exercise = Exercise.objects.create(child=current_child, requested_text=requested_text, level=current_child_level, category=category)
            response_status = status.HTTP_201_CREATED
        else:
            response_status = status.HTTP_200_OK
        serializer = ExerciseGenerationSerializer(exercise)
        return Response(serializer.data, status=response_status)


class ExerciseStatsView(generics.GenericAPIView):
    permission_classes = [IsAuthenticatedAdult, ]
    serializer_class = ExerciseStatsSerializer
    def get(self, request, pk):
        # in order to round the avg scores to 2 decimal places
        class Round2(Func):
            function = 'ROUND'
            template = '%(function)s(%(expressions)s, 2)'
        
        child = get_object_or_404(ChildProfile, pk=pk)
        # check if the child belongs to the current adult if not return 403 forbidden
        current_adult = AdultProfile.objects.get(user=request.user)
        if child.guiding_adult != current_adult:
            return Response(status=status.HTTP_403_FORBIDDEN)
        # the avg score of the child in each letter
        # values - group by the letter
        # the first annotate - if the letter was guessed correctly - add its score to the avg score else 0
        letter_scores = (SubmittedLetter.objects.filter(exercise__child=child).annotate(
                guessing_score=Case(
                    When(expected_letter=F('submitted_letter'), then=F('score')),
                    default=Value(0.0),
                    output_field=FloatField()
                )
            ).values('expected_letter').annotate(letter=F('expected_letter'), avg_score=100 * Round2(Avg('guessing_score'))
            ).values('letter', 'avg_score').order_by('letter'))
        
        # the avg score of the child in each level
        level_scores = (
            Exercise.objects.filter(child=child)
            .values('level')
            .annotate(avg_score=100* Round2(Avg('score')))
        )

        # the avg score of the child in each day
        daily_scores = (
                Exercise.objects.filter(child=child, submission_date__isnull=False)
                .annotate(day=TruncDate('submission_date'))
                .values('day')
                .annotate(avg_score=100* Round2(Avg('score')), exercise_count=Count('id'))
                .order_by('day')
        )

        # letters confused with other letters
        confused_letters = (
            SubmittedLetter.objects.filter(exercise__child=child)
            .exclude(expected_letter=F('submitted_letter')) # don't include correct guesses
            .exclude(submitted_letter='') # don't include empty guesses
            .values('expected_letter', 'submitted_letter')
            .annotate(confusion_count=Count('id')) # count how many times the expected letter was confused with the submitted letter
            .order_by('expected_letter', '-confusion_count')
        )

        letter_appearances = dict(
            SubmittedLetter.objects.filter(exercise__child=child)
            .values('expected_letter')
            .annotate(total=Count('id'))
            .values_list('expected_letter', 'total')
        )
        often_confused_letters = []
        already_added_letters = set()
        for confusion in confused_letters:
            expected_letter = confusion['expected_letter']
            # will want to add only the most confused letter with each letter
            # it is the first in order in confused_letters because it is sorted by the confusion_count
            # goes over the other letters confused with the same one
            if expected_letter not in already_added_letters:
                confused_with = confusion['submitted_letter']
                confusion_count = confusion['confusion_count']
                letter_total_appearances = letter_appearances.get(expected_letter, 1)
                confusion_percentage = round((confusion_count / letter_total_appearances) * 100, 0)
                # if it is confused often - add the submitted letter and the confusion count to the list of confused letters
                if confusion_percentage >= 65 and confusion_count >= 3: 
                    often_confused_letters.append({
                        'letter': expected_letter,
                        'confused_with': confused_with,
                        'times': confusion_count,
                        'confusion_percentage': confusion_percentage
                    })

        return Response({
            'letter_scores': letter_scores,
            'level_scores': level_scores,
            'daily_scores': daily_scores,
            'often_confused_letters': often_confused_letters
        }, status=status.HTTP_200_OK)
    
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
