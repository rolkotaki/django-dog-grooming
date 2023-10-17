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
    path('my_bookings', views.UserBookingsPage.as_view(), name='user_bookings'),
    path('bookings', views.AdminBookingsPage.as_view(), name='admin_bookings'),
    path('admin_api', views.admin_api_page, name='admin_api'),
    path('service/<int:service_id>/booking', views.booking, name='booking'),
    path('api/admin/contact/create', api_views.ContactCreate.as_view(), name='api_contact_create'),
    path('api/admin/contact/update_delete/<str:id>/', api_views.ContactRetrieveUpdateDestroy.as_view(),
         name='api_contact_update_delete'),
    path('api/admin/services', api_views.ServiceList.as_view(), name='api_services'),
    path('api/admin/service/create', api_views.ServiceCreate.as_view(), name='api_service_create'),
    path('api/admin/service/update_delete/<int:id>/', api_views.ServiceRetrieveUpdateDestroy.as_view(),
         name='api_service_update_delete'),
    path('api/admin/booking/create', api_views.BookingCreate.as_view(), name='api_booking_create'),
    path('api/booking/free_booking_slots', api_views.ListFreeTimeSlots.as_view(), name='api_free_booking_slots'),
    path('api/booking/<int:booking_id>/cancel', api_views.CancelBooking.as_view(), name='api_cancel_booking'),
    path('api/admin/bookings', api_views.BookingList.as_view(), name='api_bookings'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
