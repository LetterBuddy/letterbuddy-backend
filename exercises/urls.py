from django.urls import path
from .views import ArticlesView, ExerciseGenerationView, ExerciseSubmissionView

urlpatterns = [
    path('', ExerciseGenerationView.as_view(), name='exercise_generation'),
    path('<int:pk>/submit/', ExerciseSubmissionView.as_view(), name='exercise_submission'),
    path ('articles/', ArticlesView.as_view(), name='articles_list')
]
