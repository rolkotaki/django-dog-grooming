from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    """
    CustomUser inherits from AbstractUser from Django's authentication package. We extends the existing model
    with the phone number.
    """
    phone_number = models.CharField(max_length=20)
