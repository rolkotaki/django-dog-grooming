from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

from .models import CustomUser, Booking
from .constants import PHONE_NUMBER_VALIDATOR


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
    phone_number = forms.CharField(required=True, max_length=20, label=_('Phone number'),
                                   validators=[RegexValidator(regex=PHONE_NUMBER_VALIDATOR,
                                                              message=_('Enter a valid phone number.'))])

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
    phone_number = forms.CharField(required=True, max_length=20, label=_('Phone number'),
                                   validators=[RegexValidator(regex=PHONE_NUMBER_VALIDATOR,
                                                              message=_('Enter a valid phone number.'))])

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'phone_number']


class BookingForm(forms.Form):
    """
    Booking form class.
    """
    dog_size = forms.CharField(widget=forms.Select(attrs={'id': 'dog_size', 'name': 'dog_size'}),
                               label=_('Time:'), required=False)
    date = forms.DateField(widget=forms.TextInput(attrs={'type': 'date', 'class': 'date_input',
                                                         'id': 'date', 'name': 'date',
                                                         'onchange': 'fetchAvailableBookingTimeSlots()'}),
                           label=_('Date:'))
    time = forms.CharField(widget=forms.Select(attrs={'class': 'select_input', 'id': 'time', 'name': 'time'}),
                           label=_('Time:'))
    comment = forms.CharField(widget=forms.Textarea(attrs={'rows': '7', 'maxlength': '500',
                                                           'placeholder': _('Please tell us the breed of your dog and the required things to do ...'),
                                                           'id': 'comment', 'name': 'comment', 'class': 'text_input'}),
                              label=_('Comment:'))

    def __init__(self, *args, **kwargs):
        """
        Overriding the constructor to load the initial times in the dropdown list for the default day.
        """
        available_booking_slots = kwargs.pop('available_booking_slots', None)
        super().__init__(*args, **kwargs)
        if available_booking_slots:
            self.fields['time'].widget.choices = available_booking_slots

    class Meta:
        model = Booking
        fields = ['date', 'time', 'comment']
