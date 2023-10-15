import os
import datetime
from django.contrib.auth.views import PasswordChangeView
from django.views.generic import TemplateView
from django.contrib.auth import login, authenticate
from django.shortcuts import redirect, render
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .forms import SignUpForm, LoginForm, PersonalDataForm, BookingForm
from .models import Contact, Service, CustomUser, Booking
from .utils import get_free_booking_slots


class HomePage(TemplateView):
    """
    View class for the Home page.
    """
    template_name = "home.html"


def sign_up(request):
    """
    View method for signup.
    """
    if request.method == 'GET':
        form = SignUpForm()
        return render(request, "signup.html", {'form': form})

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # TODO set active=False until user confirms email account
            user.save()
            login(request, user)
            return redirect('home')
        return render(request, "signup.html", {'form': form})


def login_user(request):
    """
    View method for login.
    """
    if request.method == 'GET':
        form = LoginForm()
        return render(request, "login.html", {'form': form})

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect('home')
                else:
                    messages.error(request, _("The user is not active!"))
            else:
                messages.error(request, _("Invalid username or password!"))
        return render(request, "login.html", {'form': form})


@login_required(login_url='login')
def personal_data(request):
    """
    View method for the personal data.
    """
    if request.method == 'GET':
        user_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'phone_number': request.user.phone_number
        }
        form = PersonalDataForm(initial=user_data)
        return render(request, "personal_data.html", {'form': form})

    if request.method == 'POST':
        form = PersonalDataForm(request.POST)
        if form.is_valid():
            user = CustomUser.objects.get(id=request.user.id)
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.phone_number = form.cleaned_data['phone_number']
            # TODO set active=False until user confirms email account
            user.save()
            messages.success(request, _("Your data has been updated successfully."))
            return redirect('personal_data')
        return render(request, "personal_data.html", {'form': form})


class ContactPage(TemplateView):
    """
    View class for the contact details.
    """
    template_name = "contact.html"

    def get_context_data(self, **kwargs):
        """
        Overriding the get_context_data method to add the Contact object.
        """
        context = super().get_context_data(**kwargs)
        try:
            context["contact_details"] = Contact.objects.get(id='x')
        except Contact.DoesNotExist:
            context["contact_details"] = None
        return context


class GalleryPage(TemplateView):
    """
    View class for the gallery.
    """
    template_name = "gallery.html"

    def get_context_data(self, **kwargs):
        """
        Overriding the get_context_data method to add the image list from the gallery folder.
        """
        context = super().get_context_data(**kwargs)
        images = os.listdir(os.path.join(settings.MEDIA_ROOT, 'gallery'))
        images.remove('.gitkeep')
        context["images"] = images
        return context


class ServiceListPage(TemplateView):
    """
    View class for the service list.
    """
    template_name = "services.html"

    def get_context_data(self, **kwargs):
        """
        Overriding the get_context_data method to add the list of active Services.
        """
        context = super().get_context_data(**kwargs)
        context["services"] = Service.objects.filter(active=True)
        return context


class ServicePage(TemplateView):
    """
    View class for the service.
    """
    template_name = "service.html"

    def get_context_data(self, **kwargs):
        """
        Overriding the get_context_data method to add the Service object.
        """
        context = super().get_context_data(**kwargs)
        context["service"] = Service.objects.get(id=self.kwargs['service_id'])
        return context


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """
    View class for the password change. It inherits from the Django's PasswordChangeView,
    only the success url is changed.
    """
    success_url = '/'
    login_url = 'login'


@staff_member_required()
def admin_api_page(request):
    services = Service.objects.order_by('id')
    active_services = Service.objects.filter(active=True).order_by('id')
    return render(request, "admin_api.html", {'services': services, 'active_services': active_services})


@login_required(login_url='login')
def booking(request, service_id):
    """
    View method for the booking.
    """
    service = Service.objects.get(id=service_id)
    free_booking_slots = get_free_booking_slots(datetime.date.today() + datetime.timedelta(days=1), service.id)
    if request.method == 'GET':
        form = BookingForm(free_booking_slots=free_booking_slots)
        return render(request, "booking.html", {'form': form, 'service': service})

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            user = CustomUser.objects.get(id=request.user.id)
            dog_size = form.cleaned_data['dog_size']
            service_price = int(service.price_default if dog_size == 'medium' or dog_size == ''
                                else service.price_small if dog_size == 'small' else service.price_big)
            booking_data = {
                'user': user,
                'service': service,
                'dog_size': dog_size,
                'service_price': service_price,
                'date': form.cleaned_data['date'],
                'time': form.cleaned_data['time'],
                'comment': form.cleaned_data['comment']
            }
            booking = Booking.objects.create(**booking_data)
            booking.save()
            messages.success(request, _("Your booking has been successful."))
            return redirect('booking', service_id=service.id)
        form = BookingForm(request.POST, free_booking_slots=free_booking_slots)
        return render(request, "booking.html", {'form': form, 'service': service})


class UserBookingsPage(LoginRequiredMixin, TemplateView):
    """
    View class for the user booking list.
    """
    template_name = "user_bookings.html"
    login_url = 'login'

    def get_context_data(self, **kwargs):
        """
        Overriding the get_context_data method to add the list of active Bookings.
        """
        context = super().get_context_data(**kwargs)
        booking_filter = Q(cancelled=False) & Q(user=self.request.user.id) & \
                          (Q(date__gt=datetime.date.today()) |
                           (Q(date=datetime.date.today()) & Q(time__gt=datetime.datetime.now().time())))
        context["bookings"] = Booking.objects.filter(booking_filter)
        return context
