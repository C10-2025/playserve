from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    # User URLs
    path('', views.FieldListView.as_view(), name='field_list'),
    path('court/<int:pk>/', views.FieldDetailView.as_view(), name='field_detail'),
    path('create/<int:field_id>/', views.BookingCreateView.as_view(), name='create_booking'),
    path('check-availability/', views.check_availability_ajax, name='check_availability'),
    path('success/<int:booking_id>/', views.BookingSuccessView.as_view(), name='booking_success'),
    path('my-bookings/', views.BookingListView.as_view(), name='my_bookings'),
    path('cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),

    # Admin URLs
    path('admin/', views.admin_court_management, name='admin_court_management'),
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/courts/', views.AdminFieldListView.as_view(), name='admin_fields'),
    path('admin/court/add/', views.AdminFieldCreateView.as_view(), name='admin_add_field'),
    path('admin/court/<int:pk>/edit/', views.AdminFieldUpdateView.as_view(), name='admin_edit_field'),
    path('admin/court/<int:pk>/delete/', views.AdminFieldDeleteView.as_view(), name='admin_delete_field'),
    path('admin/court/<int:field_id>/toggle/', views.admin_toggle_field_status, name='admin_toggle_field'),
    path('admin/bookings/', views.AdminBookingListView.as_view(), name='admin_bookings'),
    path('admin/booking/<int:booking_id>/verify/', views.admin_verify_payment, name='admin_verify_payment'),
]