import nltk
from django.apps import AppConfig

# runs only when the server starts(twice if --noreload is not used in runserver, if used - only once)
class ExercisesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'exercises'
    nltk.download('wordnet', quiet=True)
    print("nltk wordnet downloaded")
