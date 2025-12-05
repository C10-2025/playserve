from django.urls import path
from . import views
from booking.views import show_json

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
    path('admin/booking/<int:booking_id>/verify/', views.admin_verify_payment, name='admin_verify_payment'),
    path('admin/court/<int:field_id>/toggle/', views.admin_toggle_field_status, name='admin_toggle_field'),

    # View JSON
    path('json/', show_json, name="show_json"),

    # API for mobile
    path('api/fields/', views.api_fields, name='api_fields'),
    path('api/availability/', views.api_availability, name='api_availability'),
    path('api/book/', views.api_book, name='api_book'),
    path('api/my-bookings/', views.api_my_bookings, name='api_my_bookings'),
    path('api/cancel/', views.api_cancel_booking, name='api_cancel_booking'),
    path('api/bookings/<int:pk>/upload-proof/', views.api_upload_payment_proof, name='api_upload_payment_proof'),

    # Admin JSON APIs
    path('api/admin/fields/', views.admin_api_fields_list, name='admin_api_fields_list'),
    path('api/admin/fields/create/', views.admin_api_field_create, name='admin_api_field_create'),
    path('api/admin/fields/<int:pk>/update/', views.admin_api_field_update, name='admin_api_field_update'),
    path('api/admin/fields/<int:pk>/delete/', views.admin_api_field_delete, name='admin_api_field_delete'),
    path('api/admin/pending-bookings/', views.admin_api_pending_bookings, name='admin_api_pending_bookings'),
    path('api/admin/bookings/<int:pk>/', views.admin_api_booking_detail, name='admin_api_booking_detail'),
    path('api/admin/bookings/<int:pk>/verify/', views.admin_api_verify_payment, name='admin_api_verify_payment'),
]

