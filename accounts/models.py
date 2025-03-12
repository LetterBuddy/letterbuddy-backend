from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class User(AbstractUser):
    # TODO check if email validation isn't case sensitive
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        ADULT = "ADULT", "Adult"
        CHILD = "CHILD", "Child"
    
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.ADMIN)

    def __str__(self):
        return self.username

class AdultProfile(models.Model):
    # due to only having one user model this extends
    # with specific fields for the adult
    # currently - no difference between the regular user model
    # TODO think if the user should be pk or an id field
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    def __str__(self):
        return self.user.username

class ChildProfile(models.Model):
    # TODO an other option - define languages in settings, 
    # or use django's built in languages
    class ExerciseLanguage(models.TextChoices):
        ENGLISH = "en", "English"
    class ExerciseLevel(models.TextChoices):
        LETTERS = "letters", "Letters"
        WORDS = "words", "Words"
        CATEGORY = "category", "Category"
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    guiding_adult = models.ForeignKey(AdultProfile, on_delete=models.CASCADE, related_name="children")
    exercise_language = models.CharField(max_length=50, choices=ExerciseLanguage.choices, default='en')
    exercise_level = models.CharField(max_length=50, choices=ExerciseLevel.choices, default='letters')
    def __str__(self):
        return self.user.username

