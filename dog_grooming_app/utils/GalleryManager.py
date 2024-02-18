import os
from typing import List
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile

from dog_grooming_salon.logger import logger


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
            logger.error('Image to be uploaded not found: {}'.format(image.name))
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
