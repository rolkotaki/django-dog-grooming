from django.core.exceptions import ValidationError as django_ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.db.utils import Error
from django.db import models
from unittest.mock import Mock, patch
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from dog_grooming_app.models import CustomUser, Service, Booking
from dog_grooming_app.utils.AccountActivationTokenGenerator import account_activation_token


class ModelsTestCase(TestCase):
    """
    Test cases for models.
    """

    def test_01_customuser_cancel_fails_with_save(self):
        """Tests that we return False when the user cancellation fails during the save method."""
        with patch.object(CustomUser, '__init__', return_value=None):
            with patch.object(CustomUser, 'save', side_effect=Error):
                cu = CustomUser()
                cu.pk = 1
                cu.username = 'username'
                return_value = cu.cancel_user()
        self.assertFalse(return_value)

    def test_02_booking_cancel_fails_with_save(self):
        """Tests that we return False when the booking cancellation fails during the save method."""
        with patch.object(Booking, '__init__', return_value=None):
            with patch.object(Booking, 'save', side_effect=Error):
                booking = Booking()
                booking.id = 1
                return_value = booking.cancel_booking()
        self.assertFalse(return_value)

    def test_03_service_with_no_photo_during_save(self):
        """Tests that if there is no photo provided during a service update, we keep the existing one."""
        with patch.object(Service, '__init__', return_value=None):
            with patch.object(Service, 'clean', return_value=None):
                mock_service = Mock()
                mock_service.photo = Mock()
                mock_service.photo.name = 'photo'
                with patch.object(Service.objects, 'get', return_value=mock_service):
                    service = Service()
                    service.id = 1
                    service.photo = Mock()
                    service.photo.name = None
                    service.slug = 'slug'
                    with patch.object(models.Model, 'save', return_value=None):
                        service.save()
                    Service.objects.get.assert_called_once()
        self.assertEqual(service.photo.name, mock_service.photo.name)

    def test_04_service_validate_price_not_integer(self):
        """Tests that a ValidationError is thrown is the price is not a positive integer. Default price is required."""
        with patch.object(Service, '__init__', return_value=None):
            service = Service()
        self.assertRaises(django_ValidationError, service._validate_price, field_name='price_big', value=-1)
        self.assertRaises(django_ValidationError, service._validate_price, field_name='price_big', value=0)
        self.assertRaises(django_ValidationError, service._validate_price, field_name='price_small', value='a')
        self.assertRaises(django_ValidationError, service._validate_price, field_name='price_default', value='a')
        self.assertRaises(django_ValidationError, service._validate_price, field_name='price_default', value='')
        self.assertRaises(django_ValidationError, service._validate_price, field_name='price_default', value=None)


class ActivateAccountTestCase(TestCase):
    """
    Test cases for the user account activation.
    """

    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(username='user', password='test_password')

    def test_01_activate_user_account_successful(self):
        """Tests the successful activation of a user account."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = account_activation_token.make_token(self.user)
        response = self.client.post(reverse('activate_account', args=(uid, token)), follow=True)
        self.assertContains(response, '<div class="form_success_message">')
        self.assertContains(response, 'Your account has been activated successfully, you can log in now.')

    def test_02_activate_user_account_not_successful(self):
        """Tests when activating the user account fails because of an invalid uid."""
        uid = 'aaa'
        token = account_activation_token.make_token(self.user)
        response = self.client.post(reverse('activate_account', args=(uid, token)), follow=True)
        self.assertContains(response, '<div class="login_signup_errors">')
        self.assertContains(response, 'Activation link is invalid or there was a problem activating your account.')

    def test_03_activate_user_account_not_successful(self):
        """Tests when activating the user account fails because of an invalid token."""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = 'aaa'
        response = self.client.post(reverse('activate_account', args=(uid, token)), follow=True)
        self.assertContains(response, '<div class="login_signup_errors">')
        self.assertContains(response, 'Activation link is invalid or there was a problem activating your account.')

    def test_04_activate_user_account_not_successful(self):
        """Tests when activating the user account fails because a different user's pk was used in the decoding."""
        uid = urlsafe_base64_encode(force_bytes(CustomUser.objects.create_user(username='another_user',
                                                                               password='test_password').pk))
        token = account_activation_token.make_token(self.user)
        response = self.client.post(reverse('activate_account', args=(uid, token)), follow=True)
        self.assertContains(response, '<div class="login_signup_errors">')
        self.assertContains(response, 'Activation link is invalid or there was a problem activating your account.')
