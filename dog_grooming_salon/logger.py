import logging
from django.conf import settings


logger = logging.getLogger('dog_grooming_logger')

if settings.TEST_MODE:
    logging.disable(logging.CRITICAL)
