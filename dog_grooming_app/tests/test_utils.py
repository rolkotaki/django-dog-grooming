import os
import datetime
from django.test import TestCase
from unittest.mock import Mock, patch, mock_open

from dog_grooming_app.models import Contact, Service
from dog_grooming_app.utils.BookingManager import BookingManager
from dog_grooming_app.utils.GalleryManager import GalleryManager


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
