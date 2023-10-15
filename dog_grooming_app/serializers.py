from rest_framework import serializers

from .models import Contact, Service, Booking


class ContactSerializer(serializers.ModelSerializer):
    """
    Serializer class of the Contact model for the API views.
    """

    class Meta:
        model = Contact
        fields = ('phone_number', 'email', 'address', 'opening_hour_monday', 'closing_hour_monday',
                  'opening_hour_tuesday', 'closing_hour_tuesday', 'opening_hour_wednesday', 'closing_hour_wednesday',
                  'opening_hour_thursday', 'closing_hour_thursday', 'opening_hour_friday', 'closing_hour_friday',
                  'opening_hour_saturday', 'closing_hour_saturday', 'opening_hour_sunday', 'closing_hour_sunday',
                  'google_maps_url')


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


class BookingCreateSerializer(serializers.ModelSerializer):
    """
    Serializer class of the Booking model for the create API view.
    """

    def create(self, validated_data):
        """
        Overriding the create method to add the service price automatically based on the service.
        """
        service = validated_data.get('service', None)
        dog_size = validated_data.get('dog_size', None)
        service_price = int(service.price_default if dog_size == 'medium' or dog_size == '' or not dog_size
                            else service.price_small if dog_size == 'small' else service.price_big)
        validated_data['service_price'] = service_price
        booking = Booking.objects.create(**validated_data)
        return booking

    class Meta:
        model = Booking
        fields = ('user', 'service', 'dog_size', 'date', 'time', 'comment', 'cancelled')


class BookingSerializer(serializers.ModelSerializer):
    """
    Serializer class of the Booking model for the API views.
    """

    class Meta:
        model = Booking
        fields = ('id', 'user', 'service', 'dog_size', 'service_price', 'date', 'time', 'comment', 'cancelled',
                  'booking_date')
