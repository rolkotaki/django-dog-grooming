import os
import copy
import re
import datetime
from rest_framework.test import APITestCase
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ValidationError as django_ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.translation import gettext as _
from django.db.utils import Error
from django.db import models
from django.contrib import messages
from unittest.mock import Mock, patch, mock_open
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes

from .models import CustomUser, Contact, Service, Booking
from .api_views import CancelUser, CancelBooking, ListAvailableBookingSlots, ServiceRetrieveUpdateDestroy
from .views import ContactPage, admin_api_page
from .utils import GalleryManager, BookingManager
from .tokens import account_activation_token


class ContactAPITestCase(APITestCase):
    """
    Test cases for APIs related to contact details.
    """

    def setUp(self):
        self.client = APIClient()
        self.admin_user = CustomUser.objects.create_superuser(username='admin', password='admin_password')
        self.user = CustomUser.objects.create_user(username='user', password='test_password')
        self.contact_attrs = {
            'phone_number': '+36991234567',
            'email': 'somebody@mail.com',
            'address': 'Happiness Street 1, HappyCity, 99999',
            'opening_hour_monday': '08:00:00',
            'closing_hour_monday': '17:30:00',
            'opening_hour_tuesday': '08:00:00',
            'closing_hour_tuesday': '17:30:00',
            'opening_hour_wednesday': '08:00:00',
            'closing_hour_wednesday': '17:30:00',
            'opening_hour_thursday': '08:00:00',
            'closing_hour_thursday': '17:30:00',
            'opening_hour_friday': '08:00:00',
            'closing_hour_friday': '17:30:00',
            'opening_hour_saturday': '09:00:00',
            'closing_hour_saturday': '13:30:00',
            'google_maps_url': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2726.2653641484812!2d19.65391067680947!3d46.89749933667435!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x4743d09cb06aa0cd%3A0xc162d3291067ef90!2sBennett%20Kft.%20Sz%C3%A9kt%C3%B3i%20kutyaszalon!5e0!3m2!1sen!2ses!4v1696190559457!5m2!1sen!2ses'
        }
        self.contact_update_attrs = {
            'email': 'somebody@newmail.com'
        }

    def _send_create_request(self, admin=True):
        """Calls the API to create the contact details."""
        self.client.force_authenticate(user=self.admin_user if admin else self.user)
        return self.client.post(reverse('api_contact_create'), self.contact_attrs)

    def test_01_create_contact_without_permission(self):
        """Tries to create contact details without permission."""
        response = self._send_create_request(admin=False)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_02_create_contact(self):
        """Tests creating the contact details."""
        initial_count = Contact.objects.count()
        response = self._send_create_request()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Contact.objects.count(), initial_count + 1)
        for attr, expected_value in self.contact_attrs.items():
            self.assertEqual(response.data[attr], expected_value)

    def test_03_update_contact_without_permission(self):
        """Tries to update contact details without permission."""
        self._send_create_request()
        self.client.force_authenticate(user=self.user)
        contact = Contact.objects.first()
        response = self.client.patch(reverse('api_contact_update_delete', args=(contact.id,)),
                                     self.contact_update_attrs,
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_04_update_contact(self):
        """Tests updating the contact details."""
        self._send_create_request()
        contact = Contact.objects.first()
        self.client.patch(reverse('api_contact_update_delete', args=(contact.id,)), self.contact_update_attrs,
                          format='json')
        updated = Contact.objects.get(id=contact.id)
        self.assertEqual(updated.email, 'somebody@newmail.com')

    def test_05_delete_contact_without_permission(self):
        """Tries to delete contact details without permission."""
        self._send_create_request()
        self.client.force_authenticate(user=self.user)
        contact = Contact.objects.first()
        response = self.client.delete(reverse('api_contact_update_delete', args=(contact.id,)))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_06_delete_contact(self):
        """Tests deleting the contact details."""
        self._send_create_request()
        initial_count = Contact.objects.count()
        contact = Contact.objects.first()
        self.client.delete(reverse('api_contact_update_delete', args=(contact.id,)))
        self.assertEqual(Contact.objects.count(), initial_count - 1)
        self.assertRaises(Contact.DoesNotExist, Contact.objects.get, id=contact.id)

    def test_07_cannot_create_multiple(self):
        """Tries to create multiple contact records."""
        self._send_create_request()
        response = self._send_create_request()
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class ServiceAPITestCase(APITestCase):
    """
    Test cases for APIs related to services.
    """

    def setUp(self):
        self.client = APIClient()
        self.admin_user = CustomUser.objects.create_superuser(username='admin', password='admin_password')
        self.user = CustomUser.objects.create_user(username='user', password='test_password')
        self.service_attrs = {
            'service_name_en': 'Service name EN',
            'service_name_hu': 'Service name HU',
            'price_default': 1000,
            'price_small': 750,
            'price_big': 1250,
            'service_description_en': 'Description in English for the service.',
            'service_description_hu': 'A szolgáltatás leírása magyarul.',
            'max_duration': 60,
            'active': True
        }
        self.photo_path = os.path.join(settings.MEDIA_ROOT, 'services', 'default.jpg')
        self.service_update_attrs = {
            'service_name_en': 'Service name EN changed',
            'service_name_hu': 'Service name HU valtozott',
            'price_default': 1050
        }

    def _send_create_request(self, admin=True):
        """Calls the API to create a new service. It uploads a photo too as it is required.
        At the end the photo is deleted."""
        self.client.force_authenticate(user=self.admin_user if admin else self.user)
        with open(self.photo_path, 'rb') as photo_data:
            self.service_attrs['photo'] = photo_data
            response = self.client.post(reverse('api_service_create'), self.service_attrs, format='multipart')
        if admin:
            try:
                created_service = Service.objects.last()
                os.remove(created_service.photo.path)
            except:
                pass
        return response

    def test_01_create_service_without_permission(self):
        """Tries to create a service without permission."""
        response = self._send_create_request(admin=False)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_02_create_service(self):
        """Tests creating a service."""
        initial_count = Service.objects.count()
        response = self._send_create_request()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Service.objects.count(), initial_count + 1)
        for attr, expected_value in self.service_attrs.items():
            if attr != 'photo':
                self.assertEqual(response.data[attr], expected_value)

    def test_03_update_service_without_permission(self):
        """Tries to update a service without permission."""
        self._send_create_request()
        self.client.force_authenticate(user=self.user)
        service = Service.objects.first()
        response = self.client.patch(reverse('api_service_update_delete', args=(service.id,)),
                                     self.service_update_attrs,
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_04_update_service(self):
        """Tests updating a service."""
        self._send_create_request()
        service = Service.objects.first()
        original_photo = service.photo
        self.client.patch(reverse('api_service_update_delete', args=(service.id,)), self.service_update_attrs,
                          format='json')
        updated = Service.objects.get(id=service.id)
        self.assertEqual(updated.service_name_en, 'Service name EN changed')
        self.assertEqual(updated.service_name_hu, 'Service name HU valtozott')
        self.assertEqual(updated.price_default, 1050)
        # to validate that even if we didn't provide any photo in the update, it remained the same
        self.assertEqual(original_photo, updated.photo)

    def test_05_delete_service_without_permission(self):
        """Tries to delete a service without permission."""
        self._send_create_request()
        self.client.force_authenticate(user=self.user)
        service = Service.objects.first()
        response = self.client.delete(reverse('api_service_update_delete', args=(service.id,)))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_06_delete_service(self):
        """Tests deleting a service."""
        self._send_create_request()
        initial_count = Service.objects.count()
        service = Service.objects.first()
        self.client.delete(reverse('api_service_update_delete', args=(service.id,)))
        self.assertEqual(Service.objects.count(), initial_count - 1)
        self.assertRaises(Service.DoesNotExist, Service.objects.get, id=service.id)

    def test_07_list_services_without_permission(self):
        """Tries to list the services (using the API) without permission."""
        self._send_create_request()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('api_services'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_08_list_services(self):
        """Tests listing the services, using the API."""
        self._send_create_request()
        services_count = Service.objects.count()
        response = self.client.get(reverse('api_services'))
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(response.data['count'], services_count)
        self.assertEqual(len(response.data['results']), services_count)

    def test_09_list_only_active_services(self):
        """Tests listing only the active services."""
        self._send_create_request()
        services_count = Service.objects.count()
        self.service_attrs['active'] = False
        self._send_create_request()
        response = self.client.get(reverse('api_services'), {'active': True})
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(response.data['count'], services_count)
        self.assertEqual(len(response.data['results']), services_count)

    def test_10_list_all_services(self):
        """Tests listing all the services, including the not active ones."""
        self._send_create_request()
        self.service_attrs['active'] = False
        self._send_create_request()
        services_count = Service.objects.count()
        response = self.client.get(reverse('api_services'), {'active': False})
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(response.data['count'], services_count)
        self.assertEqual(len(response.data['results']), services_count)

    def test_11_create_price_only_positive_integer(self):
        """Tests that only positive integer prices can be created."""
        self.service_attrs['price_default'] = 0
        response = self._send_create_request()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.service_attrs['price_default'] = ''
        response = self._send_create_request()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.service_attrs['price_default'] = 1
        self.service_attrs['price_small'] = -1
        response = self._send_create_request()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.service_attrs['price_small'] = 1
        self.service_attrs['price_big'] = 'a'
        response = self._send_create_request()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_12_update_price_only_positive_integer(self):
        """Tests that prices can be updated only to positive integers."""
        self._send_create_request()
        service = Service.objects.first()
        response = self.client.patch(reverse('api_service_update_delete', args=(service.id,)), {'price_default': 0},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.patch(reverse('api_service_update_delete', args=(service.id,)), {'price_default': ''},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.patch(reverse('api_service_update_delete', args=(service.id,)), {'price_small': 'Z'},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.patch(reverse('api_service_update_delete', args=(service.id,)), {'price_big': -1},
                                     format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_13_api_view_update_price_only_positive_integer_(self):
        """Tests the edge cases where the API view fails because the prices are not integers."""
        with patch.object(ServiceRetrieveUpdateDestroy, '__init__', return_value=None):
            srud = ServiceRetrieveUpdateDestroy()
        request = Mock()
        request.data = {'price_default': 'a', 'price_small': 1000, 'price_big': 2000}
        self.assertRaises(ValidationError, srud.update, request=request)
        request.data = {'price_default': 1000, 'price_small': 'a', 'price_big': 2000}
        self.assertRaises(ValidationError, srud.update, request=request)
        request.data = {'price_default': 1000, 'price_small': 1000, 'price_big': 'a'}
        self.assertRaises(ValidationError, srud.update, request=request)


class BookingAPITestCase(APITestCase):
    """
    Test cases for APIs related to bookings.
    """

    def setUp(self):
        self.client = APIClient()
        self.admin_user = CustomUser.objects.create_superuser(username='admin', password='admin_password')
        self.user = CustomUser.objects.create_user(username='user', password='test_password')
        # creating a new service to be able to do a booking
        self.service = self._create_new_service()
        today_weekday = datetime.date.today().weekday()
        self.time_delta = 1 if today_weekday != 5 else 2
        self.booking_attrs = {
            'user': self.user.id,
            'service': self.service.id,
            'dog_size': 'big',
            'date': datetime.date.strftime(datetime.date.today() + datetime.timedelta(days=self.time_delta), '%Y-%m-%d'),
            'time': datetime.time.strftime(datetime.datetime.now().time(), '%H:%M:%S'),
            'comment': 'My dog is a Golden and I want it to have batched and its nails cut.',
            'cancelled': False
        }

    def _create_new_service(self):
        """Calls the API to create a new service. It uploads a photo too as it is required.
        At the end the photo is deleted."""
        self.client.force_authenticate(user=self.admin_user)
        photo_path = os.path.join(settings.MEDIA_ROOT, 'services', 'default.jpg')
        service_attrs = {
            'service_name_en': 'Service name EN',
            'service_name_hu': 'Service name HU',
            'price_default': 1000,
            'price_small': 750,
            'price_big': 1250,
            'service_description_en': 'Description in English for the service.',
            'service_description_hu': 'A szolgáltatás leírása magyarul.',
            'max_duration': 60,
            'active': True
        }
        with open(photo_path, 'rb') as photo_data:
            service_attrs['photo'] = photo_data
            response = self.client.post(reverse('api_service_create'), service_attrs, format='multipart')
        try:
            created_service = Service.objects.last()
            os.remove(created_service.photo.path)
            return created_service
        except:
            return None

    def _create_contact(self):
        """Calls the API to create the contact details."""
        contact_attrs = {
            'phone_number': '+36991234567',
            'email': 'somebody@mail.com',
            'address': 'Happiness Street 1, HappyCity, 99999',
            'opening_hour_monday': '08:00:00',
            'closing_hour_monday': '17:30:00',
            'opening_hour_tuesday': '08:00:00',
            'closing_hour_tuesday': '17:30:00',
            'opening_hour_wednesday': '08:00:00',
            'closing_hour_wednesday': '17:30:00',
            'opening_hour_thursday': '08:00:00',
            'closing_hour_thursday': '17:30:00',
            'opening_hour_friday': '08:00:00',
            'closing_hour_friday': '17:30:00',
            'opening_hour_saturday': '09:00:00',
            'closing_hour_saturday': '13:30:00',
            'google_maps_url': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2726.2653641484812!2d19.65391067680947!3d46.89749933667435!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x4743d09cb06aa0cd%3A0xc162d3291067ef90!2sBennett%20Kft.%20Sz%C3%A9kt%C3%B3i%20kutyaszalon!5e0!3m2!1sen!2ses!4v1696190559457!5m2!1sen!2ses'
        }
        self.client.force_authenticate(user=self.admin_user)
        return self.client.post(reverse('api_contact_create'), contact_attrs)

    def _send_create_request(self, admin=True):
        """Calls the API to create the contact details."""
        self.client.force_authenticate(user=self.admin_user if admin else self.user)
        return self.client.post(reverse('api_booking_create'), self.booking_attrs)

    def test_01_create_booking_without_permission(self):
        """Tries to create a booking without permission."""
        response = self._send_create_request(admin=False)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_02_create_booking(self):
        """Tests creating a booking."""
        initial_count = Booking.objects.count()
        response = self._send_create_request()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Booking.objects.count(), initial_count + 1)
        for attr, expected_value in self.booking_attrs.items():
            self.assertEqual(response.data[attr], expected_value)

    def test_03_list_bookings_without_permission(self):
        """Tries to list the bookings (using the API) without permission."""
        self._send_create_request()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('api_bookings'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_04_list_bookings(self):
        """Tests listing the bookings, using the API."""
        self._send_create_request()
        bookings_count = Booking.objects.count()
        response = self.client.get(reverse('api_bookings'))
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(response.data['count'], bookings_count)
        self.assertEqual(len(response.data['results']), bookings_count)

    def test_05_list_only_active_bookings(self):
        """Tests listing only the active bookings."""
        self._send_create_request()
        bookings_count = Booking.objects.count()
        self.booking_attrs['date'] = datetime.datetime.strptime('2000-01-01', '%Y-%m-%d')
        self._send_create_request()
        response = self.client.get(reverse('api_bookings'), {'active': True})
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(response.data['count'], bookings_count)
        self.assertEqual(len(response.data['results']), bookings_count)

    def test_06_list_only_cancelled_bookings(self):
        """Tests listing only the cancelled bookings."""
        self.booking_attrs['cancelled'] = True
        self._send_create_request()
        bookings_count = Booking.objects.count()
        self.booking_attrs['cancelled'] = False
        self._send_create_request()
        response = self.client.get(reverse('api_bookings'), {'cancelled': True})
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(response.data['count'], bookings_count)
        self.assertEqual(len(response.data['results']), bookings_count)

    def test_07_list_only_active_and_not_cancelled_bookings(self):
        """Tests listing only the active and not cancelled bookings."""
        self.booking_attrs['cancelled'] = False
        self.booking_attrs['date'] = datetime.date.today() + datetime.timedelta(days=self.time_delta)
        self._send_create_request()
        bookings_count = Booking.objects.count()
        self.booking_attrs['cancelled'] = True
        self._send_create_request()
        self.booking_attrs['date'] = datetime.datetime.strptime('2000-01-01', '%Y-%m-%d')
        self._send_create_request()
        response = self.client.get(reverse('api_bookings'), {'active': True, 'cancelled': False})
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(response.data['count'], bookings_count)
        self.assertEqual(len(response.data['results']), bookings_count)

    def test_08_list_bookings_with_no_filters(self):
        """Tests listing the bookings with no filters."""
        self.booking_attrs['cancelled'] = False
        self.booking_attrs['date'] = datetime.date.today() + datetime.timedelta(days=self.time_delta)
        self._send_create_request()
        self.booking_attrs['cancelled'] = True
        self._send_create_request()
        self.booking_attrs['date'] = datetime.datetime.strptime('2000-01-01', '%Y-%m-%d')
        self._send_create_request()
        bookings_count = Booking.objects.count()
        response = self.client.get(reverse('api_bookings'), {'active': False})
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(response.data['count'], bookings_count)
        self.assertEqual(len(response.data['results']), bookings_count)

    def test_09_cancel_booking(self):
        """Tests cancelling a booking."""
        self.booking_attrs['cancelled'] = False
        self.booking_attrs['date'] = datetime.date.today() + datetime.timedelta(days=self.time_delta)
        self._send_create_request()
        booking = Booking.objects.last()
        original_cancelled = booking.cancelled
        self.client.logout()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('api_cancel_booking', args=(booking.id,)))
        cancelled_booking = Booking.objects.get(id=booking.id)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertNotEquals(original_cancelled, cancelled_booking.cancelled)

    def test_10_list_available_booking_slots(self):
        """Tests listing the available booking slots for a given day."""
        self._create_contact()
        response = self.client.get(reverse('api_available_booking_slots'),
                                   {'day': datetime.date.strftime(datetime.date.today() + datetime.timedelta(days=self.time_delta),
                                                                  '%Y-%m-%d'),
                                    'service_id': self.service.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn(['12:00', '12:00 - 13:00'], response_data.get('booking_slots'))
        self.booking_attrs['time'] = '12:00:00'
        self._send_create_request()
        response = self.client.get(reverse('api_available_booking_slots'),
                                   {'day': datetime.date.strftime(datetime.date.today() + datetime.timedelta(days=self.time_delta),
                                                                  '%Y-%m-%d'),
                                    'service_id': self.service.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertNotIn(['12:00', '12:00 - 13:00'], response_data.get('booking_slots'))

    def test_11_booking_slots_for_closed_day(self):
        """Tests listing the available booking slots for a closed day."""
        self._create_contact()
        today_weekday = datetime.date.today().weekday() + 1
        delta_to_sunday = (7 - today_weekday) % 7
        response = self.client.get(reverse('api_available_booking_slots'),
                                   {'day': datetime.date.strftime(datetime.date.today() +
                                                                  datetime.timedelta(days=delta_to_sunday),
                                                                  '%Y-%m-%d'),
                                    'service_id': self.service.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn(['', 'Closed'], response_data.get('booking_slots'))

    def test_12_cancel_booking_with_string_booking_id(self):
        """Tests that cancelling a booking fails with bad request when a string booking id value provided."""
        with patch.object(CancelBooking, '__init__', return_value=None):
            cb = CancelBooking()
            cb.kwargs = {'booking_id': 'a'}
            response = cb.get(request=None)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_13_cancel_booking_with_cancel_function_failing(self):
        """Tests cancelling a booking when the cancel function fails and a response with HTTP code 500 is returned."""
        self._send_create_request()
        with patch.object(CancelBooking, '__init__', return_value=None):
            with patch.object(Booking, 'cancel_booking', return_value=False):
                booking_id = Booking.objects.last().id
                cb = CancelBooking()
                cb.kwargs = {'booking_id': booking_id}
                request = Mock()
                request.query_params = {}
                response = cb.get(request=request)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('An error happened during the cancellation of the booking', response.data.get('message'))

    def test_14_cancel_booking_with_booking_not_exist_failing(self):
        """Tests cancelling a booking when the booking does not exist and a response with HTTP code 500 is returned."""
        with patch.object(CancelBooking, '__init__', return_value=None):
            with patch.object(Booking.objects, 'get', side_effect=Booking.DoesNotExist):
                cb = CancelBooking()
                cb.kwargs = {'booking_id': 1}
                request = Mock()
                request.query_params = {}
                response = cb.get(request=request)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual('Booking with booking ID 1 does not exist', response.data.get('message'))

    def test_15_list_available_time_slots_with_missing_params(self):
        """Tests listing the available booking slots when parameters are not received and fails with a bad request."""
        with patch.object(ListAvailableBookingSlots, '__init__', return_value=None):
            labs = ListAvailableBookingSlots()
        request = Mock()
        request.query_params = {}
        response = labs.get(request=request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        request.query_params = {'day': '2023-01-01'}
        response = labs.get(request=request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        request.query_params = {'service_id': 1}
        response = labs.get(request=request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserAPITestCase(APITestCase):
    """
    Test cases for APIs related to users.
    """

    def setUp(self):
        self.client = APIClient()
        self.admin_user = CustomUser.objects.create_superuser(username='admin', password='admin_password')
        self.user = CustomUser.objects.create_user(username='user', password='test_password')

    def test_01_list_users_without_permission(self):
        """Tries to list the users (using the API) without permission."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('api_users'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_02_list_users(self):
        """Tests listing the users, using the API."""
        self.client.force_authenticate(user=self.admin_user)
        users_count = CustomUser.objects.count()
        response = self.client.get(reverse('api_users'))
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(response.data['count'], users_count)
        self.assertEqual(len(response.data['results']), users_count)

    def test_03_list_only_active_users(self):
        """Tests listing only the active users."""
        self.client.force_authenticate(user=self.admin_user)
        users_count = CustomUser.objects.count()
        inactive_user = CustomUser.objects.create_user(username='inactive_user', password='test_password',
                                                       is_active=False)
        response = self.client.get(reverse('api_users'), {'active': True})
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(response.data['count'], users_count)
        self.assertEqual(len(response.data['results']), users_count)

    def test_04_list_only_not_active_users(self):
        """Tests listing only the not active users."""
        self.client.force_authenticate(user=self.admin_user)
        inactive_user = CustomUser.objects.create_user(username='inactive_user', password='test_password',
                                                       is_active=False)
        response = self.client.get(reverse('api_users'), {'active': False})
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)

    def test_05_cancel_user_without_permission(self):
        """Tests cancelling a user without permission."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('api_cancel_user', args=(self.user.id,)), follow=True)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_06_cancel_user(self):
        """Tests cancelling a user."""
        original_is_active = self.user.is_active
        self.client.logout()
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(reverse('api_cancel_user', args=(self.user.id,)))
        cancelled_user = CustomUser.objects.get(id=self.user.id)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertNotEquals(original_is_active, cancelled_user.is_active)

    def test_07_cancel_user_with_string_user_id(self):
        """Tests that cancelling a user fails with bad request when a string user id value provided."""
        with patch.object(CancelUser, '__init__', return_value=None):
            cu = CancelUser()
            cu.kwargs = {'user_id': 'a'}
            response = cu.get(request=None)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_08_cancel_user_with_cancel_function_failing(self):
        """Tests cancelling a user when the cancel function fails and a response with HTTP code 500 is returned."""
        with patch.object(CancelUser, '__init__', return_value=None):
            with patch.object(CustomUser, 'cancel_user', return_value=False):
                user_id = CustomUser.objects.last().id
                cu = CancelUser()
                cu.kwargs = {'user_id': user_id}
                request = Mock()
                request.query_params = {}
                response = cu.get(request=request)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('An error happened during the cancellation of the user', response.data.get('message'))

    def test_09_cancel_user_with_user_not_exist_failing(self):
        """Tests cancelling a user when the user does not exist and a response with HTTP code 500 is returned."""
        with patch.object(CancelUser, '__init__', return_value=None):
            with patch.object(CustomUser.objects, 'get', side_effect=CustomUser.DoesNotExist):
                cu = CancelUser()
                cu.kwargs = {'user_id': 1}
                request = Mock()
                request.query_params = {}
                response = cu.get(request=request)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual('User with user ID 1 does not exist', response.data.get('message'))


class BaseViewTestCase(TestCase):
    """
    Test cases for the base view.
    """

    def _login(self):
        """Logs in the superuser or a normal user."""
        self.client = Client()
        self.user = CustomUser.objects.create_user(username='user', password='test_password')
        self.client.force_login(user=self.user)

    def test_01_signup_displayed_when_not_logged_in(self):
        """Tests that the signup option is displayed when user is not logged in."""
        response = self.client.get(reverse('home'))
        html_content = response.content.decode('utf-8')
        pattern = r'<a id="nav_signup" class="menu_item_right" href="(.*)">Sign Up</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_02_login_displayed_when_not_logged_in(self):
        """Tests that the login option is displayed when user is not logged in."""
        response = self.client.get(reverse('home'))
        html_content = response.content.decode('utf-8')
        pattern = r'<a id="nav_login" class="menu_item_right" href="(.*)">Log In</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_03_profile_not_displayed_when_not_logged_in(self):
        """Tests that the user profile option is not displayed when user is not logged in."""
        response = self.client.get(reverse('home'))
        html_content = response.content.decode('utf-8')
        pattern = r'<button class="dropdown_button">My Profile</button>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNone(match)

    def test_04_signup_not_displayed_when_logged_in(self):
        """Tests that the signup option is not displayed when user is logged in."""
        self._login()
        response = self.client.get(reverse('home'))
        html_content = response.content.decode('utf-8')
        pattern = r'<a class="menu_item_right" href="(.*)">Sign Up</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNone(match)

    def test_05_login_not_displayed_when_logged_in(self):
        """Tests that the login option is not displayed when user is logged in."""
        self._login()
        response = self.client.get(reverse('home'))
        html_content = response.content.decode('utf-8')
        pattern = r'<a class="menu_item_right" href="(.*)">Log In</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNone(match)

    def test_06_profile_displayed_when_logged_in(self):
        """Tests that the user profile option is displayed when user is logged in."""
        self._login()
        response = self.client.get(reverse('home'))
        html_content = response.content.decode('utf-8')
        pattern = r'<button id="user_dropdown_button" class="dropdown_button">My Profile</button>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_07_multilanguage_test_with_menu_items(self):
        """Tests that the changing the language works."""
        response = self.client.get(reverse('home'))
        html_content = response.content.decode('utf-8')
        for menu_item in [_('Home'), _('Services'), _('Gallery'), _('Contact')]:
            pattern = r'<a id="nav_(.*)" class="menu_item(.*)" href="(.*)">' + menu_item + r'</a>'
            match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
            self.assertIsNotNone(match)
        response = self.client.get('/hu', follow=True)
        html_content = response.content.decode('utf-8')
        for menu_item in [_('Home'), _('Services'), _('Gallery'), _('Contact')]:
            pattern = r'<a id="nav_(.*)" class="menu_item" href="(.*)">' + menu_item + r'</a>'
            match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
            self.assertIsNotNone(match)
        # changing the language back to English
        response = self.client.get('/en', follow=True)


class HomeTestCase(TestCase):
    """
    Test cases for the Home view.
    """

    def test_01_home_rendering(self):
        """Tests that the home view is rendered successfully and the correct template is used."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'home.html')


class LogInTestCase(TestCase):
    """
    Test cases for the LogIn view.
    """

    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(username='user', password='test_password')

    def test_01_login_rendering(self):
        """Tests that the login view is rendered successfully and the correct template is used."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'login.html')

    def test_02_successful_login(self):
        """Tests a successful login."""
        response = self.client.post(reverse('login'), {'username': 'user', 'password': 'test_password'})
        self.assertRedirects(response, reverse('home'))

    def test_03_unsuccessful_login(self):
        """Tests an unsuccessful login."""
        response = self.client.post(reverse('login'), {'username': 'user', 'password': 'wrong'})
        self.assertContains(response, 'Invalid username or password!')

    def test_04_empty_username_field(self):
        """Tests when the username field is empty."""
        response = self.client.post(reverse('login'), {'username': '', 'password': 'test_password'})
        self.assertContains(response, '<ul class="error_list">')

    def test_05_empty_password_field(self):
        """Tests when the password field is empty."""
        response = self.client.post(reverse('login'), {'username': 'user', 'password': ''})
        self.assertContains(response, '<ul class="error_list">')

    def test_06_inactive_user_login(self):
        """Tests when the user is inactive."""
        inactive_user = CustomUser.objects.create_user(username='inactive_user', password='test_password',
                                                       is_active=False)
        response = self.client.post(reverse('login'), {'username': 'inactive_user', 'password': 'test_password'})
        self.assertContains(response, 'Invalid username or password!')


class SignUpTestCase(TestCase):
    """
    Test cases for the SignUp view.
    """

    def setUp(self):
        self.signup_attr = {
            'first_name': 'Firstname',
            'last_name': 'Lastname',
            'email': 'somebody@mail.com',
            'phone_number': '+36991234567',
            'username': 'test_user',
            'password1': 'AldPoE672@8',
            'password2': 'AldPoE672@8',
        }

    def test_01_signup_rendering(self):
        """Tests that the signup view is rendered successfully and the correct template is used."""
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'signup.html')

    def test_02_successful_signup(self):
        """Tests a successful signup."""
        response = self.client.post(reverse('signup'), self.signup_attr)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, '<div class="form_success_message">')
        self.assertContains(response, 'Your account has been created successfully, please check your emails '
                                      'for the activation link to complete your registration.')

    def test_03_empty_signup_fields(self):
        """Tests for each field when it is empty when trying to sign up."""
        for field in ['first_name', 'last_name', 'email', 'phone_number', 'username', 'password1', 'password2']:
            signup_attr_copy = copy.deepcopy(self.signup_attr)
            signup_attr_copy[field] = ''
            response = self.client.post(reverse('signup'), signup_attr_copy)
            self.assertContains(response, '<ul class="error_list">')


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


class PersonalDataTestCase(TestCase):
    """
    Test cases for the Personal Data view.
    """

    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(username='user', password='test_password', email='somebody@mail.com')
        self.pers_data_attr = {
            'first_name': 'Firstname',
            'last_name': 'Lastname',
            'email': 'somebody@mail.com',
            'phone_number': '+36991234567'
        }

    def test_01_personal_data_not_displayed_when_not_logged_in(self):
        """Tests that personal is not displayed when user is not logged in."""
        response = self.client.get(reverse('personal_data'))
        self.assertRedirects(response, reverse('login') + '?next=' + reverse('personal_data'))

    def test_02_personal_data_displayed_when_logged_in(self):
        """Tests that personal is displayed when user is logged in."""
        self.client.force_login(user=self.user)
        response = self.client.get(reverse('personal_data'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'personal_data.html')

    def test_03_personal_data_empty_fields(self):
        """Tests for each field when it is empty when trying to update the personal data."""
        self.client.force_login(user=self.user)
        for field in ['first_name', 'last_name', 'email', 'phone_number']:
            pers_data_attr_copy = copy.deepcopy(self.pers_data_attr)
            pers_data_attr_copy[field] = ''
            response = self.client.post(reverse('personal_data'), pers_data_attr_copy)
            self.assertContains(response, '<ul class="error_list">')

    def test_04_personal_data_successful_update_without_email(self):
        """Tests a successful update of the personal data without email change."""
        self.client.force_login(user=self.user)
        response = self.client.post(reverse('personal_data'), self.pers_data_attr, follow=True)
        self.assertContains(response, '<div class="form_success_message">')
        self.assertContains(response, 'Your data has been updated successfully')

    def test_05_personal_data_successful_update_with_email(self):
        """Tests a successful update of the personal data with email change included."""
        self.pers_data_attr['email'] = 'new@mail.com'
        self.client.force_login(user=self.user)
        response = self.client.post(reverse('personal_data'), self.pers_data_attr, follow=True)
        self.assertContains(response, '<div class="form_success_message">')
        self.assertContains(response, "Your data has been updated successfully and a confirmation email has been "
                                      "sent to confirm your new email address.")


class ContactViewTestCase(TestCase):
    """
    Test cases for the Contact view.
    """

    def setUp(self):
        self.contact_attrs = {
            'phone_number': '+36991234567',
            'email': 'somebody@mail.com',
            'address': 'Happiness Street 1, HappyCity, 99999',
            'opening_hour_monday': '08:00:00',
            'closing_hour_monday': '17:30:00',
            'opening_hour_tuesday': '08:00:00',
            'closing_hour_tuesday': '17:30:00',
            'opening_hour_wednesday': '08:00:00',
            'closing_hour_wednesday': '17:30:00',
            'opening_hour_thursday': '08:00:00',
            'closing_hour_thursday': '17:30:00',
            'opening_hour_friday': '08:00:00',
            'closing_hour_friday': '17:30:00',
            'opening_hour_saturday': '09:00:00',
            'closing_hour_saturday': '13:30:00',
            'google_maps_url': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2726.2653641484812!2d19.65391067680947!3d46.89749933667435!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x4743d09cb06aa0cd%3A0xc162d3291067ef90!2sBennett%20Kft.%20Sz%C3%A9kt%C3%B3i%20kutyaszalon!5e0!3m2!1sen!2ses!4v1696190559457!5m2!1sen!2ses'
        }
        Contact.objects.create(**self.contact_attrs)

    def test_01_contact_rendering(self):
        """Tests that the contacat view is rendered successfully and the correct template is used."""
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'contact.html')

    def test_02_contact_details_displayed(self):
        """Tests that the contact information is displayed correctly."""
        response = self.client.get(reverse('contact'))
        self.assertContains(response, '<td>+36991234567</td>')
        self.assertContains(response, '<td>somebody@mail.com</td>')
        self.assertContains(response, '<td>Happiness Street 1, HappyCity, 99999</td>')
        self.assertContains(response,
                            'src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2726.2653641484812!2d19.65391067680947!3d46.89749933667435!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x4743d09cb06aa0cd%3A0xc162d3291067ef90!2sBennett%20Kft.%20Sz%C3%A9kt%C3%B3i%20kutyaszalon!5e0!3m2!1sen!2ses!4v1696190559457!5m2!1sen!2ses"')
        html_content = response.content.decode('utf-8')
        pattern = r'<td>(.*)Closed(.*)</td>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)
        pattern = r'<td>(.*)Sunday:(.*)</td>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)
        pattern = r'<td>(.*)Monday:(.*)</td>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_03_contact_details_none_when_no_data_in_database(self):
        """Tests that we provide None in the context data when there is no data found in the database."""
        with patch.object(Contact.objects, 'get', side_effect=Contact.DoesNotExist):
            contact_page = ContactPage()
            context = contact_page.get_context_data()
        self.assertIn('contact_details', context.keys())
        self.assertIsNone(context.get('contact_details'))

    def test_04_send_callback_request(self):
        """Tests sending a callback request from the Contact view."""
        response = self.client.post(reverse('contact'), {'call_me': 'call_me'}, follow=True)
        self.assertContains(response, '<div class="form_success_message"')
        self.assertContains(response, 'The callback request has been sent to the owner.')
        # to test that the message is only displayed when required
        response = self.client.post(reverse('contact'), {'dont_call_me': 'dont_call_me'}, follow=True)
        self.assertNotContains(response, 'The callback request has been sent to the owner.')


class GalleryViewTestCase(TestCase):
    """
    Test cases for the Gallery view.
    """

    def test_01_gallery_rendering(self):
        """Tests that the gallery view is rendered successfully and the correct template is used."""
        response = self.client.get(reverse('gallery'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'gallery.html')


class ServiceViewTestCase(TestCase):
    """
    Test cases for the Services and Service views.
    """

    def setUp(self):
        self.photo_path = os.path.join(settings.MEDIA_ROOT, 'services', 'default.jpg')
        with open(self.photo_path, 'rb') as photo_data:
            image = SimpleUploadedFile("image.jpg", photo_data.read(), content_type="image/jpeg")
        self.service_attrs = {
            'service_name_en': 'Service name EN',
            'service_name_hu': 'Service name HU',
            'price_default': 1000,
            'price_small': 750,
            'price_big': 1250,
            'service_description_en': 'Description in English for the service.',
            'service_description_hu': 'A szolgáltatás leírása magyarul.',
            'max_duration': 60,
            'photo': image,
            'active': True
        }
        self.service = Service.objects.create(**self.service_attrs)

    def tearDown(self):
        try:
            os.remove(self.service.photo.path)
        except:
            pass

    def _login(self):
        """Logs in a normal user."""
        self.client = Client()
        self.user = CustomUser.objects.create_user(username='user', password='test_password')
        self.client.force_login(user=self.user)

    def test_01_service_list_rendering(self):
        """Tests that the services view is rendered successfully and the correct template is used."""
        response = self.client.get(reverse('services'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'services.html')

    def test_02_service_box_is_displayed(self):
        """Tests that the service box is displayed indeed in the Services view."""
        response = self.client.get(reverse('services'))
        self.assertContains(response, '<div class="service_box">')
        html_content = response.content.decode('utf-8')
        pattern = r'<p class="service_box_name">(.*)Service name EN(.*)</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_03_service_rendering(self):
        """Tests that the service view is rendered successfully and the correct template is used."""
        response = self.client.get(reverse('service', args=(self.service.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'service.html')

    def test_04_service_is_displayed(self):
        """Tests that the service is indeed displayed successfully in the Service view."""
        response = self.client.get(reverse('service', args=(self.service.id,)))
        self.assertContains(response, '<div class="service">')
        html_content = response.content.decode('utf-8')
        pattern = r'<p class="service_name">(.*)Service name EN(.*)</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_05_booking_is_disabled_when_not_logged_in(self):
        """Tests that the booking option is not available for users not logged in."""
        response = self.client.get(reverse('service', args=(self.service.id,)))
        self.assertContains(response, '<div class="service">')
        html_content = response.content.decode('utf-8')
        pattern = r'<a class="a_button green_button(.*)disabled_button(.*)" href(.*)Book(.*)</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_06_booking_is_enabled_when_logged_in(self):
        """Tests that the booking option is available for users logged in."""
        self._login()
        response = self.client.get(reverse('service', args=(self.service.id,)))
        self.assertContains(response, '<div class="service">')
        html_content = response.content.decode('utf-8')
        pattern = r'<a class="a_button green_button(.*)disabled_button(.*)" href(.*)Book(.*)</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNone(match)
        pattern = r'<a class="a_button green_button( ?)" href(.*)Book(.*)</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_07_default_price_displayed(self):
        """Tests that by default the default price is displayed."""
        response = self.client.get(reverse('service', args=(self.service.id,)))
        html_content = response.content.decode('utf-8')
        pattern = r'<option value="medium" selected >medium</option>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)
        pattern = r'<p id="medium" class="service_price">1000 Ft</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)


class AdminAPIViewTestCase(TestCase):
    """
    Test cases for the Admin API view.
    """

    def _login(self, admin=True):
        """Logs in a superuser or a normal user."""
        self.client = Client()
        if admin:
            self.user = CustomUser.objects.create_superuser(username='admin', password='admin_password')
        else:
            self.user = CustomUser.objects.create_user(username='user', password='test_password')
        self.client.force_login(user=self.user)

    def test_01_not_displayed_when_not_staff(self):
        """Tests that the view is not displayed for users that are not staff or admin."""
        self._login(admin=False)
        response = self.client.get(reverse('admin_api'))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        html_content = response.content.decode('utf-8')
        pattern = r'<a class="menu_item" href="(.*)">Admin API</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNone(match)

    def test_02_displayed_when_staff(self):
        """Tests that the view is displayed only when the user is staff or admin."""
        self._login(admin=True)
        response = self.client.get(reverse('admin_api'))
        html_content = response.content.decode('utf-8')
        pattern = r'<a id="nav_admin_api" class="menu_item" href="(.*)">Admin API</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_03_admin_api_rendering(self):
        """Tests that the admin api view is rendered successfully and the correct template is used."""
        self._login(admin=True)
        response = self.client.get(reverse('admin_api'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'admin_api.html')

    def test_04_not_displayed_when_not_logged_in(self):
        """Tests that the view is not displayed when the user is not logged in."""
        response = self.client.get(reverse('admin_api'))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_05_service_update_destroy_button_disabled_when_no_selected(self):
        """Tests that the Update/Delete button is not enabled until a service is selected from the list."""
        self._login(admin=True)
        response = self.client.get(reverse('admin_api'))
        html_content = response.content.decode('utf-8')
        pattern = r'<a id="service_update_delete_button" class="a_button red_button" >(.*)Update/Delete</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_06_list_booking_slots_button_disabled_when_no_selected(self):
        """Tests that the Update/Delete button is not enabled until a service is selected from the list."""
        self._login(admin=True)
        response = self.client.get(reverse('admin_api'))
        html_content = response.content.decode('utf-8')
        pattern = r'<a id="available_booking_slots_button" class="a_button blue_button" >(.*)List Available Slots</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_07_cancel_user_button_disabled_when_no_selected(self):
        """Tests that the Cancel User button is not enabled until a user is selected from the list."""
        self._login(admin=True)
        response = self.client.get(reverse('admin_api'))
        html_content = response.content.decode('utf-8')
        pattern = r'<a id="cancel_user_button" class="a_button red_button" >(.*)Cancel User</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_08_admin_image_upload_to_gallery(self):
        """Tests uploading an image to the gallery from the Admin page."""
        request = Mock()
        request.method = 'POST'
        request.POST = {'image_upload_submit': ['Upload']}
        request.FILES = {'image_to_be_uploaded': 'image'}
        with patch.object(GalleryManager, 'upload_image_to_gallery', return_value=True) as mock_upload_image_to_gallery:
            with patch.object(messages, 'success') as mock_success_message:
                response = admin_api_page(request)
                mock_upload_image_to_gallery.assert_called_once()
                mock_success_message.assert_called_once()
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_09_admin_image_upload_to_gallery_with_no_file(self):
        """Tests the inaction of uploading an image to the gallery when there is no image in the request."""
        request = Mock()
        request.method = 'POST'
        request.POST = {'image_upload_submit': ['Upload']}
        request.FILES = {}
        with patch.object(GalleryManager, 'upload_image_to_gallery', return_value=True) as mock_upload_image_to_gallery:
            with patch.object(messages, 'success') as mock_success_message:
                with patch('dog_grooming_app.views.render') as mock_render:
                    response = admin_api_page(request)
                    mock_upload_image_to_gallery.assert_not_called()
                    mock_success_message.assert_not_called()
                    mock_render.assert_called_once()

    def test_10_admin_delete_image_from_gallery(self):
        """Tests deleting an image from the gallery from the Admin page."""
        request = Mock()
        request.method = 'POST'
        request.POST = {'image_delete_submit': ['Delete'], 'image_to_be_deleted': ['image.jpg']}
        with patch.object(GalleryManager, 'delete_image_from_gallery', return_value=None) \
                as mock_delete_image_from_gallery:
            with patch.object(messages, 'success') as mock_success_message:
                response = admin_api_page(request)
                mock_delete_image_from_gallery.assert_called_once()
                mock_success_message.assert_called_once()
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)


class BookingViewTestCase(TestCase):
    """
    Test cases for the Booking view.
    """

    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(username='user', password='test_password')
        self.admin_user = CustomUser.objects.create_superuser(username='admin', password='admin_password')
        self._create_contact()
        self.service = self._create_new_service()

    def _login(self):
        """Logs in a normal user."""
        self.client.logout()
        self.client.force_login(user=self.user)

    def _create_new_service(self):
        """Calls the API to create a new service. It uploads a photo too as it is required.
        At the end the photo is deleted."""
        self.client.force_login(user=self.admin_user)
        photo_path = os.path.join(settings.MEDIA_ROOT, 'services', 'default.jpg')
        service_attrs = {
            'service_name_en': 'Service name EN',
            'service_name_hu': 'Service name HU',
            'price_default': 1000,
            'price_small': 750,
            'price_big': 1250,
            'service_description_en': 'Description in English for the service.',
            'service_description_hu': 'A szolgáltatás leírása magyarul.',
            'max_duration': 60,
            'active': True
        }
        with open(photo_path, 'rb') as photo_data:
            service_attrs['photo'] = photo_data
            response = self.client.post(reverse('api_service_create'), service_attrs, format='multipart')
        try:
            created_service = Service.objects.last()
            os.remove(created_service.photo.path)
            return created_service
        except:
            return None

    def _create_contact(self):
        """Calls the API to create the contact details."""
        contact_attrs = {
            'phone_number': '+36991234567',
            'email': 'somebody@mail.com',
            'address': 'Happiness Street 1, HappyCity, 99999',
            'opening_hour_monday': '08:00:00',
            'closing_hour_monday': '17:30:00',
            'opening_hour_tuesday': '08:00:00',
            'closing_hour_tuesday': '17:30:00',
            'opening_hour_wednesday': '08:00:00',
            'closing_hour_wednesday': '17:30:00',
            'opening_hour_thursday': '08:00:00',
            'closing_hour_thursday': '17:30:00',
            'opening_hour_friday': '08:00:00',
            'closing_hour_friday': '17:30:00',
            'opening_hour_saturday': '09:00:00',
            'closing_hour_saturday': '13:30:00',
            'google_maps_url': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2726.2653641484812!2d19.65391067680947!3d46.89749933667435!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x4743d09cb06aa0cd%3A0xc162d3291067ef90!2sBennett%20Kft.%20Sz%C3%A9kt%C3%B3i%20kutyaszalon!5e0!3m2!1sen!2ses!4v1696190559457!5m2!1sen!2ses'
        }
        self.client.force_login(user=self.admin_user)
        return self.client.post(reverse('api_contact_create'), contact_attrs)

    def test_01_booking_rendering(self):
        """Tests that the booking view is rendered successfully and the correct template is used."""
        self._login()
        response = self.client.get(reverse('booking', args=(self.service.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'booking.html')

    def test_02_booking_when_not_logged_in(self):
        """Tests that the booking view is not available for users not logged in."""
        self.client.logout()
        response = self.client.get(reverse('booking', args=(self.service.id,)))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertRedirects(response, reverse('login') + '?next=' + reverse('booking', args=(self.service.id,)))

    def test_03_booking_not_available_without_comment(self):
        """Tests that the booking is not available without a comment."""
        self._login()
        self.client.get(reverse('booking', args=(self.service.id,)))
        response = self.client.post(reverse('booking', args=(self.service.id,)),
                                    {'dog_size': 'medium',
                                     'date': datetime.date.strftime(datetime.date.today() + datetime.timedelta(days=1),
                                                                    '%Y-%m-%d'),
                                     'time': '08:00',
                                     'comment': '',
                                     })
        self.assertContains(response, '<ul class="error_list">')
        self.assertContains(response, 'This field is required.')

    def test_04_booking_not_available_without_time(self):
        """Tests that the booking is not available without a valid time."""
        self._login()
        self.client.get(reverse('booking', args=(self.service.id,)))
        response = self.client.post(reverse('booking', args=(self.service.id,)),
                                    {'dog_size': 'medium',
                                     'date': datetime.date.strftime(datetime.date.today() + datetime.timedelta(days=1),
                                                                    '%Y-%m-%d'),
                                     'time': '',
                                     'comment': 'My dog is a Golden and I would like to have it bathed.',
                                     })
        self.assertContains(response, '<ul class="error_list">')
        self.assertContains(response, 'This field is required.')

    def test_05_successful_booking_with_message(self):
        """Tests that when the booking is successful, the correct success message is displayed."""
        self._login()
        self.client.get(reverse('booking', args=(self.service.id,)))
        response = self.client.post(reverse('booking', args=(self.service.id,)),
                                    {'dog_size': '',
                                     'date': datetime.date.strftime(datetime.date.today() + datetime.timedelta(days=1),
                                                                    '%Y-%m-%d'),
                                     'time': '08:00',
                                     'comment': 'My dog is a Golden and I would like to have it bathed.',
                                     }, follow=True)
        self.assertContains(response, '<div class="form_success_message">')
        self.assertContains(response, 'Your booking has been successful.')


class UserBookingsViewTestCase(TestCase):
    """
    Test cases for the User Bookings view.
    """

    def setUp(self):
        self.client = Client()
        self.admin_user = CustomUser.objects.create_superuser(username='admin', password='admin_password')
        self.user = CustomUser.objects.create_user(username='user', password='test_password')
        self._create_contact()
        self.service = self._create_new_service()
        self.booking = self._create_booking()

    def _login(self):
        """Logs in a normal user."""
        self.client.logout()
        self.client.force_login(user=self.user)

    def _create_new_service(self):
        """Calls the API to create a new service. It uploads a photo too as it is required.
        At the end the photo is deleted."""
        self.client.force_login(user=self.admin_user)
        photo_path = os.path.join(settings.MEDIA_ROOT, 'services', 'default.jpg')
        service_attrs = {
            'service_name_en': 'Service name EN',
            'service_name_hu': 'Service name HU',
            'price_default': 1000,
            'price_small': 750,
            'price_big': 1250,
            'service_description_en': 'Description in English for the service.',
            'service_description_hu': 'A szolgáltatás leírása magyarul.',
            'max_duration': 60,
            'active': True
        }
        with open(photo_path, 'rb') as photo_data:
            service_attrs['photo'] = photo_data
            response = self.client.post(reverse('api_service_create'), service_attrs, format='multipart')
        try:
            created_service = Service.objects.last()
            os.remove(created_service.photo.path)
            return created_service
        except:
            return None

    def _create_contact(self):
        """Calls the API to create the contact details."""
        contact_attrs = {
            'phone_number': '+36991234567',
            'email': 'somebody@mail.com',
            'address': 'Happiness Street 1, HappyCity, 99999',
            'opening_hour_monday': '08:00:00',
            'closing_hour_monday': '17:30:00',
            'opening_hour_tuesday': '08:00:00',
            'closing_hour_tuesday': '17:30:00',
            'opening_hour_wednesday': '08:00:00',
            'closing_hour_wednesday': '17:30:00',
            'opening_hour_thursday': '08:00:00',
            'closing_hour_thursday': '17:30:00',
            'opening_hour_friday': '08:00:00',
            'closing_hour_friday': '17:30:00',
            'opening_hour_saturday': '09:00:00',
            'closing_hour_saturday': '13:30:00',
            'google_maps_url': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2726.2653641484812!2d19.65391067680947!3d46.89749933667435!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x4743d09cb06aa0cd%3A0xc162d3291067ef90!2sBennett%20Kft.%20Sz%C3%A9kt%C3%B3i%20kutyaszalon!5e0!3m2!1sen!2ses!4v1696190559457!5m2!1sen!2ses'
        }
        self.client.force_login(user=self.admin_user)
        return self.client.post(reverse('api_contact_create'), contact_attrs)

    def _create_booking(self):
        """Calls the API to create a booking."""
        self.client.force_login(user=self.admin_user)
        booking_attrs = {
            'user': self.user,
            'service': self.service,
            'dog_size': 'big',
            'service_price': 5000,
            'date': datetime.date.strftime(datetime.date.today() + datetime.timedelta(days=1), '%Y-%m-%d'),
            'time': datetime.time.strftime(datetime.datetime.now().time(), '%H:%M:%S'),
            'comment': 'My dog is a Golden and I want it to have batched and its nails cut.',
            'cancelled': False
        }
        return Booking.objects.create(**booking_attrs)

    def test_01_user_bookings_rendering(self):
        """Tests that the user bookings view is rendered successfully and the correct template is used."""
        self._login()
        response = self.client.get(reverse('user_bookings'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'user_bookings.html')

    def test_02_user_bookings_when_not_logged_in(self):
        """Tests that the user bookings view is not available for users not logged in."""
        self.client.logout()
        response = self.client.get(reverse('user_bookings'))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertRedirects(response, reverse('login') + '?next=' + reverse('user_bookings'))

    def test_03_booking_box_is_displayed(self):
        """Tests that the booking box is displayed indeed in the User Bookings view."""
        self._login()
        response = self.client.get(reverse('user_bookings'))
        self.assertContains(response, '<div class="user_booking_box">')
        html_content = response.content.decode('utf-8')
        pattern = r'<p class="service_box_name">(.*)Service name EN(.*)</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_04_cancel_button_is_displayed(self):
        """Tests that the booking box is displayed indeed in the User Bookings view."""
        self._login()
        response = self.client.get(reverse('user_bookings'))
        html_content = response.content.decode('utf-8')
        pattern = r'<a class="a_button red_button" href(.*)>Cancel</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_05_booking_box_disappears_after_cancel(self):
        """Tests that the booking box disappears indeed after cancelling in the User Bookings view."""
        self._login()
        response = self.client.get(reverse('user_bookings'))
        self.assertContains(response, '<div class="user_booking_box">')
        html_content = response.content.decode('utf-8')
        pattern = r'<p class="service_box_name">(.*)Service name EN(.*)</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)
        response = self.client.get(reverse('api_cancel_booking', args=(self.booking.id,)), follow=True)
        html_content = response.content.decode('utf-8')
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertNotContains(response, '<div class="user_booking_box">')
        self.assertIsNone(match)

    def test_06_when_there_are_no_bookings(self):
        """Tests the User Bookings view when there are no bookings."""
        self._login()
        Booking.objects.all().delete()
        response = self.client.get(reverse('user_bookings'))
        self.assertContains(response, 'You have no bookings.')


class AdminBookingsViewTestCase(TestCase):
    """
    Test cases for the Admin Bookings view.
    """

    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(username='user', password='test_password')
        self.admin_user = CustomUser.objects.create_superuser(username='admin', password='admin_password')
        self._create_contact()
        self.service = self._create_new_service()
        self.booking = self._create_booking()

    def _login(self, admin=True):
        """Logs in a normal user."""
        self.client.logout()
        self.client.force_login(user=self.admin_user if admin else self.user)

    def _create_new_service(self):
        """Calls the API to create a new service. It uploads a photo too as it is required.
        At the end the photo is deleted."""
        self._login(admin=True)
        photo_path = os.path.join(settings.MEDIA_ROOT, 'services', 'default.jpg')
        service_attrs = {
            'service_name_en': 'Service name EN',
            'service_name_hu': 'Service name HU',
            'price_default': 1000,
            'price_small': 750,
            'price_big': 1250,
            'service_description_en': 'Description in English for the service.',
            'service_description_hu': 'A szolgáltatás leírása magyarul.',
            'max_duration': 60,
            'active': True
        }
        with open(photo_path, 'rb') as photo_data:
            service_attrs['photo'] = photo_data
            response = self.client.post(reverse('api_service_create'), service_attrs, format='multipart')
        try:
            created_service = Service.objects.last()
            os.remove(created_service.photo.path)
            return created_service
        except:
            return None

    def _create_contact(self):
        """Calls the API to create the contact details."""
        contact_attrs = {
            'phone_number': '+36991234567',
            'email': 'somebody@mail.com',
            'address': 'Happiness Street 1, HappyCity, 99999',
            'opening_hour_monday': '08:00:00',
            'closing_hour_monday': '17:30:00',
            'opening_hour_tuesday': '08:00:00',
            'closing_hour_tuesday': '17:30:00',
            'opening_hour_wednesday': '08:00:00',
            'closing_hour_wednesday': '17:30:00',
            'opening_hour_thursday': '08:00:00',
            'closing_hour_thursday': '17:30:00',
            'opening_hour_friday': '08:00:00',
            'closing_hour_friday': '17:30:00',
            'opening_hour_saturday': '09:00:00',
            'closing_hour_saturday': '13:30:00',
            'google_maps_url': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2726.2653641484812!2d19.65391067680947!3d46.89749933667435!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x4743d09cb06aa0cd%3A0xc162d3291067ef90!2sBennett%20Kft.%20Sz%C3%A9kt%C3%B3i%20kutyaszalon!5e0!3m2!1sen!2ses!4v1696190559457!5m2!1sen!2ses'
        }
        self._login(admin=True)
        return self.client.post(reverse('api_contact_create'), contact_attrs)

    def _create_booking(self, cancelled=False):
        """Calls the API to create a booking."""
        self._login(admin=False)
        booking_attrs = {
            'user': self.user,
            'service': self.service,
            'dog_size': 'big',
            'service_price': 5000,
            'date': datetime.date.strftime(datetime.date.today() + datetime.timedelta(days=1), '%Y-%m-%d'),
            'time': datetime.time.strftime(datetime.datetime.now().time(), '%H:%M:%S'),
            'comment': 'My dog is a Golden and I want it to have batched and its nails cut.',
            'cancelled': False
        }
        cancelled_booking_attrs = {
            'user': self.user,
            'service': self.service,
            'dog_size': 'big',
            'service_price': 5000,
            'date': datetime.date.strftime(datetime.date.today() + datetime.timedelta(days=2), '%Y-%m-%d'),
            'time': datetime.time.strftime(datetime.datetime.now().time(), '%H:%M:%S'),
            'comment': 'My dog is a Golden and I want it to have batched and its nails cut.',
            'cancelled': True
        }
        return Booking.objects.create(**(booking_attrs if not cancelled else cancelled_booking_attrs))

    def test_01_admin_bookings_rendering(self):
        """Tests that the admin bookings view is rendered successfully and the correct template is used."""
        self._login()
        response = self.client.get(reverse('admin_bookings'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'admin_bookings.html')

    def test_02_admin_bookings_when_not_logged_in(self):
        """Tests that the admin bookings view is not available for users not logged in."""
        self.client.logout()
        response = self.client.get(reverse('admin_bookings'))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertRedirects(response, reverse('login') + '?next=' + reverse('admin_bookings'))

    def test_03_admin_bookings_when_not_staff(self):
        """Tests that the admin bookings view is only available for staff users."""
        self._login(admin=False)
        response = self.client.get(reverse('admin_bookings'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_04_booking_box_is_displayed(self):
        """Tests that the booking box is displayed indeed in the Admin Bookings view."""
        self._login()
        response = self.client.get(reverse('admin_bookings'))
        self.assertContains(response, '<div class="admin_booking_box">')
        html_content = response.content.decode('utf-8')
        pattern = r'<p class="service_box_name">(.*)Service name EN(.*)</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_05_cancel_button_is_displayed(self):
        """Tests that the booking box is displayed indeed in the Admin Bookings view."""
        self._login()
        response = self.client.get(reverse('admin_bookings'))
        html_content = response.content.decode('utf-8')
        pattern = r'<a class="a_button red_button" href(.*)>Cancel</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_06_booking_box_disappears_after_cancel(self):
        """Tests that the booking box is displayed indeed in the Admin Bookings view."""
        self._login()
        response = self.client.get(reverse('admin_bookings'))
        self.assertContains(response, '<div class="admin_booking_box">')
        html_content = response.content.decode('utf-8')
        pattern = r'<p class="service_box_name">(.*)Service name EN(.*)</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)
        response = self.client.get(reverse('api_cancel_booking', args=(self.booking.id,)) + '?by_user=false',
                                   follow=True)
        html_content = response.content.decode('utf-8')
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertNotContains(response, '<div class="admin_booking_box">')
        self.assertIsNone(match)

    def test_07_admin_bookings_search_elements_displayed(self):
        """Tests that the search elements are displayed indeed in the Admin Bookings view."""
        self._login()
        response = self.client.get(reverse('admin_bookings'))
        self.assertContains(response, '<div id="admin_booking_search_form">')
        html_content = response.content.decode('utf-8')
        pattern = r'<input name="booking_date" id="booking_date" type="date" value="(.*)" />'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)
        pattern = r'<input name="cancelled" id="cancelled" type="checkbox" value="cancelled" (.*)/>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)
        self.assertContains(response, '<input name="submit_search" type="submit" value="Search"/>')
        self.assertContains(response, '<input name="submit_all" type="submit" value="All" />')

    def test_08_admin_booking_filter_on_cancelled_too(self):
        """Tests that the cancelled booking boxes are displayed as well in the Admin Bookings view."""
        self.cancelled_booking = self._create_booking(cancelled=True)
        self._login()
        response = self.client.post(reverse('admin_bookings'), {'cancelled': 'cancelled'}, follow=True)
        self.assertContains(response, '<div class="admin_booking_box">')
        html_content = response.content.decode('utf-8')
        pattern = r'<p style="color:red;">Cancelled</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)
        pattern = r'<a class="a_button red_button" href(.*)>Cancel</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_09_admin_booking_filter_on_active(self):
        """Tests that the cancelled booking boxes are displayed as well in the Admin Bookings view."""
        self.cancelled_booking = self._create_booking(cancelled=True)
        self._login()
        response = self.client.post(reverse('admin_bookings'), follow=True)
        self.assertContains(response, '<div class="admin_booking_box">')
        html_content = response.content.decode('utf-8')
        pattern = r'<p style="color:red;">Cancelled</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNone(match)
        pattern = r'<a class="a_button red_button" href(.*)>Cancel</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_10_admin_booking_filter_on_date(self):
        """Tests that the cancelled booking boxes are displayed as well in the Admin Bookings view."""
        self.cancelled_booking = self._create_booking(cancelled=True)
        self._login()
        response = self.client.post(reverse('admin_bookings'), {'booking_date':
                                                                    datetime.date.strftime(datetime.date.today() +
                                                                                           datetime.timedelta(days=1),
                                                                                           '%Y-%m-%d'),
                                                                'cancelled': 'cancelled',
                                                                'submit_search': 'Search'},
                                    follow=True)
        self.assertContains(response, '<div class="admin_booking_box">')
        # only the active booking should be available, based on the date
        html_content = response.content.decode('utf-8')
        pattern = r'<p style="color:red;">Cancelled</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNone(match)
        pattern = r'<a class="a_button red_button" href(.*)>Cancel</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_11_admin_booking_filter_on_date(self):
        """Tests that the cancelled booking boxes are displayed as well in the Admin Bookings view."""
        self.cancelled_booking = self._create_booking(cancelled=True)
        self._login()
        response = self.client.post(reverse('admin_bookings'), {'booking_date':
                                                                    datetime.date.strftime(datetime.date.today() +
                                                                                           datetime.timedelta(days=2),
                                                                                           '%Y-%m-%d'),
                                                                'cancelled': 'cancelled',
                                                                'submit_search': 'Search'},
                                    follow=True)
        self.assertContains(response, '<div class="admin_booking_box">')
        # only the cancelled booking should be available, based on the date
        html_content = response.content.decode('utf-8')
        pattern = r'<p style="color:red;">Cancelled</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)
        pattern = r'<a class="a_button red_button" href(.*)>Cancel</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNone(match)


class ModelsTestCase(TestCase):
    """
    Test cases for models.
    """

    def test_01_customuser_cancel_fails_with_save(self):
        """Tests that we return False when the user cancellation fails during the save method."""
        with patch.object(CustomUser, '__init__', return_value=None):
            with patch.object(CustomUser, 'save', side_effect=Error):
                cu = CustomUser()
                return_value = cu.cancel_user()
        self.assertFalse(return_value)

    def test_02_booking_cancel_fails_with_save(self):
        """Tests that we return False when the booking cancellation fails during the save method."""
        with patch.object(Booking, '__init__', return_value=None):
            with patch.object(Booking, 'save', side_effect=Error):
                booking = Booking()
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


class BookingManagerTestCase(TestCase):
    """
    Test cases for the Booking Manager.
    """

    def test_01_no_available_booking_slots(self):
        """Tests the return value when there are no available booking slots."""
        contact_mock = Mock()
        contact_mock.get_opening_hour_for_day = Mock(return_value=datetime.time(8, 0))
        contact_mock.get_closing_hour_for_day = Mock(return_value=datetime.time(9, 0))
        service_mock = Mock()
        service_mock.get_duration_of_service = Mock(return_value=(datetime.timedelta(minutes=120),
                                                                  datetime.timedelta(minutes=135)))
        with patch.object(Contact.objects, 'get', return_value=contact_mock):
            with patch.object(Service.objects, 'get', return_value=service_mock):
                available_slots = BookingManager.get_available_booking_slots('2023-12-12', 1)
        self.assertListEqual(available_slots, [('', 'No available slots')])

    def test_02_no_booking_slots_because_of_closed(self):
        """Tests the return value when there are no available booking slots because the salon is closed."""
        contact_mock = Mock()
        contact_mock.get_opening_hour_for_day = Mock(return_value=None)
        contact_mock.get_closing_hour_for_day = Mock(return_value=datetime.time(9, 0))
        with patch.object(Contact.objects, 'get', return_value=contact_mock):
            available_slots = BookingManager.get_available_booking_slots('2023-12-12', 1)
        self.assertListEqual(available_slots, [('', 'Closed')])

        contact_mock.get_opening_hour_for_day = Mock(return_value=datetime.time(8, 0))
        contact_mock.get_closing_hour_for_day = Mock(return_value=None)
        with patch.object(Contact.objects, 'get', return_value=contact_mock):
            available_slots = BookingManager.get_available_booking_slots('2023-12-12', 1)
        self.assertListEqual(available_slots, [('', 'Closed')])

        contact_mock.get_opening_hour_for_day = Mock(return_value=None)
        contact_mock.get_closing_hour_for_day = Mock(return_value=None)
        with patch.object(Contact.objects, 'get', return_value=contact_mock):
            available_slots = BookingManager.get_available_booking_slots('2023-12-12', 1)
        self.assertListEqual(available_slots, [('', 'Closed')])

    def test_03_available_booking_slots_with_no_other_booking(self):
        """Tests the return value when there are no other bookings for the same day."""
        contact_mock = Mock()
        contact_mock.get_opening_hour_for_day = Mock(return_value=datetime.time(8, 0))
        contact_mock.get_closing_hour_for_day = Mock(return_value=datetime.time(9, 0))
        service_mock = Mock()
        service_mock.get_duration_of_service = Mock(return_value=(datetime.timedelta(minutes=15),
                                                                  datetime.timedelta(minutes=30)))
        with patch.object(Contact.objects, 'get', return_value=contact_mock):
            with patch.object(Service.objects, 'get', return_value=service_mock):
                available_slots = BookingManager.get_available_booking_slots('2023-12-12', 1)
        self.assertListEqual(available_slots, [('08:00', '08:00 - 08:15'),
                                               ('08:15', '08:15 - 08:30'),
                                               ('08:30', '08:30 - 08:45'),
                                               ('08:45', '08:45 - 09:00')])

    def test_04_available_booking_slots_with_other_booking(self):
        """Tests the return value when there are other bookings for the same day."""
        contact_mock = Mock()
        contact_mock.get_opening_hour_for_day = Mock(return_value=datetime.time(8, 0))
        contact_mock.get_closing_hour_for_day = Mock(return_value=datetime.time(9, 0))
        service_mock = Mock()
        service_mock.get_duration_of_service = Mock(return_value=(datetime.timedelta(minutes=15),
                                                                  datetime.timedelta(minutes=30)))
        with patch.object(Contact.objects, 'get', return_value=contact_mock):
            with patch.object(Service.objects, 'get', return_value=service_mock):
                with patch.object(BookingManager, 'get_booked_time_slots', return_value=[(datetime.time(8, 15),
                                                                                          datetime.time(8, 45))]):
                    available_slots = BookingManager.get_available_booking_slots('2023-12-12', 1)
        self.assertListEqual(available_slots, [('08:45', '08:45 - 09:00')])

    def test_05_available_booking_slots_with_other_booking(self):
        """Tests the return value when there are other bookings for the same day."""
        contact_mock = Mock()
        contact_mock.get_opening_hour_for_day = Mock(return_value=datetime.time(8, 0))
        contact_mock.get_closing_hour_for_day = Mock(return_value=datetime.time(10, 0))
        service_mock = Mock()
        service_mock.get_duration_of_service = Mock(return_value=(datetime.timedelta(minutes=15),
                                                                  datetime.timedelta(minutes=30)))
        with patch.object(Contact.objects, 'get', return_value=contact_mock):
            with patch.object(Service.objects, 'get', return_value=service_mock):
                with patch.object(BookingManager, 'get_booked_time_slots', return_value=[(datetime.time(8, 45),
                                                                                          datetime.time(9, 15))]):
                    available_slots = BookingManager.get_available_booking_slots('2023-12-12', 1)
        self.assertListEqual(available_slots, [('08:00', '08:00 - 08:15'),
                                               ('08:15', '08:15 - 08:30'),
                                               ('09:15', '09:15 - 09:30'),
                                               ('09:30', '09:30 - 09:45'),
                                               ('09:45', '09:45 - 10:00')])


class GalleryManagerTestCase(TestCase):
    """
    Test cases for the Gallery Manager.
    """

    @patch('builtins.open', mock_open())
    def test_01_upload_image_to_gallery(self):
        """Tests uploading the photo into the gallery."""
        image = Mock()
        image.name = 'image.jpg'
        image.chunks = lambda: [list() for _ in range(3)]
        return_value = GalleryManager.upload_image_to_gallery(image)
        self.assertTrue(return_value)

    def test_02_upload_image_to_gallery_fails(self):
        """Tests when uploading a photo to the gallery fails."""
        mo = mock_open()
        with patch('builtins.open', mo) as mocked_open:
            mocked_open.side_effect = FileNotFoundError
            image = Mock()
            image.name = 'image'
            return_value = GalleryManager.upload_image_to_gallery(image)
        self.assertFalse(return_value)

    def test_03_get_gallery_images(self):
        """Tests getting the image list from the gallery."""
        images = GalleryManager.get_gallery_image_list()
        self.assertNotIn('.gitkeep', images)
        self.assertIsInstance(images, list)

    def test_04_delete_image_from_gallery(self):
        """Tests deleting an image from the gallery."""
        image = 'image.jpg'
        with patch.object(os, 'listdir', return_value=[image]):
            with patch.object(os.path, 'isfile', return_value=True):
                with patch.object(os, 'remove', return_value=None):
                    GalleryManager.delete_image_from_gallery(image)
                    os.listdir.assert_called_once()
                    os.path.isfile.assert_called_once()
                    os.remove.assert_called_once()
