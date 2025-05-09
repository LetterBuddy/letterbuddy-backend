import nltk
from groq import Groq
from paddleocr import PaddleOCR

from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential

from django.apps import AppConfig
from django.conf import settings


azure_client = None
groq_client = None
paddleOcr = None

def initialize_models():
    # if any of the models is not initialized - try to initialize them
    global groq_client, paddleOcr, azure_client
    if azure_client is None:
        try:
            azure_client = ChatCompletionsClient(
                endpoint='https://models.github.ai/inference',
                credential=AzureKeyCredential(settings.AZURE_TOKEN)
            )
        except Exception as e:
            print("Failed to initialize the Azure client")
            print(e)
    if groq_client is None:
        try:
            groq_client = Groq(api_key=settings.GROQ_API_KEY)
        except Exception as e:
            print("Failed to initialize the Groq client")
            print(e)
    if paddleOcr is None:
        try:
            paddleOcr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        except Exception as e:
            print("Failed to initialize the PaddleOCR client")
            print(e)

# runs only when the server starts(twice if --noreload is not used in runserver, if used - only once)
class ExercisesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'exercises'
    # the server has to run this before it can be used
    def ready(self):
        # initialize the models
        initialize_models()
        # Check if wordnet is already available
        try:
            nltk.data.find('corpora/wordnet.zip')
            print("wordnet is already available")
        # if not, download it
        except LookupError:
            print("wordnet was not found")
            nltk.download('wordnet', quiet=True)
            print("wordnet download complete")
        
        
