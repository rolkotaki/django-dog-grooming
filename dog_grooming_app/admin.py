from django.contrib import admin
from .models import CustomUser, Contact, Service, Booking


admin.site.register(CustomUser)
admin.site.register(Contact)
admin.site.register(Service)
admin.site.register(Booking)
