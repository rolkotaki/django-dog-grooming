import os
import copy
import re
import datetime
from rest_framework import status
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.translation import gettext as _
from django.contrib import messages
from unittest.mock import Mock, patch

import dog_grooming_app.utils.constants
from dog_grooming_app.models import CustomUser, Contact, Service, Booking
from dog_grooming_app.views import ContactPage, admin_page
from dog_grooming_app.utils.GalleryManager import GalleryManager
from dog_grooming_app.utils.constants import SERVICES_PER_PAGE, BOOKINGS_PER_PAGE, GALLERY_IMAGES_PER_PAGE, PAGINATION_PAGES


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

    def test_02_pagination_not_displayed(self):
        """Tests that the pagination is not displayed when we have no more items than the maximum allowed on a page."""
        response = self.client.get(reverse('gallery'))
        self.assertNotContains(response, '<div class="pagination">')

    def test_03_pagination_pages(self):
        """Tests that the pagination is displayed when we have more items than the maximum allowed on a page."""
        with patch.object(dog_grooming_app.views.GalleryPage, '__init__', return_value=None):
            mock_gallery = dog_grooming_app.views.GalleryPage()
            mock_gallery.request = Mock()
            mock_gallery.request.GET = {'page': 1}
            images = ['{}.jpg'.format(i) for i in range(GALLERY_IMAGES_PER_PAGE)]
            with patch.object(GalleryManager, 'get_gallery_image_list', return_value=images):
                context = mock_gallery.get_context_data()
                self.assertListEqual(context['pages'], [1])
                self.assertListEqual(context['images'], images)

            mock_gallery.request.GET = {'page': 1}
            images = ['{}.jpg'.format(i) for i in range(GALLERY_IMAGES_PER_PAGE + 1)]
            with patch.object(GalleryManager, 'get_gallery_image_list', return_value=images):
                context = mock_gallery.get_context_data()
                self.assertListEqual(context['pages'], [1, 2])
                self.assertListEqual(context['images'], images[:GALLERY_IMAGES_PER_PAGE])
            mock_gallery.request.GET = {'page': 2}
            with patch.object(GalleryManager, 'get_gallery_image_list', return_value=images):
                context = mock_gallery.get_context_data()
                self.assertListEqual(context['pages'], [1, 2])
                self.assertListEqual(context['images'], images[GALLERY_IMAGES_PER_PAGE:])

            mock_gallery.request.GET = {'page': 2}
            images = ['{}.jpg'.format(i) for i in range(GALLERY_IMAGES_PER_PAGE * PAGINATION_PAGES + 1)]
            with patch.object(GalleryManager, 'get_gallery_image_list', return_value=images):
                context = mock_gallery.get_context_data()
                self.assertListEqual(context['pages'], [i for i in range(1, PAGINATION_PAGES + 1)])
                self.assertListEqual(context['images'], images[GALLERY_IMAGES_PER_PAGE:GALLERY_IMAGES_PER_PAGE * 2])
            mock_gallery.request.GET = {'page': PAGINATION_PAGES}
            with patch.object(GalleryManager, 'get_gallery_image_list', return_value=images):
                context = mock_gallery.get_context_data()
                self.assertListEqual(context['pages'], [i for i in range(2, PAGINATION_PAGES + 2)])
                self.assertListEqual(context['images'], images[GALLERY_IMAGES_PER_PAGE * (PAGINATION_PAGES - 1):
                                                               GALLERY_IMAGES_PER_PAGE * PAGINATION_PAGES])

            page = int(PAGINATION_PAGES / 2) + 1
            mock_gallery.request.GET = {'page': page}
            images = ['{}.jpg'.format(i) for i in range(GALLERY_IMAGES_PER_PAGE * (PAGINATION_PAGES + 1) + 1)]
            with patch.object(GalleryManager, 'get_gallery_image_list', return_value=images):
                context = mock_gallery.get_context_data()
                self.assertListEqual(context['pages'], [i for i in range(1, PAGINATION_PAGES + 1)])
                self.assertListEqual(context['images'], images[GALLERY_IMAGES_PER_PAGE * (page - 1):
                                                               GALLERY_IMAGES_PER_PAGE * page])


