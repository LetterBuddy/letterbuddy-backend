from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # TODO check if email validation isn't case sensitive
    class Role(models.TextChoices):
        ADMIN = "ADMIN"
        ADULT = "ADULT"
        CHILD = "CHILD"
    
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.ADMIN)

    def __str__(self):
        return self.username

class AdultProfile(models.Model):
    # due to only having one user model this extends
    # with specific fields for the adult
    # currently - no difference between the regular user model
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    def __str__(self):
        return self.user.username

class ChildProfile(models.Model):
    class ExerciseLevel(models.TextChoices):
        LETTERS = "letters"
        WORDS = "words"
        CATEGORY = "category"
        
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    guiding_adult = models.ForeignKey(AdultProfile, on_delete=models.CASCADE, related_name="children")
    exercise_level = models.CharField(max_length=50, choices=ExerciseLevel.choices, default='letters')
    def __str__(self):
        return self.user.username

