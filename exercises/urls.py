from django.urls import path
from .views import ArticlesView, ExerciseGenerationView, ExerciseSubmissionView, ExerciseRetrieveView, SubmissionListOfChildView

urlpatterns = [
    path('', ExerciseGenerationView.as_view(), name='exercise_generation'),
    path('<int:pk>/submit/', ExerciseSubmissionView.as_view(), name='exercise_submit'),
    path('<int:pk>/', ExerciseRetrieveView.as_view(), name='exercise_retrieve'),
    path ('<int:pk>/submissions/', SubmissionListOfChildView.as_view(), name='submission_list_of_child'),
    path ('articles/', ArticlesView.as_view(), name='articles_list')
]
