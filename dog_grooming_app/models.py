from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


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
    opening_hour_monday = models.TimeField(null=True)
    closing_hour_monday = models.TimeField(null=True)
    opening_hour_tuesday = models.TimeField(null=True)
    closing_hour_tuesday = models.TimeField(null=True)
    opening_hour_wednesday = models.TimeField(null=True)
    closing_hour_wednesday = models.TimeField(null=True)
    opening_hour_thursday = models.TimeField(null=True)
    closing_hour_thursday = models.TimeField(null=True)
    opening_hour_friday = models.TimeField(null=True)
    closing_hour_friday = models.TimeField(null=True)
    opening_hour_saturday = models.TimeField(null=True)
    closing_hour_saturday = models.TimeField(null=True)
    opening_hour_sunday = models.TimeField(null=True)
    closing_hour_sunday = models.TimeField(null=True)
    google_maps_url = models.CharField(max_length=500, null=False)

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

    def _validate_price(self, field_name, value):
        """
        Validates that the prices are positive integers.
        """
        try:
            if value is not None and value != '':
                if int(value) <= 0:
                    raise ValidationError({field_name: _("Price must be greater than zero!")})
            elif field_name == 'price_default':  # meaning it is empty
                raise ValidationError({field_name: _("Default price must not be empty!")})
        except ValueError:
            raise ValidationError({field_name: _("A valid number is required!")})

    def clean(self):
        """
        Overrides the clean method to validate that prices.
        """
        super().clean()
        self._validate_price('price_default', self.price_default)
        self._validate_price('price_small', self.price_small)
        self._validate_price('price_big', self.price_big)

    def save(self, *args, **kwargs):
        """
        Overriding the save method to keep the existing photo if the user does not provide it during the update
        and to validate the prices.
        """
        self.clean()
        if self.photo.name is None or self.photo.name == '':
            self.photo = Service.objects.get(id=self.id).photo
        super().save(*args, **kwargs)


class Booking(models.Model):
    """
    Booking model.
    """
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING)
    service = models.ForeignKey(Service, on_delete=models.DO_NOTHING)
    dog_size = models.CharField(null=True)
    service_price = models.IntegerField(null=False)  # it can change in the meanwhile, so I save the one when booked
    date = models.DateField(null=False, auto_now=False)
    time = models.TimeField(null=False, auto_now=False)
    comment = models.TextField(null=False)
    cancelled = models.BooleanField(default=False)
    booking_date = models.DateTimeField(null=False, auto_now_add=True)
