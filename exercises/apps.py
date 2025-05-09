import nltk
from django.apps import AppConfig

# runs only when the server starts(twice if --noreload is not used in runserver, if used - only once)
class ExercisesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'exercises'
    # the server has to run this before it can be used
    def ready(self):
        # Check if wordnet is already available
        try:
            nltk.data.find('corpora/wordnet.zip')
            print("wordnet is already available")
        # if not, download it
        except LookupError:
            print("wordnet was not found")
            nltk.download('wordnet', quiet=True)
            print("wordnet download complete")
