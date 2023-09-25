"""user profile urls
"""
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.HomePage.as_view(), name='home'),
    path('user/', include("django.contrib.auth.urls")),
    path('login', views.login_user, name='login'),
    path('signup', views.sign_up, name='signup'),
]
