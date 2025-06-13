from django.apps import AppConfig

# runs only when the server starts(twice if --noreload is not used in runserver, if used - only once)
class ExercisesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'exercises'
    # the server has to run this before it can be used
    def ready(self):
        # to avoid django imports before the app is ready
        from .views import initialize_models
        initialize_models()

