from django.db import models
from django.contrib.auth.models import AbstractUser
# Create your models here.

class User(AbstractUser):
    # TODO check if email validation isn't case sensitive 
    def __str__(self):
        return self.username

class Adult(models.Model):
    # often called profile - due to only having one user model this extends
    # with specific fields for the adult
    # currently - no difference between the regular user model
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    def __str__(self):
        return self.user.username

