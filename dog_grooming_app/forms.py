from .models import CustomUser
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.utils.translation import gettext_lazy as _


class LoginForm(forms.Form):
    """
    Login form class.
    """
    username = forms.CharField(required=True, max_length=150, label=_('Username'))
    password = forms.CharField(max_length=50, widget=forms.PasswordInput, label=_('Password'))


class SignUpForm(UserCreationForm):
    """
    SignUp form class.
    """
    first_name = forms.CharField(required=True, max_length=150, label=_('First name'))
    last_name = forms.CharField(required=True, max_length=150, label=_('Last name'))
    email = forms.EmailField(required=True, max_length=254, widget=forms.EmailInput(attrs={'class': 'validate', }))
    phone_number = forms.CharField(required=True, max_length=20, label=_('Phone number'))

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'username', 'password1', 'password2']


class PersonalDataForm(forms.Form):
    """
    Personal Data form class.
    """
    first_name = forms.CharField(required=True, max_length=150, label=_('First name'))
    last_name = forms.CharField(required=True, max_length=150, label=_('Last name'))
    email = forms.EmailField(required=True, max_length=254, widget=forms.EmailInput(attrs={'class': 'validate', }))
    phone_number = forms.CharField(required=True, max_length=20, label=_('Phone number'))

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number']
