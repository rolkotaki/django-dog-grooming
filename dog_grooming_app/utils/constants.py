from django.utils.translation import gettext_lazy as _


# Constants for the application

# regular expression to validate the phone number (of Hungary)
PHONE_NUMBER_VALIDATOR = r'^(?:0036|\+36|06)[0-9]{1,10}$'
# break after services
BREAK = 15
# time interval in minutes after which we check if there is an available booking slot
BOOKING_SLOT_SEARCH_TIME_INTERVAL = 15

# pagination constants
PAGINATION_PAGES = 5  # should be an odd number
SERVICES_PER_PAGE = 12
BOOKINGS_PER_PAGE = 12
GALLERY_IMAGES_PER_PAGE = 12

# Email templates
BOOKING_CANCELLATION_EMAIL_SUBJECT_TO_USER = str(_('Your booking has been cancelled'))
BOOKING_CANCELLATION_EMAIL_SUBJECT_TO_ADMIN = str(_('A booking has been cancelled'))
USER_CANCELLATION_EMAIL_SUBJECT = str(_('Your account has been deactivated'))
USER_REGISTRATION_EMAIL_SUBJECT = str(_('Confirm your registration at Emma Dog Grooming Salon'))
CALLBACK_EMAIL_SUBJECT = str(_('Someone has requested a callback'))
