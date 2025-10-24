from django.contrib import admin
from .models import PlayingField, Booking

class ReadOnlyAdmin(admin.ModelAdmin):
    """Read-only admin base class following Community module pattern"""
    list_display = ("id",)
    search_fields = ()
    list_filter = ()
    readonly_fields = ()

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions


@admin.register(PlayingField)
class PlayingFieldAdmin(admin.ModelAdmin):
    """Full CRUD admin for court management"""
    list_display = ['name', 'city', 'price_per_hour', 'is_active', 'created_by']
    list_filter = ['city', 'is_active', 'court_surface', 'has_lights', 'has_backboard']
    search_fields = ['name', 'address', 'owner_name', 'owner_contact']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'address', 'city', 'latitude', 'longitude')
        }),
        ('Court Details', {
            'fields': ('number_of_courts', 'court_surface', 'has_lights', 'has_backboard')
        }),
        ('Pricing & Hours', {
            'fields': ('price_per_hour', 'opening_time', 'closing_time')
        }),
        ('Owner Information', {
            'fields': ('owner_name', 'owner_contact', 'owner_bank_account')
        }),
        ('Media & Description', {
            'fields': ('description', 'court_image'),
            'classes': ('collapse',)
        }),
        ('Status & Metadata', {
            'fields': ('is_active', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Admins only see courts they created"""
        qs = super().get_queryset(request)
        if hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN':
            return qs.filter(created_by=request.user)
        return qs.none()

    def save_model(self, request, obj, form, change):
        """Set created_by on new courts"""
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        """Only allow changing own courts"""
        if obj and hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN':
            return obj.created_by == request.user
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Only allow deleting own courts"""
        if obj and hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN':
            return obj.created_by == request.user
        return super().has_delete_permission(request, obj)


@admin.register(Booking)
class BookingAdmin(ReadOnlyAdmin):
    """Read-only admin for booking monitoring"""
    list_display = ['id', 'booker_name', 'field', 'booking_date', 'start_time', 'status', 'total_price']
    list_filter = ['status', 'booking_date', 'field__city']
    search_fields = ['booker_name', 'booker_phone', 'user__username', 'field__name']
    readonly_fields = ['created_at', 'updated_at', 'confirmed_at', 'cancelled_at']

    fieldsets = (
        ('Booking Information', {
            'fields': ('user', 'field', 'booking_date', 'start_time', 'end_time', 'duration_hours')
        }),
        ('Customer Details', {
            'fields': ('booker_name', 'booker_phone', 'booker_email', 'notes')
        }),
        ('Payment & Status', {
            'fields': ('total_price', 'status', 'payment_proof')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'confirmed_at', 'cancelled_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Admins only see bookings for their courts"""
        qs = super().get_queryset(request)
        if hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN':
            return qs.filter(field__created_by=request.user).select_related('field', 'user')
        return qs.none()
