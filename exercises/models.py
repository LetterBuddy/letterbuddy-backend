from django.db import models
from accounts.models import ChildProfile, User

class ExerciseSubmission(models.Model):
    # TODO add more according to wordnet categories
    class ExerciseCategory(models.TextChoices):
        VEHICLE = "vehicle", "Vehicle"
        ANIMAL = "animal", "Animal"

    child = models.ForeignKey(ChildProfile ,on_delete=models.CASCADE)
    requested_text = models.CharField()
    submitted_text = models.CharField()
    # TODO learn more about the ImageField - if not needed - remove Pillow
    uploaded_image = models.ImageField()
    # could maybe use DecimalField instead
    score = models.FloatField()
    # TODO maybe move ExerciseLevel and ExerciseLanguage here instead of ChildProfile
    level = models.CharField(max_length=50, choices=ChildProfile.ExerciseLevel.choices, default='letters')
    language = models.CharField(max_length=50, choices=ChildProfile.ExerciseLanguage.choices, default='en')
    category = models.CharField(max_length=50, choices=ExerciseCategory.choices)
    submission_date = models.DateTimeField(auto_now_add=True)
    time_taken = models.DurationField()

    def __str__(self):
        return self.child.user.username + " requested to write " + self.requested_text + " and wrote " + self.submitted_text + " with a score of " + self.score


class Letter(models.Model):
    letter = models.CharField(max_length=1)
    language = models.CharField(max_length=50, choices=ChildProfile.ExerciseLanguage.choices, default='en')
    avg_score = models.FloatField()
    count_apperances = models.IntegerField()
    def __str__(self):
        return self.letter + " in " + self.language