from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from django.db import IntegrityError
from rest_framework.exceptions import APIException
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .serializers import ContactSerializer, ServiceSerializer, ServiceUpdateDeleteSerializer
from .models import Contact, Service


class ContactCreate(CreateAPIView):
    """
    API view class to create the Contact details.
    """
    serializer_class = ContactSerializer

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


class ServiceCreate(CreateAPIView):
    """
    API view class to create a new Service.
    """
    serializer_class = ServiceSerializer

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
                        raise ValidationError({price_field: _("Price be greater than zero!")})
        except ValueError:
            raise ValidationError({field_with_error: _("A valid number is required!")})
        return super().create(request, *args, **kwargs)


class ServicePagination(LimitOffsetPagination):
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
    pagination_class = ServicePagination

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
