import datetime
from django.contrib.auth.views import PasswordChangeView
from django.views.generic import TemplateView
from django.contrib.auth import login, authenticate
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from .forms import SignUpForm, LoginForm, PersonalDataForm, BookingForm
from .models import Contact, Service, CustomUser, Booking
from .utils import GalleryManager, BookingManager
from .tokens import account_activation_token


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
            user.is_active = False
            user.save()
            # sending the email to confirm the registration
            user.send_activation_link(get_current_site(request).domain,
                                      'https' if request.is_secure() else 'http')

            messages.success(request, _('Your account has been created successfully, please check your emails '
                                        'for the activation link to complete your registration.'))
            return render(request, "signup.html", {'form': form})
        return render(request, "signup.html", {'form': form})


def activate_account(request, uidb64, token):
    """
    View method to activate a user account.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, _('Your account has been activated successfully, you can log in now.'))
    else:
        messages.error(request, _('Activation link is invalid or there was a problem activating your account.'))
    return redirect('login')


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
                else:  # it seems that the authenticate() returns None if the user is not active anyway
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
            user.phone_number = form.cleaned_data['phone_number']
            if user.email != form.cleaned_data['email']:
                # if the email has changed, we send an activation mail to the user to confirm their new email address
                user.email = form.cleaned_data['email']
                user.is_active = False
                user.save()
                user.send_activation_link(get_current_site(request).domain,
                                          'https' if request.is_secure() else 'http')
                redirect('logout')
                messages.success(request, _("Your data has been updated successfully and a confirmation email has been "
                                            "sent to confirm your new email address."))
            else:
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

    def post(self, request, *args, **kwargs):
        """
        Post method to send the callback request email to the owner.
        """
        if request.POST.get('call_me', None):
            Contact.send_callback_request(request.user)
            messages.success(request, _('The callback request has been sent to the owner.'))
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)


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
        context["images"] = GalleryManager.get_gallery_image_list()
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
    """
    View method for the Admin API page.
    """
    services = Service.objects.order_by('id')
    active_services = Service.objects.filter(active=True).order_by('id')
    users = CustomUser.objects.filter(is_active=True).order_by('id')
    gallery_images = GalleryManager.get_gallery_image_list()
    if request.method == 'GET':
        return render(request, "admin_api.html", {'services': services, 'active_services': active_services,
                                                  'users': users, 'gallery_images': gallery_images})
    if request.method == 'POST':
        # uploading a new image to the gallery
        if 'image_upload_submit' in request.POST:
            image = request.FILES.get('image_to_be_uploaded')
            if image:
                GalleryManager.upload_image_to_gallery(image)
                messages.success(request, _("The image has been uploaded successfully."))
                return redirect('admin_api')
        # deleting an image from the gallery
        if 'image_delete_submit' in request.POST:
            image = request.POST.get('image_to_be_deleted')
            GalleryManager.delete_image_from_gallery(image)
            messages.success(request, _("The image has been deleted successfully."))
            return redirect('admin_api')
        return render(request, "admin_api.html", {'services': services, 'active_services': active_services,
                                                  'users': users, 'gallery_images': gallery_images})


@login_required(login_url='login')
def booking(request, service_id):
    """
    View method for the booking.
    """
    service = Service.objects.get(id=service_id)
    available_booking_slots = BookingManager.get_available_booking_slots(datetime.date.today() + datetime.timedelta(days=1),
                                                                         service.id)
    if request.method == 'GET':
        form = BookingForm(available_booking_slots=available_booking_slots)
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
        form = BookingForm(request.POST, available_booking_slots=available_booking_slots)
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
        context["bookings"] = Booking.objects.filter(booking_filter).order_by('date', 'time')
        return context


class AdminBookingsPage(LoginRequiredMixin, TemplateView):
    """
    View class for the admin booking list.
    """
    template_name = "admin_bookings.html"
    login_url = 'login'

    def dispatch(self, request, *args, **kwargs):
        """
        Overriding the dispatch method to restrict access to admin/staff users.
        """
        if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, day=None, cancelled=False, **kwargs):
        """
        Overriding the get_context_data method to add the list of active Bookings.
        """
        context = super().get_context_data(**kwargs)
        if not day:
            booking_filter = (Q(cancelled=False) | Q(cancelled=cancelled)) & \
                              (Q(date__gt=datetime.date.today()) |
                               (Q(date=datetime.date.today()) & Q(time__gt=datetime.datetime.now().time())))
        else:
            booking_filter = (Q(cancelled=False) | Q(cancelled=cancelled)) & Q(date=day)
        context["bookings"] = Booking.objects.filter(booking_filter).order_by('date', 'time')
        context['day'] = '' if not day else day
        context['cancelled'] = True if cancelled else False
        return context

    def post(self, request, *args, **kwargs):
        """
        Post method to handle the filtering and searching of the Bookings.
        """
        cancelled = True if request.POST.get('cancelled', False) else False
        day = None  # if 'submit_all' in request.POST
        # bookings for a specific day
        if 'submit_search' in request.POST:
            day = request.POST.get('booking_date', None)
        context = self.get_context_data(day=day, cancelled=cancelled, **kwargs)
        return self.render_to_response(context)
