from django.views.generic import TemplateView
from django.contrib.auth import login, authenticate, logout
from django.shortcuts import redirect, render
from django.contrib import messages
from .forms import SignUpForm, LoginForm
from django.utils.translation import gettext_lazy as _


class HomePage(TemplateView):
    template_name = "home.html"


def sign_up(request):
    if request.method == 'GET':
        form = SignUpForm()
        return render(request, "signup.html", {'form': form})

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # TODO set active=False until user confirms email account
            user.save()
            # messages.success(request, "Successful signup")
            login(request, user)
            return redirect('home')
        return render(request, "signup.html", {'form': form})


def login_user(request):
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
