from django.urls import path, include
from .views import ArticlesView, ExerciseGenerationView

urlpatterns = [
    path('', ExerciseGenerationView.as_view(), name='exercise_generation'),
    path ('articles/', ArticlesView.as_view(), name='articles_list')
]
