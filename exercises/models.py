from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import ChildProfile

# decimal field for score - that removes the need of the score got to fit the decimal places - will rounded it to fit 
class ScoreRoundingDecimalField(models.DecimalField):
    def validate_precision(self, value):
        return value


class Exercise(models.Model):
    class ExerciseCategory(models.TextChoices):
        VEHICLE = "vehicle"
        ANIMAL = "animal"
        COLOR = "color"
        TOY = "toy"
        FOOD = "food"
        CLOTHING = "clothing"
        ACTION = "action"
        JOB = "job"
        NATURE = "nature"
        FAMILY = "family"
        PLACE = "place"


    child = models.ForeignKey(ChildProfile ,on_delete=models.CASCADE)
    requested_text = models.CharField()
    submitted_text = models.CharField()
    
    submitted_image = models.ImageField(null=True, blank=True)
    
    score = ScoreRoundingDecimalField(null=True, blank=True, max_digits=3, decimal_places=2, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    level = models.CharField(max_length=50, choices=ChildProfile.ExerciseLevel.choices, default='letters')
    category = models.CharField(max_length=50, choices=ExerciseCategory.choices, null=True, blank=True)

    generated_date = models.DateTimeField(auto_now_add=True)
    submission_date = models.DateTimeField(null=True, blank=True)

    feedback = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.child.user.username + " level:" + self.level + " category:" + self.category + " generated at:" + str(self.generated_date)

class SubmittedLetter(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    submitted_letter = models.CharField(max_length=1)
    expected_letter = models.CharField(max_length=1)
    score = ScoreRoundingDecimalField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)], max_digits=3, decimal_places=2)
    position = models.IntegerField()
    def __str__(self):
        return "Expected:" + self.expected_letter + " submitted:" + self.submitted_letter + " score:" + str(self.score) + " position:" + str(self.position)


class CategorizedWord(models.Model):
    word = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=Exercise.ExerciseCategory.choices, db_index=True)
    def __str__(self):
        return self.word + " category:" + self.category

class Article(models.Model):
    title = models.CharField(max_length=200)
    description = models.CharField()
    link = models.URLField()
    def __str__(self):
        return self.title + " " + self.link