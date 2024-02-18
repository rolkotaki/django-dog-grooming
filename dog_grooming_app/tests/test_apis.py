import os
import datetime
from rest_framework.test import APITestCase
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.urls import reverse
from django.conf import settings
from unittest.mock import Mock, patch

from dog_grooming_app.models import CustomUser, Contact, Service, Booking
from dog_grooming_app.api_views import CancelUser, CancelBooking, ListAvailableBookingSlots, \
    ServiceRetrieveUpdateDestroy


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
            self.service_attrs['service_name_en'] = 'Service name EN {}'.format(Service.objects.count())
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

    def test_08_list_all_services(self):
        """Tests listing all the services, using the API."""
        self.service_attrs['active'] = True
        self._send_create_request()
        self.service_attrs['active'] = False
        self._send_create_request()
        services_count = Service.objects.count()
        response = self.client.get(reverse('api_services'))
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(response.data['count'], services_count)
        self.assertEqual(len(response.data['results']), services_count)

    def test_09_list_only_active_services(self):
        """Tests listing only the active services."""
        self.service_attrs['active'] = True
        self._send_create_request()
        self.service_attrs['active'] = False
        self._send_create_request()
        self._send_create_request()
        response = self.client.get(reverse('api_services'), {'active': True})
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)

    def test_10_list_only_inactive_services(self):
        """Tests listing only the inactive services."""
        self.service_attrs['active'] = True
        self._send_create_request()
        self.service_attrs['active'] = False
        self._send_create_request()
        self._send_create_request()
        response = self.client.get(reverse('api_services'), {'active': False})
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

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
            'service_name_en': 'Service name EN {}'.format(Service.objects.count()),
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
