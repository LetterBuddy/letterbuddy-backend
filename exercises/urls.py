from django.urls import path
from .views import (ArticlesView, 
                    ExerciseGenerationView, 
                    ExerciseSubmissionView, 
                    ExerciseRetrieveDeleteView, 
                    SubmissionListOfChildView)

urlpatterns = [
    path('', ExerciseGenerationView.as_view(), name='exercise_generation'),
    path('<int:pk>/submit/', ExerciseSubmissionView.as_view(), name='exercise_submit'),
    path('<int:pk>/', ExerciseRetrieveDeleteView.as_view(), name='exercise_retrieve_delete'),
    path ('<int:pk>/submissions/', SubmissionListOfChildView.as_view(), name='submission_list_of_child'),
    path ('articles/', ArticlesView.as_view(), name='articles_list')
]
