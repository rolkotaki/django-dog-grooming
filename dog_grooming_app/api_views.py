import datetime
from django.urls import reverse
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from rest_framework.views import APIView
from rest_framework.exceptions import APIException
from rest_framework.filters import SearchFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.response import Response
from rest_framework import status

from .serializers import ContactSerializer, ServiceSerializer, ServiceUpdateDeleteSerializer, BookingCreateSerializer, \
                         BookingSerializer
from .models import Contact, Service, Booking
from .utils import get_free_booking_slots, cancel_booking


class ContactCreate(CreateAPIView):
    """
    API view class to create the Contact details.
    """
    serializer_class = ContactSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        """
        Overrides the create method to throw a error when the Contact details already exist.
        """
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            raise APIException(_("The contact information already exist, please update the existing one!"))


class ContactRetrieveUpdateDestroy(RetrieveUpdateDestroyAPIView):
    """
    API view class to update or delete the Contact details.
    """
    queryset = Contact.objects.all()
    lookup_field = 'id'
    serializer_class = ContactSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]


class ServiceCreate(CreateAPIView):
    """
    API view class to create a new Service.
    """
    serializer_class = ServiceSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]

    def create(self, request, *args, **kwargs):
        """
        Overrides the create method to validate that the prices are positive integers
        and at least the default is not empty.
        """
        field_with_error = 'price_default'
        try:
            price_list = ['price_default', 'price_small', 'price_big']
            for price_field in price_list:
                field_with_error = price_field
                price = request.data.get(price_field)
                if price is not None and price != '':
                    if int(price) <= 0:
                        raise ValidationError({price_field: _("Price must be greater than zero!")})
                elif price_field == 'price_default':  # meaning it is empty
                    raise ValidationError({price_field: _("Default price must not be empty!")})
        except ValueError:
            raise ValidationError({field_with_error: _("A valid number is required!")})
        return super().create(request, *args, **kwargs)


class Pagination(LimitOffsetPagination):
    """
    Pagination class for the Service model.
    """
    default_limit = 50
    max_limit = 100


class ServiceList(ListAPIView):
    """
    API view class to view/list the Services.
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter)
    filter_fields = ('id',)
    search_fields = ('service_name_hu', 'service_description_hu')
    pagination_class = Pagination
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        """
        Overrides the get_queryset method to be able to filter on active Services.
        """
        active = self.request.query_params.get('active', None)
        if active is None:
            return super().get_queryset()
        queryset = Service.objects.all()
        if active.lower() == 'true':
            return queryset.filter(Q(active=True))
        return queryset


class ServiceRetrieveUpdateDestroy(RetrieveUpdateDestroyAPIView):
    """
    API view class to update or delete Services.
    """
    queryset = Service.objects.all()
    lookup_field = 'id'
    serializer_class = ServiceUpdateDeleteSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]

    def update(self, request, *args, **kwargs):
        """
        Overrides the update method to validate that the prices are positive integers
        and at least the default is not empty.
        """
        field_with_error = 'price_default'
        try:
            price_list = ['price_default', 'price_small', 'price_big']
            for price_field in price_list:
                field_with_error = price_field
                price = request.data.get(price_field)
                if price is not None and price != '':
                    if int(price) <= 0:
                        raise ValidationError({price_field: _("Price must be greater than zero!")})
                elif price_field == 'price_default':  # meaning it is empty
                    raise ValidationError({price_field: _("Default price must not be empty!")})
        except ValueError:
            raise ValidationError({field_with_error: _("A valid number is required!")})
        return super().update(request, *args, **kwargs)


class BookingCreate(CreateAPIView):
    """
    API view class to create a new Service. (If the Admin user wants to create for a specific user
    in an exceptional case.)
    """
    serializer_class = BookingCreateSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]


class CancelBooking(APIView):
    """
    API view class to cancel a booking.
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]

    def get(self, request, *args, **kwargs):
        try:
            booking_id = int(self.kwargs.get('booking_id'))
        except ValueError:
            return Response({'message': _('Incorrect booking id')}, status=status.HTTP_400_BAD_REQUEST)
        by_user = request.query_params.get('by_user', True)
        if cancel_booking(booking_id, by_user=by_user):
            return redirect(reverse('user_bookings'))
        return Response({'message': _('An error happened during the cancellation of the booking %(booking_id)')
                                    % {'booking_id': booking_id}},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListFreeTimeSlots(APIView):
    """
    API view class to get the free time slots for booking.
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]

    def get(self, request):
        day = request.query_params.get('day', None)
        service_id = request.query_params.get('service_id', None)
        if not day or not service_id:
            return Response({'message': _('Incorrect day or service_id')}, status=status.HTTP_400_BAD_REQUEST)
        booking_slots = get_free_booking_slots(day=day, service_id=service_id)
        response_data = {
            'message': _('These are the free booking slots'),
            'booking_slots': booking_slots
        }
        return Response(response_data, status=status.HTTP_200_OK, content_type='application/json')


class BookingList(ListAPIView):
    """
    API view class to view/list the Bookings.
    """
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    filter_backends = (DjangoFilterBackend, SearchFilter)
    filter_fields = ('id',)
    search_fields = ('date', 'cancelled', 'booking_date')
    pagination_class = Pagination
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        """
        Overrides the get_queryset method to be able to filter on active and/or cancelled Bookings.
        """
        cancelled = self.request.query_params.get('cancelled', '')
        active = self.request.query_params.get('active', 'true')  # active, meaning the ones in the future
        filter_list = list()
        if active.lower() == 'true':
            filter_list.append((Q(date__gt=datetime.date.today()) |
                                (Q(date=datetime.date.today()) & Q(time__gt=datetime.datetime.now().time()))))
        if cancelled.lower() == 'true':
            filter_list.append(Q(cancelled=True))
        elif cancelled.lower() == 'false':
            filter_list.append(Q(cancelled=False))
        # if cancelled is None, we display everything

        if len(filter_list) == 0:
            return super().get_queryset()

        queryset = Booking.objects.all()
        booking_filter = None
        for q in filter_list:
            if not booking_filter:
                booking_filter = q
                continue
            booking_filter = (booking_filter & q)
        return queryset.filter(booking_filter)
