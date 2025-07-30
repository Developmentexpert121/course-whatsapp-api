from django.db import models


# Create your models here.
class User(models.Model):
    email = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=100)
    password = models.CharField(max_length=128)

    def __str__(self):
        return self.name
