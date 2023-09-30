from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    """
    CustomUser inherits from AbstractUser from Django's authentication package. We extend the existing model
    with the phone number.
    """
    phone_number = models.CharField(max_length=20)


class Contact(models.Model):
    """
    Contact details model.
    """
    id = models.CharField(max_length=1, null=False, primary_key=True, default='x')  # to ensure there is one row only
    phone_number = models.CharField(max_length=20, null=False)
    email = models.EmailField(max_length=150, null=False)
    address = models.CharField(max_length=300, null=False)
    opening_hours_en = models.CharField(max_length=150, null=False)
    opening_hours_hu = models.CharField(max_length=150, null=False)

    def save(self, *args, **kwargs):
        """
        Overriding the save method to not allow multiple rows.
        """
        self.id = 'x'
        super().save(*args, **kwargs)


class Service(models.Model):
    """
    Service model.
    """
    id = models.AutoField(primary_key=True)
    service_name_en = models.CharField(max_length=100, null=False)
    service_name_hu = models.CharField(max_length=100, null=False)
    price_default = models.IntegerField(null=False)  # at least one price must be provided
    price_small = models.IntegerField(null=True)
    price_big = models.IntegerField(null=True)
    service_description_en = models.TextField(null=False)
    service_description_hu = models.TextField(null=False)
    max_duration = models.SmallIntegerField(null=False)
    photo = models.ImageField(blank=False, null=False, upload_to='services')
    active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        """
        Overriding the save method to keep the existing photo if the user does not provide it during the update.
        """
        if self.photo.name is None or self.photo.name == '':
            self.photo = Service.objects.get(id=self.id).photo
        super().save(*args, **kwargs)