class ServiceViewTestCase(TestCase):
    """
    Test cases for the Services and Service views.
    """

    def _create_service(self):
        photo_path = os.path.join(settings.MEDIA_ROOT, 'services', 'default.jpg')
        with open(photo_path, 'rb') as photo_data:
            image = SimpleUploadedFile("image.jpg", photo_data.read(), content_type="image/jpeg")
        service_attrs = {
            'service_name_en': 'Service name EN {}'.format(Service.objects.count()),
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
        return Service.objects.create(**service_attrs)

    def setUp(self):
        self.service = self._create_service()

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
        response = self.client.get(reverse('service', args=(self.service.slug,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'service.html')

    def test_04_service_is_displayed(self):
        """Tests that the service is indeed displayed successfully in the Service view."""
        response = self.client.get(reverse('service', args=(self.service.slug,)))
        self.assertContains(response, '<div class="service">')
        html_content = response.content.decode('utf-8')
        pattern = r'<p class="service_name">(.*)Service name EN(.*)</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_05_booking_is_disabled_when_not_logged_in(self):
        """Tests that the booking option is not available for users not logged in."""
        response = self.client.get(reverse('service', args=(self.service.slug,)))
        self.assertContains(response, '<div class="service">')
        html_content = response.content.decode('utf-8')
        pattern = r'<a class="a_button green_button(.*)disabled_button(.*)" href(.*)Book(.*)</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_06_booking_is_enabled_when_logged_in(self):
        """Tests that the booking option is available for users logged in."""
        self._login()
        response = self.client.get(reverse('service', args=(self.service.slug,)))
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
        response = self.client.get(reverse('service', args=(self.service.slug,)))
        html_content = response.content.decode('utf-8')
        pattern = r'<option value="medium" selected >medium</option>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)
        pattern = r'<p id="medium" class="service_price">1000 Ft</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_08_pagination_not_displayed(self):
        """Tests that the pagination is not displayed when we have no more items than the maximum allowed on a page."""
        response = self.client.get(reverse('services'))
        self.assertNotContains(response, '<div class="pagination">')

    def test_09_pagination_is_displayed(self):
        """Tests that the pagination is displayed when we have more items than the maximum allowed on a page."""
        for i in range(SERVICES_PER_PAGE):
            self._create_service()  # so that we have one more service than the maximum allowed on a page
        response = self.client.get(reverse('services'))
        self.assertContains(response, '<div class="pagination">')
        self.assertContains(response, '<a class="page_link" href="?page=2">last &raquo;</a>')
        self.assertNotContains(response, '<a class="page_link" href="?page=1">&laquo; first</a>')

    def test_10_pagination_links_are_correct(self):
        """Tests that the pagination links are all displayed correctly."""
        for i in range(SERVICES_PER_PAGE * PAGINATION_PAGES):
            self._create_service()
        response = self.client.get(reverse('services'), {'page': 2})
        self.assertContains(response, '<div class="pagination">')
        self.assertContains(response, '<a class="page_link" href="?page={}">last &raquo;</a>'.format(
            PAGINATION_PAGES + 1))
        self.assertContains(response, '<a class="page_link" href="?page=1">&laquo; first</a>')
        self.assertContains(response, '<span class="current_page">2</span>')

        response = self.client.get(reverse('services'), {'page': PAGINATION_PAGES})
        self.assertContains(response, '<div class="pagination">')
        self.assertContains(response, '<a class="page_link" href="?page={}">last &raquo;</a>'.format(
            PAGINATION_PAGES + 1))
        self.assertContains(response, '<a class="page_link" href="?page=1">&laquo; first</a>')
        self.assertContains(response, '<span class="current_page">{}</span>'.format(PAGINATION_PAGES))

        response = self.client.get(reverse('services'))
        self.assertContains(response, '<div class="pagination">')
        self.assertContains(response, '<a class="page_link" href="?page={}">last &raquo;</a>'.format(
            PAGINATION_PAGES + 1))
        self.assertNotContains(response, '<a class="page_link" href="?page=1">&laquo; first</a>')

        response = self.client.get(reverse('services'), {'page': PAGINATION_PAGES + 1})
        self.assertContains(response, '<div class="pagination">')
        self.assertNotContains(response, '<a class="page_link" href="?page={}">last &raquo;</a>'.format(
            PAGINATION_PAGES + 1))
        self.assertContains(response, '<a class="page_link" href="?page=1">&laquo; first</a>')


class AdminViewTestCase(TestCase):
    """
    Test cases for the Admin view.
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
        response = self.client.get(reverse('admin_page'))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        html_content = response.content.decode('utf-8')
        pattern = r'<a class="menu_item" href="(.*)">Admin</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNone(match)

    def test_02_displayed_when_staff(self):
        """Tests that the view is displayed only when the user is staff or admin."""
        self._login(admin=True)
        response = self.client.get(reverse('admin_page'))
        html_content = response.content.decode('utf-8')
        pattern = r'<a id="nav_admin_page" class="menu_item" href="(.*)">Admin</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_03_admin_page_rendering(self):
        """Tests that the admin view is rendered successfully and the correct template is used."""
        self._login(admin=True)
        response = self.client.get(reverse('admin_page'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'admin_page.html')

    def test_04_not_displayed_when_not_logged_in(self):
        """Tests that the view is not displayed when the user is not logged in."""
        response = self.client.get(reverse('admin_page'))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_05_service_update_destroy_button_disabled_when_no_selected(self):
        """Tests that the Update/Delete button is not enabled until a service is selected from the list."""
        self._login(admin=True)
        response = self.client.get(reverse('admin_page'))
        html_content = response.content.decode('utf-8')
        pattern = r'<a id="service_update_delete_button" class="a_button red_button" >(.*)Update/Delete</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_06_list_booking_slots_button_disabled_when_no_selected(self):
        """Tests that the Update/Delete button is not enabled until a service is selected from the list."""
        self._login(admin=True)
        response = self.client.get(reverse('admin_page'))
        html_content = response.content.decode('utf-8')
        pattern = r'<a id="available_booking_slots_button" class="a_button blue_button" >(.*)List Available Slots</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_07_cancel_user_button_disabled_when_no_selected(self):
        """Tests that the Cancel User button is not enabled until a user is selected from the list."""
        self._login(admin=True)
        response = self.client.get(reverse('admin_page'))
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
                response = admin_page(request)
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
                    response = admin_page(request)
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
                response = admin_page(request)
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
        self.client.force_login(user=self.admin_user)
        return self.client.post(reverse('api_contact_create'), contact_attrs)

    def test_01_booking_rendering(self):
        """Tests that the booking view is rendered successfully and the correct template is used."""
        self._login()
        response = self.client.get(reverse('booking', args=(self.service.slug,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'booking.html')

    def test_02_booking_when_not_logged_in(self):
        """Tests that the booking view is not available for users not logged in."""
        self.client.logout()
        response = self.client.get(reverse('booking', args=(self.service.slug,)))
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertRedirects(response, reverse('login') + '?next=' + reverse('booking', args=(self.service.slug,)))

    def test_03_booking_not_available_without_comment(self):
        """Tests that the booking is not available without a comment."""
        self._login()
        self.client.get(reverse('booking', args=(self.service.slug,)))
        response = self.client.post(reverse('booking', args=(self.service.slug,)),
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
        self.client.get(reverse('booking', args=(self.service.slug,)))
        response = self.client.post(reverse('booking', args=(self.service.slug,)),
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
        self.client.get(reverse('booking', args=(self.service.slug,)))
        response = self.client.post(reverse('booking', args=(self.service.slug,)),
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
        pattern = r'<a class="a_button red_button" onclick="return confirmCancel\((.*)\)\;" href(.*)>Cancel</a>'
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

    def test_07_pagination_not_displayed(self):
        """Tests that the pagination is not displayed when we have no more items than the maximum allowed on a page."""
        self._login()
        response = self.client.get(reverse('user_bookings'))
        self.assertNotContains(response, '<div class="pagination">')

    def test_08_pagination_is_displayed(self):
        """Tests that the pagination is displayed when we have more items than the maximum allowed on a page."""
        for i in range(BOOKINGS_PER_PAGE):
            self._create_booking()  # so that we have one more booking than the maximum allowed on a page
        self._login()
        response = self.client.get(reverse('user_bookings'))
        self.assertContains(response, '<div class="pagination">')
        self.assertContains(response, '<a class="page_link" href="?page=2">last &raquo;</a>')
        self.assertNotContains(response, '<a class="page_link" href="?page=1">&laquo; first</a>')

    def test_09_pagination_links_are_correct(self):
        """Tests that the pagination links are all displayed correctly."""
        for i in range(BOOKINGS_PER_PAGE * PAGINATION_PAGES):
            self._create_booking()
        self._login()
        response = self.client.get(reverse('user_bookings'), {'page': 2})
        self.assertContains(response, '<div class="pagination">')
        self.assertContains(response, '<a class="page_link" href="?page={}">last &raquo;</a>'.format(
            PAGINATION_PAGES + 1))
        self.assertContains(response, '<a class="page_link" href="?page=1">&laquo; first</a>')
        self.assertContains(response, '<span class="current_page">2</span>')

        response = self.client.get(reverse('user_bookings'), {'page': PAGINATION_PAGES})
        self.assertContains(response, '<div class="pagination">')
        self.assertContains(response, '<a class="page_link" href="?page={}">last &raquo;</a>'.format(
            PAGINATION_PAGES + 1))
        self.assertContains(response, '<a class="page_link" href="?page=1">&laquo; first</a>')
        self.assertContains(response, '<span class="current_page">{}</span>'.format(PAGINATION_PAGES))

        response = self.client.get(reverse('user_bookings'))
        self.assertContains(response, '<div class="pagination">')
        self.assertContains(response, '<a class="page_link" href="?page={}">last &raquo;</a>'.format(
            PAGINATION_PAGES + 1))
        self.assertNotContains(response, '<a class="page_link" href="?page=1">&laquo; first</a>')

        response = self.client.get(reverse('user_bookings'), {'page': PAGINATION_PAGES + 1})
        self.assertContains(response, '<div class="pagination">')
        self.assertNotContains(response, '<a class="page_link" href="?page={}">last &raquo;</a>'.format(
            PAGINATION_PAGES + 1))
        self.assertContains(response, '<a class="page_link" href="?page=1">&laquo; first</a>')


class AdminBookingsViewTestCase(TestCase):
    """
    Test cases for the Admin Bookings view.
    """

    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(username='user', password='test_password', first_name='first_name',
                                                   last_name='last_name')
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
        pattern = r'<a class="a_button red_button" onclick="return confirmCancel\((.*)\)\;" href(.*)>Cancel</a>'
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
        pattern = r'<input name="user" id="user" type="text" (.*)/>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)
        self.assertContains(response, '<input name="submit_search" type="submit" value="Search"/>')
        self.assertContains(response, '<input name="submit_all" type="submit" value="All" />')

    def test_08_admin_booking_filter_on_cancelled_too(self):
        """Tests that the filtering on cancelled bookings works well in the Admin Bookings view."""
        self.cancelled_booking = self._create_booking(cancelled=True)
        self._login()
        response = self.client.post(reverse('admin_bookings'), {'cancelled': 'cancelled'}, follow=True)
        self.assertContains(response, '<div class="admin_booking_box">')
        html_content = response.content.decode('utf-8')
        pattern = r'<p style="color:red;">Cancelled</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)
        pattern = r'<a class="a_button red_button" onclick="return confirmCancel\((.*)\)\;" href(.*)>Cancel</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_09_admin_booking_filter_on_active(self):
        """Tests that the filtering on active bookings works well in the Admin Bookings view."""
        self.cancelled_booking = self._create_booking(cancelled=True)
        self._login()
        response = self.client.post(reverse('admin_bookings'), follow=True)
        self.assertContains(response, '<div class="admin_booking_box">')
        html_content = response.content.decode('utf-8')
        pattern = r'<p style="color:red;">Cancelled</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNone(match)
        pattern = r'<a class="a_button red_button" onclick="return confirmCancel\((.*)\)\;" href(.*)>Cancel</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_10_admin_booking_filter_on_date(self):
        """Tests that the filtering on the date works well in the Admin Bookings view."""
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
        # both bookings should be available, as we display everything from the given day on
        html_content = response.content.decode('utf-8')
        pattern = r'<p style="color:red;">Cancelled</p>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)
        pattern = r'<a class="a_button red_button" onclick="return confirmCancel\((.*)\)\;" href(.*)>Cancel</a>'
        match = re.search(pattern, html_content, re.DOTALL | re.IGNORECASE)
        self.assertIsNotNone(match)

    def test_11_admin_booking_filter_on_date(self):
        """Tests that the filtering on the date works well in the Admin Bookings view."""
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

    def test_12_admin_booking_filter_on_user_id(self):
        """Tests that the filtering on the user works well in the Admin Bookings view."""
        self._login()
        # should return the booking, by user ID
        response = self.client.post(reverse('admin_bookings'), {'user': self.user.pk,
                                                                'submit_search': 'Search'},
                                    follow=True)
        self.assertContains(response, '<div class="admin_booking_box">')
        # should not return the booking
        response = self.client.post(reverse('admin_bookings'), {'user': self.user.pk + 1,
                                                                'submit_search': 'Search'},
                                    follow=True)
        self.assertNotContains(response, '<div class="admin_booking_box">')

        # should return the booking, by username
        response = self.client.post(reverse('admin_bookings'), {'user': 'user',
                                                                'submit_search': 'Search'},
                                    follow=True)
        self.assertContains(response, '<div class="admin_booking_box">')
        # should not return the booking
        response = self.client.post(reverse('admin_bookings'), {'user': 'someone',
                                                                'submit_search': 'Search'},
                                    follow=True)
        self.assertNotContains(response, '<div class="admin_booking_box">')

        # should return the booking, by first name
        response = self.client.post(reverse('admin_bookings'), {'user': 'first',
                                                                'submit_search': 'Search'},
                                    follow=True)
        self.assertContains(response, '<div class="admin_booking_box">')
        # should not return the booking
        response = self.client.post(reverse('admin_bookings'), {'user': 'noexist',
                                                                'submit_search': 'Search'},
                                    follow=True)
        self.assertNotContains(response, '<div class="admin_booking_box">')

        # should return the booking, by last name
        response = self.client.post(reverse('admin_bookings'), {'user': 'last',
                                                                'submit_search': 'Search'},
                                    follow=True)
        self.assertContains(response, '<div class="admin_booking_box">')
        # should not return the booking
        response = self.client.post(reverse('admin_bookings'), {'user': 'middlename',
                                                                'submit_search': 'Search'},
                                    follow=True)
        self.assertNotContains(response, '<div class="admin_booking_box">')

    def test_13_admin_booking_filter_on_everything(self):
        """Tests that the filtering on bookings works well in the Admin Bookings view."""
        self._login()
        # should return the booking
        response = self.client.post(reverse('admin_bookings'), {'booking_date':
                                                                    datetime.date.strftime(datetime.date.today() +
                                                                                           datetime.timedelta(days=1),
                                                                                           '%Y-%m-%d'),
                                                                'user': 'user',
                                                                'cancelled': 'cancelled',
                                                                'submit_search': 'Search'},
                                    follow=True)
        self.assertContains(response, '<div class="admin_booking_box">')

        # should not return the booking
        response = self.client.post(reverse('admin_bookings'), {'booking_date':
                                                                    datetime.date.strftime(datetime.date.today() +
                                                                                           datetime.timedelta(days=2),
                                                                                           '%Y-%m-%d'),
                                                                'user': 'user',
                                                                'cancelled': 'cancelled',
                                                                'submit_search': 'Search'},
                                    follow=True)
        self.assertNotContains(response, '<div class="admin_booking_box">')

        response = self.client.post(reverse('admin_bookings'), {'booking_date':
                                                                    datetime.date.strftime(datetime.date.today() +
                                                                                           datetime.timedelta(days=1),
                                                                                           '%Y-%m-%d'),
                                                                'user': 'noone',
                                                                'cancelled': 'cancelled',
                                                                'submit_search': 'Search'},
                                    follow=True)
        self.assertNotContains(response, '<div class="admin_booking_box">')

    def test_14_pagination_not_displayed(self):
        """Tests that the pagination is not displayed when we have no more items than the maximum allowed on a page."""
        self._login()
        response = self.client.get(reverse('admin_bookings'))
        self.assertNotContains(response, '<div class="pagination">')

    def test_15_pagination_is_displayed(self):
        """Tests that the pagination is displayed when we have more items than the maximum allowed on a page."""
        for i in range(BOOKINGS_PER_PAGE):
            self._create_booking()  # so that we have one more booking than the maximum allowed on a page
        self._login()
        response = self.client.get(reverse('admin_bookings'))
        self.assertContains(response, '<div class="pagination">')
        self.assertContains(response, '<a class="page_link" href="?page=2">last &raquo;</a>')
        self.assertNotContains(response, '<a class="page_link" href="?page=1">&laquo; first</a>')

    def test_16_pagination_links_are_correct(self):
        """Tests that the pagination links are all displayed correctly."""
        for i in range(BOOKINGS_PER_PAGE * PAGINATION_PAGES):
            self._create_booking()
        self._login()
        response = self.client.get(reverse('admin_bookings'), {'page': 2})
        self.assertContains(response, '<div class="pagination">')
        self.assertContains(response, '<a class="page_link" href="?page={}">last &raquo;</a>'.format(
            PAGINATION_PAGES + 1))
        self.assertContains(response, '<a class="page_link" href="?page=1">&laquo; first</a>')
        self.assertContains(response, '<span class="current_page">2</span>')

        response = self.client.get(reverse('admin_bookings'), {'page': PAGINATION_PAGES})
        self.assertContains(response, '<div class="pagination">')
        self.assertContains(response, '<a class="page_link" href="?page={}">last &raquo;</a>'.format(
            PAGINATION_PAGES + 1))
        self.assertContains(response, '<a class="page_link" href="?page=1">&laquo; first</a>')
        self.assertContains(response, '<span class="current_page">{}</span>'.format(PAGINATION_PAGES))

        response = self.client.get(reverse('admin_bookings'))
        self.assertContains(response, '<div class="pagination">')
        self.assertContains(response, '<a class="page_link" href="?page={}">last &raquo;</a>'.format(
            PAGINATION_PAGES + 1))
        self.assertNotContains(response, '<a class="page_link" href="?page=1">&laquo; first</a>')

        response = self.client.get(reverse('admin_bookings'), {'page': PAGINATION_PAGES + 1})
        self.assertContains(response, '<div class="pagination">')
        self.assertNotContains(response, '<a class="page_link" href="?page={}">last &raquo;</a>'.format(
            PAGINATION_PAGES + 1))
        self.assertContains(response, '<a class="page_link" href="?page=1">&laquo; first</a>')
