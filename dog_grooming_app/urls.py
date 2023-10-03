from django.conf.urls.static import static
from django.conf import settings

from django.urls import path, include
from . import views, api_views

urlpatterns = [
    path('', views.HomePage.as_view(), name='home'),
    path('contact', views.ContactPage.as_view(), name='contact'),
    path('gallery', views.GalleryPage.as_view(), name='gallery'),
    path('services', views.ServiceListPage.as_view(), name='services'),
    path('service/<int:service_id>', views.ServicePage.as_view(), name='service'),
    path('user/', include("django.contrib.auth.urls")),
    path('login', views.login_user, name='login'),
    path('signup', views.sign_up, name='signup'),
    path('change_password', views.CustomPasswordChangeView.as_view(), name='change_password'),
    path('personal_data', views.personal_data, name='personal_data'),
    path('api/admin/contact/create', api_views.ContactCreate.as_view()),
    path('api/admin/contact/update_delete/<str:id>/', api_views.ContactRetrieveUpdateDestroy.as_view()),
    path('api/admin/services', api_views.ServiceList.as_view()),
    path('api/admin/service/create', api_views.ServiceCreate.as_view()),
    path('api/admin/service/update_delete/<int:id>/', api_views.ServiceRetrieveUpdateDestroy.as_view()),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
