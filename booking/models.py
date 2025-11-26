from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, time

class PlayingField(models.Model):
    """
    Tennis court information with owner details and amenities
    """
    CITY_CHOICES = [
        ('Jakarta', 'Jakarta'),
        ('Bogor', 'Bogor'),
        ('Depok', 'Depok'),
        ('Tangerang', 'Tangerang'),
        ('Bekasi', 'Bekasi'),
    ]

    SURFACE_CHOICES = [
        ('HARD', 'Hard Court'),
        ('CLAY', 'Clay Court'),
        ('GRASS', 'Grass Court'),
        ('SYNTHETIC', 'Synthetic'),
    ]

    # Basic Information
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=50, choices=CITY_CHOICES)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Court Details
    number_of_courts = models.PositiveIntegerField(default=1, help_text="Number of courts available")
    has_lights = models.BooleanField(default=False, help_text="Night play available")
    has_backboard = models.BooleanField(default=False, help_text="Practice wall available")
    court_surface = models.CharField(max_length=20, choices=SURFACE_CHOICES, default='HARD')

    # Pricing
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)

    # Owner/Contact Information (for admin)
    owner_name = models.CharField(max_length=100, blank=True)
    owner_contact = models.CharField(max_length=50, blank=True, help_text="Phone/WhatsApp number")
    owner_bank_account = models.CharField(max_length=100, blank=True, help_text="Bank name and account number")
    # Removed owner_qris_image field - using default static image instead

    # Operating Hours
    opening_time = models.TimeField(default=time(6, 0))  # 6 AM
    closing_time = models.TimeField(default=time(22, 0))  # 10 PM

    # Additional Features
    description = models.TextField(blank=True)
    amenities = models.JSONField(default=list, blank=True, help_text='["parking", "locker", "shower", "cafe"]')
    court_image = models.ImageField(upload_to='courts/', blank=True, null=True)
    image_url = models.URLField(blank=True, help_text="External image URL for court thumbnail")

    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_fields')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['city', 'name']
        indexes = [
            models.Index(fields=['city', 'is_active']),
            models.Index(fields=['price_per_hour']),
        ]

    def __str__(self):
        return f"{self.name} - {self.city}"

    @property
    def price_range_category(self):
        """Categorize price for filtering"""
        if self.price_per_hour < 75000:
            return 'budget'
        elif self.price_per_hour < 150000:
            return 'mid'
        else:
            return 'premium'

    def get_available_slots(self, date):
        """Get available time slots for a specific date"""
        booked_slots = self.bookings.filter(
            booking_date=date,
            status__in=['PENDING_PAYMENT', 'CONFIRMED']
        ).values_list('start_time', 'end_time')

        # Return list of booked time ranges for frontend display
        return list(booked_slots)


class Booking(models.Model):
    """
    Booking reservation with flexible time slots and payment tracking
    """
    STATUS_CHOICES = [
        ('PENDING_PAYMENT', 'Awaiting Payment Confirmation'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    ]

    # Core Booking Information
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    field = models.ForeignKey(PlayingField, on_delete=models.CASCADE, related_name='bookings')

    # Date and Time (flexible slots)
    booking_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    duration_hours = models.DecimalField(max_digits=3, decimal_places=1)

    # Booker Identity/Contact
    booker_name = models.CharField(max_length=100, help_text="Full name for reservation")
    booker_phone = models.CharField(max_length=20, help_text="Contact number")
    booker_email = models.EmailField(blank=True)

    # Payment Information
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_PAYMENT')
    payment_proof = models.ImageField(upload_to='payment_proofs/', blank=True, null=True)

    # Additional Information
    notes = models.TextField(blank=True, help_text="Special requests or notes")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['field', 'booking_date', 'start_time']),
            models.Index(fields=['status', 'booking_date']),
        ]

    def __str__(self):
        return f"{self.booker_name} - {self.field.name} on {self.booking_date}"

    def clean(self):
        """Validate booking before saving"""
        # Skip validation if this is a partial booking creation (during form validation)
        # Only validate when we have all required fields
        if hasattr(self, '_skip_validation') and self._skip_validation:
            return

        # Only validate if we have the required fields
        if self.start_time and self.end_time:
            # Check if start time is before end time
            if self.start_time >= self.end_time:
                raise ValidationError("End time must be after start time")

        # Check if within operating hours (only if field is available)
        try:
            field = self.field
            if field and self.start_time and self.end_time:
                if self.start_time < field.opening_time or self.end_time > field.closing_time:
                    raise ValidationError(
                        f"Booking must be within operating hours: "
                        f"{field.opening_time.strftime('%H:%M')} - {field.closing_time.strftime('%H:%M')}"
                    )

                # Check for conflicts
                is_available, message = self.check_availability()
                if not is_available:
                    raise ValidationError(message)
        except:
            # If field is not accessible, skip field-specific validation
            pass

    def check_availability(self):
        """Check if this time slot conflicts with existing bookings"""
        conflicting_bookings = Booking.objects.filter(
            field=self.field,
            booking_date=self.booking_date,
            status__in=['PENDING_PAYMENT', 'CONFIRMED']
        ).exclude(id=self.id)

        for booking in conflicting_bookings:
            # Check for overlap: (start1 < end2) and (end1 > start2)
            if (self.start_time < booking.end_time and self.end_time > booking.start_time):
                return False, f"Time slot conflicts with existing booking ({booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')})"

        return True, "Available"

    def calculate_price(self):
        """Calculate total price based on duration and field hourly rate"""
        return float(self.duration_hours) * float(self.field.price_per_hour)

    def save(self, *args, **kwargs):
        # Auto-calculate duration if not set
        if not self.duration_hours and self.start_time and self.end_time:
            start_minutes = self.start_time.hour * 60 + self.start_time.minute
            end_minutes = self.end_time.hour * 60 + self.end_time.minute
            self.duration_hours = (end_minutes - start_minutes) / 60

        # Auto-calculate total price
        if not self.total_price:
            self.total_price = self.calculate_price()

        # Set confirmed_at when status changes to CONFIRMED
        if self.status == 'CONFIRMED' and not self.confirmed_at:
            self.confirmed_at = timezone.now()

        # Set cancelled_at when status changes to CANCELLED
        if self.status == 'CANCELLED' and not self.cancelled_at:
            self.cancelled_at = timezone.now()

        super().save(*args, **kwargs)

    @property
    def can_cancel(self):
        """Check if booking can be cancelled (at least 24 hours before)"""
        if self.status not in ['PENDING_PAYMENT', 'CONFIRMED']:
            return False

        booking_datetime = datetime.combine(self.booking_date, self.start_time)
        now = timezone.now()
        time_until_booking = booking_datetime - now.replace(tzinfo=None)

        return time_until_booking.total_seconds() > 86400  # 24 hours in seconds

    @property
    def is_upcoming(self):
        """Check if booking is in the future"""
        booking_datetime = datetime.combine(self.booking_date, self.start_time)
        return booking_datetime > datetime.now()
