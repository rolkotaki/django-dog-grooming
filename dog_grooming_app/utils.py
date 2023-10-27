import datetime
import os
from typing import List, Tuple
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

from .models import Booking, Contact, Service, CustomUser
from .constants import BREAK, BOOKING_SLOT_SEARCH_TIME_INTERVAL


def get_opening_hour_for_day(day_of_week: int) -> datetime.time:
    """
    Returns the opening hour for a given day of the week.
    """
    contact_details = Contact.objects.get(id='x')
    opening_hour_attrs = {
        0: contact_details.opening_hour_monday,
        1: contact_details.opening_hour_tuesday,
        2: contact_details.opening_hour_wednesday,
        3: contact_details.opening_hour_thursday,
        4: contact_details.opening_hour_friday,
        5: contact_details.opening_hour_saturday,
        6: contact_details.opening_hour_sunday,
    }
    return opening_hour_attrs.get(day_of_week)


def get_closing_hour_for_day(day_of_week: int) -> datetime.time:
    """
    Returns the closing hour for a given day of the week.
    """
    contact_details = Contact.objects.get(id='x')
    closing_hour_attrs = {
        0: contact_details.closing_hour_monday,
        1: contact_details.closing_hour_tuesday,
        2: contact_details.closing_hour_wednesday,
        3: contact_details.closing_hour_thursday,
        4: contact_details.closing_hour_friday,
        5: contact_details.closing_hour_saturday,
        6: contact_details.closing_hour_sunday,
    }
    return closing_hour_attrs.get(day_of_week)


def get_duration_of_service(service_id: int) -> Tuple[datetime.timedelta, datetime.timedelta]:
    """
    Returns the duration of a service with and without the break.
    """
    service = Service.objects.get(id=service_id)
    duration_without_break = datetime.timedelta(minutes=service.max_duration)
    duration_with_break = datetime.timedelta(minutes=(service.max_duration + BREAK))
    return duration_without_break, duration_with_break


def get_booked_time_slots(day: datetime.date, duration_with_break: datetime.timedelta) \
        -> List[Tuple[datetime.time, datetime.time]]:
    """
    Returns the booked time slots for a given day.
    Returns a list of tuples where each tuple contains the start and end time of the booking.
    The required break after the service is included in the returned end times.
    """
    bookings = Booking.objects.filter(date=day).order_by('time')
    return [(booking.time, (datetime.datetime.combine(day, booking.time) + duration_with_break).time())
            for booking in bookings]


def get_available_booking_slots(day: [datetime.date, str], service_id: int) -> List[Tuple[str, str]]:
    """
    Returns the list of free time slots that can be booked on a given day.
    :param day: The day for which we want to retrieve the free slots that can be booked.
    :param service_id: The ID of the service that is being booked.
    :return: List of tuples with the value and the text of the option HTML tag in the dropdown list.
    """
    inital_times = list()
    booking_day = datetime.datetime.strptime(day, '%Y-%m-%d').date() if isinstance(day, str) else day
    # retrieving the opening and closing hours
    opening_hour = get_opening_hour_for_day(booking_day.weekday())
    closing_hour = get_closing_hour_for_day(booking_day.weekday())

    # if there is no opening or closing time, then we return closed
    if not opening_hour or not closing_hour:
        return [('', _('Closed'))]

    # retrieving the duration of the service
    duration_without_break, duration_with_break = get_duration_of_service(service_id)

    # retrieving the booked slots for the given day
    booked_slots = get_booked_time_slots(booking_day, duration_with_break)

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
            inital_times.append((datetime.time.strftime(cur_time, '%H:%M'),
                                 "{} - {}".format(datetime.time.strftime(cur_time, '%H:%M'),
                                                  datetime.time.strftime(
                                                      (datetime.datetime.combine(booking_day, cur_time) +
                                                       duration_without_break).time(),
                                                      '%H:%M'))))
        # we increase the current time by the booking slot search time interval
        cur_time = (datetime.datetime.combine(booking_day, cur_time) +
                    datetime.timedelta(minutes=BOOKING_SLOT_SEARCH_TIME_INTERVAL)).time()
        # cur_time = (datetime.datetime.combine(booking_day, cur_time) + duration_without_break).time()
        # TODO: to check with the owner if for example a one hour booking can start at any minute of an hour
        #  or only in certain times, like every half hour
    if len(inital_times) == 0:
        return [('', _('No free slots'))]
    return inital_times


def cancel_booking(booking_id: int, by_user: bool = True) -> bool:
    """
    Cancels the booking by putting the cancelled flag to True.
    The by_user param indicates whether it is cancelled by the user themselves or by the admin.
    """
    booking = Booking.objects.get(id=booking_id)
    booking.cancelled = True
    booking.save()
    # if it is cancelled by the admin, we send a mail to the user
    if not by_user:
        # TODO: send an email to the user
        pass
    # if it is cancelled by the user, we send a mail to the admin
    if by_user:
        # TODO: send an email to the admin
        pass
    return True


def upload_image_to_gallery(image: InMemoryUploadedFile) -> bool:
    """
    Uploads an image to the gallery folder.
    """
    with open(os.path.join(settings.MEDIA_ROOT, 'gallery', image.name), 'wb+') as image_file:
        for chunk in image.chunks():
            image_file.write(chunk)
    return True


def get_gallery_image_list() -> List[str]:
    """
    Returns the list of images in the gallery folder.
    """
    images = os.listdir(os.path.join(settings.MEDIA_ROOT, 'gallery'))
    images.remove('.gitkeep')
    return images


def delete_image_from_gallery(image: str) -> None:
    """
    Deletes an image from the gallery folder.
    """
    if image in os.listdir(os.path.join(settings.MEDIA_ROOT, 'gallery')):
        if os.path.isfile(os.path.join(settings.MEDIA_ROOT, 'gallery', image)):
            os.remove(os.path.join(settings.MEDIA_ROOT, 'gallery', image))


def cancel_user(user_id: int) -> bool:
    """
    Cancels the user by putting the is_active flag to False.
    """
    user = CustomUser.objects.get(id=user_id)
    user.is_active = False
    user.save()
    # we send a mail to the user
    # TODO: send an email to the user
    return True
