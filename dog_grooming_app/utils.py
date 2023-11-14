import datetime
import os
from typing import List, Tuple
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

from .models import Booking, Contact, Service
from .constants import BOOKING_SLOT_SEARCH_TIME_INTERVAL


class BookingManager:
    """
    The BookingManager class has static methods to manage bookings, such as returning the available booking time slots.
    """

    @classmethod
    def get_booked_time_slots(cls, day: datetime.date, duration_with_break: datetime.timedelta) \
            -> List[Tuple[datetime.time, datetime.time]]:
        """
        Returns the booked time slots for a given day.
        Returns a list of tuples where each tuple contains the start and end time of the booking.
        The required break after the service is included in the returned end times.
        """
        bookings = Booking.objects.filter(date=day).order_by('time')
        return [(booking.time, (datetime.datetime.combine(day, booking.time) + duration_with_break).time())
                for booking in bookings]

    @classmethod
    def get_available_booking_slots(cls, day: [datetime.date, str], service_id: int) -> List[Tuple[str, str]]:
        """
        Returns the list of available time slots that can be booked on a given day.
        :param day: The day for which we want to retrieve the available slots that can be booked.
        :param service_id: The ID of the service that is being booked.
        :return: List of tuples with the value and the text of the option HTML tag in the dropdown list.
        """
        available_booking_slots = list()
        booking_day = datetime.datetime.strptime(day, '%Y-%m-%d').date() if isinstance(day, str) else day
        # retrieving the opening and closing hours
        contact_details = Contact.objects.get(id='x')
        opening_hour = contact_details.get_opening_hour_for_day(booking_day.weekday())
        closing_hour = contact_details.get_closing_hour_for_day(booking_day.weekday())

        # if there is no opening or closing time, then we return closed
        if not opening_hour or not closing_hour:
            return [('', _('Closed'))]

        # retrieving the duration of the service
        duration_without_break, duration_with_break = Service.objects.get(id=service_id).get_duration_of_service()

        # retrieving the booked slots for the given day
        booked_slots = cls.get_booked_time_slots(booking_day, duration_with_break)

        # looping through the available time slots and checking if it coincides with any existing booking
        # if not, we add it to the list to be returned
        cur_time = opening_hour
        while (datetime.datetime.combine(booking_day, cur_time) + duration_without_break).time() <= closing_hour:
            timeslot_available = True
            cur_time_with_duration = (datetime.datetime.combine(booking_day, cur_time) + duration_with_break).time()
            for booked_slot in booked_slots:
                if (booked_slot[0] <= cur_time < booked_slot[1]) or \
                        (booked_slot[0] < cur_time_with_duration <= booked_slot[1]):
                    timeslot_available = False
                    break
            # if the timeslot is available, we append it to the list to be returned
            if timeslot_available:
                available_booking_slots.append((datetime.time.strftime(cur_time, '%H:%M'),
                                     "{} - {}".format(datetime.time.strftime(cur_time, '%H:%M'),
                                                      datetime.time.strftime(
                                                          (datetime.datetime.combine(booking_day, cur_time) +
                                                           duration_without_break).time(),
                                                          '%H:%M'))))
            # we increase the current time by the booking slot search time interval
            cur_time = (datetime.datetime.combine(booking_day, cur_time) +
                        datetime.timedelta(minutes=BOOKING_SLOT_SEARCH_TIME_INTERVAL)).time()
        if len(available_booking_slots) == 0:
            return [('', _('No available slots'))]
        return available_booking_slots


class GalleryManager:
    """
    The GalleryManager class has class methods to manage the Gallery, such as uploading and deleting photos and
    fetching the image list in the gallery.
    """

    @classmethod
    def upload_image_to_gallery(cls, image: InMemoryUploadedFile) -> bool:
        """
        Uploads an image to the gallery folder.
        """
        try:
            with open(os.path.join(settings.MEDIA_ROOT, 'gallery', image.name), 'wb+') as image_file:
                for chunk in image.chunks():
                    image_file.write(chunk)
        except FileNotFoundError:
            return False
        return True

    @classmethod
    def get_gallery_image_list(cls) -> List[str]:
        """
        Returns the list of images in the gallery folder.
        """
        images = os.listdir(os.path.join(settings.MEDIA_ROOT, 'gallery'))
        images.remove('.gitkeep')
        return images

    @classmethod
    def delete_image_from_gallery(cls, image: str) -> None:
        """
        Deletes an image from the gallery folder.
        """
        if image in os.listdir(os.path.join(settings.MEDIA_ROOT, 'gallery')):
            if os.path.isfile(os.path.join(settings.MEDIA_ROOT, 'gallery', image)):
                os.remove(os.path.join(settings.MEDIA_ROOT, 'gallery', image))
