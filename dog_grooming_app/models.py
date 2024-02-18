import datetime
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.db.utils import Error
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils.text import slugify
from typing import Tuple
import threading

from dog_grooming_app.utils.constants import PHONE_NUMBER_VALIDATOR, BREAK, BOOKING_CANCELLATION_EMAIL_SUBJECT_TO_ADMIN, \
    BOOKING_CANCELLATION_EMAIL_SUBJECT_TO_USER, USER_CANCELLATION_EMAIL_SUBJECT, USER_REGISTRATION_EMAIL_SUBJECT, \
    CALLBACK_EMAIL_SUBJECT
from dog_grooming_salon.utils import DogGroomingEmail
from dog_grooming_app.utils.AccountActivationTokenGenerator import account_activation_token
from dog_grooming_salon.logger import logger


class CustomUser(AbstractUser):
    """
    CustomUser inherits from AbstractUser from Django's authentication package. We extend the existing model
    with the phone number.
    """
    phone_number = models.CharField(max_length=20, validators=[RegexValidator(regex=PHONE_NUMBER_VALIDATOR,
                                                                              message=_('Enter a valid phone number.'))])

    def cancel_user(self) -> bool:
        """
        Cancels the user by putting the is_active flag to False. The user is notified via email.
        """
        try:
            self.is_active = False
            self.save()
            html_message = render_to_string('emails/user_cancellation.html', {'username': self.username})
            dg_email = DogGroomingEmail(to=self.email, subject=str(_(USER_CANCELLATION_EMAIL_SUBJECT)),
                                        message=html_message)
            threading.Thread(target=dg_email.send).start()
            return True
        except Error:
            logger.error('An error happened during the cancellation of the user {}'.format(self.pk, self.username))
            return False

    def send_activation_link(self, domain: str, protocol: str):
        """
        Sends the activation link to the user's email.
        """
        email_context = {'username': self.username,
                         'domain': domain,
                         'uid': urlsafe_base64_encode(force_bytes(self.pk)),
                         'token': account_activation_token.make_token(self),
                         'protocol': protocol}
        html_message = render_to_string('emails/user_registration.html', email_context)
        dg_email = DogGroomingEmail(to=[self.email], subject=str(_(USER_REGISTRATION_EMAIL_SUBJECT)),
                                    message=html_message)
        threading.Thread(target=dg_email.send).start()


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

    def get_opening_hour_for_day(self, day_of_week: int) -> datetime.time:
        """
        Returns the opening hour for a given day of the week.
        """
        opening_hour_attrs = {
            0: self.opening_hour_monday,
            1: self.opening_hour_tuesday,
            2: self.opening_hour_wednesday,
            3: self.opening_hour_thursday,
            4: self.opening_hour_friday,
            5: self.opening_hour_saturday,
            6: self.opening_hour_sunday,
        }
        return opening_hour_attrs.get(day_of_week)

    def get_closing_hour_for_day(self, day_of_week: int) -> datetime.time:
        """
        Returns the closing hour for a given day of the week.
        """
        closing_hour_attrs = {
            0: self.closing_hour_monday,
            1: self.closing_hour_tuesday,
            2: self.closing_hour_wednesday,
            3: self.closing_hour_thursday,
            4: self.closing_hour_friday,
            5: self.closing_hour_saturday,
            6: self.closing_hour_sunday,
        }
        return closing_hour_attrs.get(day_of_week)

    def save(self, *args, **kwargs):
        """
        Overriding the save method to not allow multiple rows.
        """
        self.id = 'x'
        super().save(*args, **kwargs)

    @staticmethod
    def send_callback_request(user: CustomUser):
        superusers_emails = CustomUser.objects.filter(is_superuser=True).values_list('email', flat=True)
        html_message = render_to_string('emails/callback_request.html', {'user': user})
        dg_email = DogGroomingEmail(to=superusers_emails, subject=str(_(CALLBACK_EMAIL_SUBJECT)),
                                    message=html_message)
        threading.Thread(target=dg_email.send).start()


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
    slug = models.SlugField(unique=True, max_length=255, null=True, blank=True)

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

    def get_duration_of_service(self) -> Tuple[datetime.timedelta, datetime.timedelta]:
        """
        Returns the duration of a service with and without the break.
        """
        duration_without_break = datetime.timedelta(minutes=self.max_duration)
        duration_with_break = datetime.timedelta(minutes=(self.max_duration + BREAK))
        return duration_without_break, duration_with_break

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
        if not self.slug:
            self.slug = slugify(self.service_name_en)
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

    def cancel_booking(self, by_user: bool = True) -> bool:
        """
        Cancels the booking by putting the cancelled flag to True.
        The by_user param indicates whether it is cancelled by the user themselves or by the admin.
        The user or the admin is notified via email.
        """
        try:
            self.cancelled = True
            self.save()
            email_context = {'username': self.user.username,
                             'day': self.date,
                             'time': self.time}
            # if it is cancelled by the admin, we send a mail to the user
            if not by_user:
                html_message = render_to_string('emails/booking_cancellation_to_user.html', email_context)
                dg_email = DogGroomingEmail(to=[self.user.email],
                                            subject=str(_(BOOKING_CANCELLATION_EMAIL_SUBJECT_TO_USER)),
                                            message=html_message)
                threading.Thread(target=dg_email.send).start()
            # if it is cancelled by the user, we send a mail to the admin
            if by_user:
                superusers_emails = CustomUser.objects.filter(is_superuser=True).values_list('email', flat=True)
                html_message = render_to_string('emails/booking_cancellation_to_admin.html', email_context)
                dg_email = DogGroomingEmail(to=superusers_emails,
                                            subject=str(_(BOOKING_CANCELLATION_EMAIL_SUBJECT_TO_ADMIN)),
                                            message=html_message)
                threading.Thread(target=dg_email.send).start()
            return True
        except Error:
            logger.error('An error happened during the cancellation of the booking {}'.format(self.id))
            return False
