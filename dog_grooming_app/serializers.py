from rest_framework import serializers

from .models import Contact, Service


class ContactSerializer(serializers.ModelSerializer):
    """
    Serializer class of the Contact model for the API views.
    """

    class Meta:
        model = Contact
        fields = ('phone_number', 'email', 'address', 'opening_hours_en', 'opening_hours_hu', 'google_maps_url')


class ServiceSerializer(serializers.ModelSerializer):
    """
    Serializer class of the Service model for the create and list API views.
    """

    class Meta:
        model = Service
        fields = ('id', 'service_name_en', 'service_name_hu', 'price_default', 'price_small', 'price_big',
                  'service_description_en', 'service_description_hu', 'max_duration', 'photo', 'active')


class ServiceUpdateDeleteSerializer(ServiceSerializer):
    """
    Serializer class of the Service model for the update and delete API views.
    This class is needed to allow the image field to be empty, in this case we use the existing photo.
    This is implemented in the model class.
    """
    photo = serializers.ImageField(default=None)
