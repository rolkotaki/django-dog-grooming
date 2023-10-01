from django.contrib.auth.views import PasswordChangeView
from django.views.generic import TemplateView
from django.contrib.auth import login, authenticate
from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from .forms import SignUpForm, LoginForm, PersonalDataForm
from .models import Contact, Service, CustomUser


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
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, _("Invalid username or password!"))
        return render(request, "login.html", {'form': form})


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
        context["contact_details"] = Contact.objects.get(id='x')
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


class CustomPasswordChangeView(PasswordChangeView):
    """
    View class for the password change. It inherits from the Django's PasswordChangeView,
    only the success url is changed.
    """
    success_url = '/'
