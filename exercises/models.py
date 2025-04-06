from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from accounts.models import ChildProfile

# TODO we are losing the score of each letter in the exercise(it is not referencing it in letter model)
class Exercise(models.Model):
    # TODO add more according to wordnet categories
    # TODO maybe move them to a separate model, than could more easily add and retrieve them
    class ExerciseCategory(models.TextChoices):
        VEHICLE = "vehicle"
        ANIMAL = "animal"
        COLOR = "color"
        TOY = "toy"

    child = models.ForeignKey(ChildProfile ,on_delete=models.CASCADE)
    requested_text = models.CharField()
    submitted_text = models.CharField()

    # TODO check about ImageField instead of IMGhippo, if not needed remember to remove pillow from requirements
    submitted_image = models.ImageField(null=True, blank=True)
    
    score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])

    # TODO maybe move ExerciseLevel here instead of ChildProfile
    level = models.CharField(max_length=50, choices=ChildProfile.ExerciseLevel.choices, default='letters')
    category = models.CharField(max_length=50, choices=ExerciseCategory.choices, null=True, blank=True)
    # TODO remove this field
    generated_date = models.DateTimeField(auto_now_add=True)

    submission_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.child.user.username + " level:" + self.level + " category:" + self.category + " generated at:" + str(self.generated_date)

class Letter(models.Model):
    letter = models.CharField(max_length=1)
    avg_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    count_appearances = models.IntegerField()
    def __str__(self):
        return self.letter

class Article(models.Model):
    title = models.CharField(max_length=200)
    description = models.CharField()
    link = models.URLField()
    def __str__(self):
        return self.title + " " + self.link