from django.urls import path
from .views import ArticlesView, LetterStatsView, ExerciseGenerationView, ExerciseSubmissionView, ExerciseRetrieveView, SubmissionListOfChildView

urlpatterns = [
    path('', ExerciseGenerationView.as_view(), name='exercise_generation'),
    path('stats/<int:pk>/letters', LetterStatsView.as_view(), name='letter_stats'),
    path('<int:pk>/submit/', ExerciseSubmissionView.as_view(), name='exercise_submit'),
    path('<int:pk>/', ExerciseRetrieveDeleteView.as_view(), name='exercise_retrieve_delete'),
    path ('<int:pk>/submissions/', SubmissionListOfChildView.as_view(), name='submission_list_of_child'),
    path ('articles/', ArticlesView.as_view(), name='articles_list')
]
