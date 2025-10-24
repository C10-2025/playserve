# PlayServe Booking System - Complete Implementation Plan v2

## 1. Overview & Objectives

### Project Vision
Build an MVP booking system for tennis courts in Indonesia (Jakarta area) that allows:
- **Players**: Browse 120+ courts, make reservations, pay via QRIS
- **Admins**: Add/manage courts, view bookings, verify payments

### Core Principles
- **Simple MVP**: Manual payment verification via QRIS screenshot
- **Mobile-First**: Most users will book via phone
- **Flexible Scheduling**: Users pick any time within operating hours
- **Real-time Availability**: Prevent double bookings with conflict checking

---

## 2. Database Models

### Enhanced PlayingField Model

```python
# booking/models.py
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
    owner_qris_image = models.ImageField(upload_to='qris/', blank=True, null=True, help_text="QRIS payment code")
    
    # Operating Hours
    opening_time = models.TimeField(default=time(6, 0))  # 6 AM
    closing_time = models.TimeField(default=time(22, 0))  # 10 PM
    
    # Additional Features
    description = models.TextField(blank=True)
    amenities = models.JSONField(default=list, blank=True, help_text='["parking", "locker", "shower", "cafe"]')
    court_image = models.ImageField(upload_to='courts/', blank=True, null=True)
    
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
        # Check if start time is before end time
        if self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time")
        
        # Check if within operating hours
        if self.start_time < self.field.opening_time or self.end_time > self.field.closing_time:
            raise ValidationError(
                f"Booking must be within operating hours: "
                f"{self.field.opening_time.strftime('%H:%M')} - {self.field.closing_time.strftime('%H:%M')}"
            )
        
        # Check for conflicts
        is_available, message = self.check_availability()
        if not is_available:
            raise ValidationError(message)
    
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
```

---

## 3. User Flow - Detailed Journey

### 3.1 Court Discovery & Selection

**URL: `/booking/` (Court List Page)**

**Features:**
- Grid/list view of all active courts (120+ imported)
- Search bar (searches name, address, city)
- Filters:
  - City dropdown (Jakarta, Bogor, Depok, Tangerang, Bekasi)
  - Price range slider (Rp 50,000 - Rp 200,000)
  - Features checkboxes (Has Lights, Has Backboard)
  - Sort by: Price (low-high), Price (high-low), Name

**Court Card Display:**
```
┌─────────────────────────────┐
│   [Court Image/Placeholder] │
│                             │
│  Court Name                 │
│  📍 City, Address (truncated)│
│  🎾 2 courts • Lights: Yes  │
│  💰 Rp 90,000/hour          │
│                             │
│      [BOOK NOW] Button      │
└─────────────────────────────┘
```

**User Actions:**
- Browse courts
- Apply filters
- Click "BOOK NOW" → Redirects to Court Detail Page

---

### 3.2 Court Detail View

**URL: `/booking/court/<id>/` (Field Detail Page)**

**Page Sections:**

1. **Court Gallery**
   - Main court image
   - Thumbnail gallery (if multiple)

2. **Court Information**
   - Court name and full address
   - City with map link (using lat/long)
   - Number of courts available
   - Surface type (Hard/Clay/Grass)
   - Features: Lights ✓, Backboard ✓
   - Amenities: Parking, Locker, Shower, Cafe (from JSON)
   - Operating hours: 06:00 - 22:00

3. **Pricing**
   - Rp 90,000 per hour (large, prominent)

4. **Availability Preview**
   - Mini calendar showing next 7-14 days
   - Green dot = Available slots
   - Red dot = Fully booked
   - Yellow dot = Limited availability

5. **Description**
   - Court owner's description (if provided)

6. **Call-to-Action**
   - Large "BOOK NOW" button (sticky on mobile)

**User Actions:**
- Review court details
- Check availability calendar
- Click "BOOK NOW" → Redirects to Booking Form (Step 1)

---

### 3.3 Booking Form - Multi-Step Process

**URL: `/booking/create/<field_id>/` (Booking Creation Page)**

#### **Step 1: Identity & Contact**

```
┌────────────────────────────────┐
│  Booking for: [Court Name]     │
│  Step 1 of 3: Your Information │
├────────────────────────────────┤
│                                │
│  Full Name *                   │
│  [John Doe          ]          │
│  (pre-filled from profile)     │
│                                │
│  Phone Number *                │
│  [+62 812-3456-7890 ]          │
│  (pre-filled if in profile)    │
│                                │
│  Email (optional)              │
│  [john@email.com    ]          │
│  (pre-filled from user.email)  │
│                                │
│      [Next: Select Time] →     │
└────────────────────────────────┘
```

#### **Step 2: Date & Time Selection**

```
┌────────────────────────────────┐
│  Step 2 of 3: Pick Date & Time │
├────────────────────────────────┤
│                                │
│  Select Date *                 │
│  [📅 Calendar Widget]          │
│  (blocks past dates & fully    │
│   booked dates)                │
│                                │
│  Start Time *                  │
│  [▼ 14:00    ] (dropdown)      │
│                                │
│  Duration *                    │
│  ○ 1 hour    ○ 1.5 hours       │
│  ○ 2 hours   ○ 2.5 hours       │
│  ○ 3 hours                     │
│                                │
│  End Time: 16:00 (auto-calc)   │
│                                │
│  ✅ Available! (real-time check)│
│                                │
│  Total Price: Rp 180,000       │
│  (2 hours × Rp 90,000)         │
│                                │
│  Notes (optional)              │
│  [Any special requests...]     │
│                                │
│  ← [Back]  [Next: Payment] →   │
└────────────────────────────────┘
```

**Real-time Availability Check:**
- AJAX call on time change
- Shows ✅ Available or ❌ Not Available with conflict time
- Suggests alternative times if not available

#### **Step 3: Payment & Confirmation**

```
┌────────────────────────────────┐
│  Step 3 of 3: Payment          │
├────────────────────────────────┤
│                                │
│  📋 Booking Summary            │
│  ───────────────────────────   │
│  Court: TC7 Tennis Court       │
│  Date: Friday, Oct 25, 2025    │
│  Time: 14:00 - 16:00 (2 hrs)   │
│  Name: John Doe                │
│  Phone: +62 812-3456-7890      │
│  ───────────────────────────   │
│  Total: Rp 180,000             │
│                                │
│  💳 Payment Instructions       │
│  1. Scan QRIS code below       │
│  2. Pay Rp 180,000             │
│  3. Take screenshot of payment │
│  4. Upload proof below         │
│                                │
│  [      QRIS Code Image      ] │
│  (Owner's QRIS from database)  │
│                                │
│  [Download QRIS] [Copy Amount] │
│                                │
│  Upload Payment Proof *        │
│  [Choose File] (image upload)  │
│                                │
│  ☑ I agree to terms &          │
│     cancellation policy        │
│     (24h advance notice)       │
│                                │
│     [CONFIRM BOOKING] ✓        │
│                                │
│  ← [Back]                      │
└────────────────────────────────┘
```

**User Actions:**
- Review booking summary
- Scan QRIS code with banking app
- Make payment externally
- Take screenshot
- Upload payment proof
- Submit booking

---

### 3.4 Booking Confirmation

**URL: `/booking/success/<booking_id>/` (Success Page)**

```
┌────────────────────────────────┐
│         ✅ Booking Created!     │
│                                │
│  Booking ID: #BK123456         │
│  Status: Awaiting Confirmation │
│                                │
│  Your booking has been         │
│  submitted. We'll verify your  │
│  payment within 1-2 hours.     │
│                                │
│  📧 Confirmation email sent to │
│     john@email.com             │
│                                │
│  📋 Booking Details            │
│  ───────────────────────────   │
│  Court: TC7 Tennis Court       │
│  Date: Friday, Oct 25, 2025    │
│  Time: 14:00 - 16:00           │
│  Total Paid: Rp 180,000        │
│                                │
│    [View My Bookings]          │
│    [Book Another Court]        │
└────────────────────────────────┘
```

---

### 3.5 User Dashboard - My Bookings

**URL: `/booking/my-bookings/` (User Booking List)**

**Sections:**

1. **Upcoming Bookings**
   ```
   ┌──────────────────────────────┐
   │ 📅 Friday, Oct 25, 2025      │
   │ TC7 Tennis Court - Bekasi    │
   │ 14:00 - 16:00 (2 hours)      │
   │ Status: ✅ Confirmed         │
   │ [View Details] [Cancel]      │
   └──────────────────────────────┘
   ```

2. **Pending Payment Confirmation**
   ```
   ┌──────────────────────────────┐
   │ 📅 Sunday, Oct 27, 2025      │
   │ Indoor Court - Jakarta       │
   │ 10:00 - 11:00 (1 hour)       │
   │ Status: ⏳ Awaiting Confirm  │
   │ [View Details] [Upload Proof]│
   └──────────────────────────────┘
   ```

3. **Past Bookings**
   - Completed bookings
   - Cancelled bookings
   - Option to "Book Again"

**User Actions:**
- View booking details
- Cancel upcoming booking (if >24h away)
- Re-upload payment proof
- Download booking receipt
- Leave review (future feature)

---

## 4. Admin Flow - Detailed Journey

### 4.1 Admin Dashboard

**URL: `/booking/admin/dashboard/` (Admin Overview)**

**Access Control:**
- Only users with `profile.role == 'ADMIN'` or Django staff
- Admins see their own created courts

**Dashboard Sections:**

1. **Quick Stats**
   ```
   ┌─────────────┬─────────────┬─────────────┐
   │ My Courts   │   Bookings  │   Revenue   │
   │     3       │     24      │ Rp 2.1M     │
   └─────────────┴─────────────┴─────────────┘
   ```

2. **My Courts List**
   - Table of courts created by admin
   - Edit/Deactivate options
   - View bookings per court

3. **Recent Bookings**
   - Pending payment confirmations (needs action)
   - Upcoming bookings
   - Filter by court, date, status

4. **Call-to-Action**
   - **[+ Add New Court]** button (prominent)

---

### 4.2 Add New Court

**URL: `/booking/admin/add-court/` (Court Creation Form)**

```
┌────────────────────────────────────┐
│  Add New Tennis Court              │
├────────────────────────────────────┤
│                                    │
│  BASIC INFORMATION                 │
│  ───────────────────────────────   │
│  Court Name *                      │
│  [TC7 Tennis Court Jatikramat  ]   │
│                                    │
│  Full Address *                    │
│  [Jl. Masjid No.12, Jatikramat,]   │
│  [Jatiasih, Kota Bekasi        ]   │
│                                    │
│  City *                            │
│  [▼ Bekasi]                        │
│                                    │
│  Latitude (optional)               │
│  [-6.287        ]                  │
│                                    │
│  Longitude (optional)              │
│  [106.959       ]                  │
│  [📍 Pick from Map]                │
│                                    │
│  COURT DETAILS                     │
│  ───────────────────────────────   │
│  Number of Courts *                │
│  [2] courts available              │
│                                    │
│  Court Surface *                   │
│  ○ Hard Court  ○ Clay Court        │
│  ○ Grass Court ○ Synthetic         │
│                                    │
│  Features                          │
│  ☑ Has Lights (night play)         │
│  ☐ Has Backboard (practice wall)   │
│                                    │
│  Operating Hours                   │
│  Open:  [06:00 ▼]                  │
│  Close: [22:00 ▼]                  │
│                                    │
│  Amenities (check all that apply)  │
│  ☑ Parking  ☑ Locker Room          │
│  ☐ Shower   ☐ Cafe                 │
│  ☐ Pro Shop ☐ Equipment Rental     │
│                                    │
│  Description                       │
│  [Premium court with excellent  ]  │
│  [lighting and well-maintained  ]  │
│  [surface...                    ]  │
│                                    │
│  Court Photos                      │
│  [Upload Image] (optional)         │
│                                    │
│  PRICING                           │
│  ───────────────────────────────   │
│  Price per Hour *                  │
│  Rp [90000      ]                  │
│                                    │
│  OWNER/CONTACT INFORMATION         │
│  ───────────────────────────────   │
│  Owner Name *                      │
│  [Budi Santoso             ]       │
│                                    │
│  Owner Contact (Phone/WA) *        │
│  [+62 821-9876-5432        ]       │
│                                    │
│  Bank Account Details *            │
│  [BCA - 1234567890         ]       │
│  [a.n. Budi Santoso        ]       │
│                                    │
│  QRIS Payment Code *               │
│  [Upload QRIS Image] (required)    │
│  📱 Users will scan this to pay    │
│                                    │
│     [Cancel]  [Save Court] ✓       │
└────────────────────────────────────┘
```

**Validation:**
- All required fields must be filled
- QRIS image must be uploaded (critical for payment)
- Price must be positive number
- Lat/long must be valid coordinates if provided

**After Saving:**
- Court is created with `is_active=True`
- Admin is redirected to court list
- Success message: "Court added successfully!"

---

### 4.3 Manage Courts

**URL: `/booking/admin/courts/` (Admin Court List)**

**Table View:**
```
┌─────┬──────────────┬────────┬───────┬────────────┬─────────┐
│ ID  │ Court Name   │ City   │ Price │ Bookings   │ Actions │
├─────┼──────────────┼────────┼───────┼────────────┼─────────┤
│ 001 │ TC7 Tennis   │ Bekasi │ 90K   │ 12 active  │ [Edit]  │
│     │ Court        │        │       │            │ [View]  │
│     │              │        │       │            │ [📴]   │
├─────┼──────────────┼────────┼───────┼────────────┼─────────┤
│ 002 │ Indoor Court │Jakarta │ 150K  │ 8 active   │ [Edit]  │
│     │ Senayan      │        │       │            │ [View]  │
│     │              │        │       │            │ [📴]   │
└─────┴──────────────┴────────┴───────┴────────────┴─────────┘
```

**Actions:**
- **Edit**: Modify court details (same form as Add)
- **View**: See court detail page as users see it
- **Deactivate**: Hide from public listings (soft delete)

---

### 4.4 Booking Management

**URL: `/booking/admin/bookings/` (Admin Booking List)**

**Filters:**
- Status: All, Pending Payment, Confirmed, Cancelled
- Court: Dropdown of admin's courts
- Date range picker

**Booking Table:**
```
┌────────┬───────────┬──────────┬────────┬───────────┬─────────┐
│ Date   │ Court     │ Customer │ Time   │ Status    │ Actions │
├────────┼───────────┼──────────┼────────┼───────────┼─────────┤
│ Oct 25 │ TC7       │ John Doe │ 14-16  │ ⏳ Pending│ [View]  │
│        │ Bekasi    │ 0812...  │ 2hrs   │ Payment   │ [✓ Conf]│
│        │           │          │180K    │           │ [✗ Deny]│
├────────┼───────────┼──────────┼────────┼───────────┼─────────┤
│ Oct 27 │ TC7       │ Jane S.  │ 10-11  │ ✅ Confirm│ [View]  │
│        │ Bekasi    │ 0813...  │ 1hr    │           │ [Cancel]│
│        │           │          │ 90K    │           │         │
└────────┴───────────┴──────────┴────────┴───────────┴─────────┘
```

**Actions:**
- **View**: See booking details and payment proof
- **Confirm**: Change status to CONFIRMED (verify payment)
- **Deny**: Cancel booking with reason (refund if needed)
- **Cancel**: Admin-initiated cancellation

---

### 4.5 Payment Verification

**URL: `/booking/admin/verify/<booking_id>/` (Payment Verification Page)**

```
┌────────────────────────────────────┐
│  Verify Payment - Booking #BK12345 │
├────────────────────────────────────┤
│                                    │
│  BOOKING DETAILS                   │
│  Customer: John Doe                │
│  Phone: +62 812-3456-7890          │
│  Court: TC7 Tennis Court           │
│  Date: Friday, Oct 25, 2025        │
│  Time: 14:00 - 16:00 (2 hours)     │
│  Amount: Rp 180,000                │
│                                    │
│  PAYMENT PROOF                     │
│  Uploaded: Oct 23, 2025 14:32      │
│                                    │
│  [   Payment Screenshot Image   ]  │
│  (full size, zoomable)             │
│                                    │
│  [Download Image]                  │
│                                    │
│  VERIFY PAYMENT                    │
│  ───────────────────────────────   │
│                                    │
│  Payment Verified?                 │
│  ○ Yes - Confirm Booking           │
│  ○ No - Request Re-upload          │
│  ○ No - Cancel & Refund            │
│                                    │
│  Admin Notes (optional)            │
│  [Payment verified via BCA...  ]   │
│                                    │
│    [Cancel]  [Submit Decision] ✓   │
└────────────────────────────────────┘
```

**Verification Flow:**
1. Admin reviews payment screenshot to PlayServe company QRIS
2. Checks if amount matches the booking total (Rp 180,000)
3. Verifies payment timestamp is recent
4. Confirms or denies booking
5. System sends notification to user
6. Revenue is collected by PlayServe, court owners paid separately

---

## 5. Backend Implementation

### 5.1 Views Structure

```python
# booking/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from .models import PlayingField, Booking
from .forms import BookingStepOneForm, BookingStepTwoForm, BookingStepThreeForm, FieldForm

# === USER VIEWS ===

class FieldListView(ListView):
    """Court listing with search and filters"""
    model = PlayingField
    template_name = 'booking/field_list.html'
    context_object_name = 'fields'
    paginate_by = 12

    def get_queryset(self):
        queryset = PlayingField.objects.filter(is_active=True)
        
        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(address__icontains=search) |
                Q(city__icontains=search)
            )
        
        # City filter
        city = self.request.GET.get('city')
        if city:
            queryset = queryset.filter(city=city)
        
        # Price range filter
        price_min = self.request.GET.get('price_min')
        price_max = self.request.GET.get('price_max')
        if price_min:
            queryset = queryset.filter(price_per_hour__gte=price_min)
        if price_max:
            queryset = queryset.filter(price_per_hour__lte=price_max)
        
        # Features filter
        if self.request.GET.get('has_lights') == 'true':
            queryset = queryset.filter(has_lights=True)
        if self.request.GET.get('has_backboard') == 'true':
            queryset = queryset.filter(has_backboard=True)
        
        # Sorting
        sort = self.request.GET.get('sort', 'name')
        if sort == 'price_low':
            queryset = queryset.order_by('price_per_hour')
        elif sort == 'price_high':
            queryset = queryset.order_by('-price_per_hour')
        else:
            queryset = queryset.order_by('name')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cities'] = PlayingField.CITY_CHOICES
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_city'] = self.request.GET.get('city', '')
        return context


class FieldDetailView(DetailView):
    """Court detail page with availability preview"""
    model = PlayingField
    template_name = 'booking/field_detail.html'
    context_object_name = 'field'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        field = self.object
        
        # Get next 14 days availability
        today = timezone.now().date()
        availability_data = []
        
        for i in range(14):
            date = today + timezone.timedelta(days=i)
            booked_slots = field.get_available_slots(date)
            
            # Determine availability status
            if len(booked_slots) == 0:
                status = 'available'
            elif len(booked_slots) >= 10:  # Arbitrary threshold
                status = 'full'
            else:
                status = 'limited'
            
            availability_data.append({
                'date': date,
                'status': status,
                'booked_count': len(booked_slots)
            })
        
        context['availability_calendar'] = availability_data
        return context


class BookingCreateView(LoginRequiredMixin, CreateView):
    """
    Multi-step booking form
    Step 1: Identity & Contact
    Step 2: Date & Time Selection
    Step 3: Payment & Confirmation
    """
    model = Booking
    template_name = 'booking/booking_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.field = get_object_or_404(PlayingField, pk=kwargs.get('field_id'))
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_class(self):
        step = self.request.GET.get('step', '1')
        if step == '1':
            return BookingStepOneForm
        elif step == '2':
            return BookingStepTwoForm
        else:
            return BookingStepThreeForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['field'] = self.field
        context['step'] = self.request.GET.get('step', '1')
        
        # Pre-fill user data in step 1
        if context['step'] == '1':
            context['form'].initial = {
                'booker_name': self.request.user.get_full_name() or self.request.user.username,
                'booker_email': self.request.user.email,
            }
        
        return context
    
    def form_valid(self, form):
        step = self.request.GET.get('step', '1')
        
        if step == '1':
            # Save step 1 data to session
            self.request.session['booking_step1'] = form.cleaned_data
            return redirect(f"{self.request.path}?step=2")
        
        elif step == '2':
            # Save step 2 data to session
            booking_data = form.cleaned_data
            
            # Check availability via AJAX or here
            temp_booking = Booking(
                field=self.field,
                booking_date=booking_data['booking_date'],
                start_time=booking_data['start_time'],
                end_time=booking_data['end_time'],
            )
            is_available, message = temp_booking.check_availability()
            
            if not is_available:
                form.add_error(None, message)
                return self.form_invalid(form)
            
            self.request.session['booking_step2'] = {
                'booking_date': str(booking_data['booking_date']),
                'start_time': str(booking_data['start_time']),
                'end_time': str(booking_data['end_time']),
                'duration_hours': float(booking_data['duration_hours']),
                'notes': booking_data.get('notes', ''),
            }
            return redirect(f"{self.request.path}?step=3")
        
        else:  # step 3
            # Combine all steps and create booking
            step1_data = self.request.session.get('booking_step1', {})
            step2_data = self.request.session.get('booking_step2', {})
            
            booking = form.save(commit=False)
            booking.user = self.request.user
            booking.field = self.field
            
            # Add step 1 data
            booking.booker_name = step1_data['booker_name']
            booking.booker_phone = step1_data['booker_phone']
            booking.booker_email = step1_data.get('booker_email', '')
            
            # Add step 2 data
            from datetime import datetime
            booking.booking_date = datetime.strptime(step2_data['booking_date'], '%Y-%m-%d').date()
            booking.start_time = datetime.strptime(step2_data['start_time'], '%H:%M:%S').time()
            booking.end_time = datetime.strptime(step2_data['end_time'], '%H:%M:%S').time()
            booking.duration_hours = step2_data['duration_hours']
            booking.notes = step2_data.get('notes', '')
            
            # Calculate total price
            booking.total_price = booking.calculate_price()
            
            try:
                booking.save()
                
                # Clear session data
                del self.request.session['booking_step1']
                del self.request.session['booking_step2']
                
                messages.success(self.request, 'Booking created successfully! Awaiting payment confirmation.')
                return redirect('booking:booking_success', booking_id=booking.id)
            
            except Exception as e:
                messages.error(self.request, f'Error creating booking: {str(e)}')
                return self.form_invalid(form)


@login_required
def check_availability_ajax(request):
    """AJAX endpoint for real-time availability checking"""
    field_id = request.GET.get('field_id')
    date = request.GET.get('date')
    start_time = request.GET.get('start_time')
    end_time = request.GET.get('end_time')
    
    if not all([field_id, date, start_time, end_time]):
        return JsonResponse({'available': False, 'message': 'Missing parameters'})
    
    try:
        from datetime import datetime
        field = PlayingField.objects.get(id=field_id)
        
        temp_booking = Booking(
            field=field,
            booking_date=datetime.strptime(date, '%Y-%m-%d').date(),
            start_time=datetime.strptime(start_time, '%H:%M').time(),
            end_time=datetime.strptime(end_time, '%H:%M').time(),
        )
        
        is_available, message = temp_booking.check_availability()
        
        return JsonResponse({
            'available': is_available,
            'message': message
        })
    
    except Exception as e:
        return JsonResponse({'available': False, 'message': str(e)})


class BookingSuccessView(LoginRequiredMixin, DetailView):
    """Booking confirmation page"""
    model = Booking
    template_name = 'booking/booking_success.html'
    context_object_name = 'booking'
    pk_url_kwarg = 'booking_id'
    
    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)


class BookingListView(LoginRequiredMixin, ListView):
    """User's booking history dashboard"""
    model = Booking
    template_name = 'booking/booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 10

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related('field').order_by('-booking_date', '-start_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Separate into categories
        all_bookings = self.get_queryset()
        today = timezone.now().date()
        
        context['upcoming_bookings'] = all_bookings.filter(
            booking_date__gte=today,
            status__in=['PENDING_PAYMENT', 'CONFIRMED']
        )
        context['pending_bookings'] = all_bookings.filter(status='PENDING_PAYMENT')
        context['past_bookings'] = all_bookings.filter(
            Q(booking_date__lt=today) | Q(status__in=['CANCELLED', 'COMPLETED'])
        )
        
        return context


@login_required
def cancel_booking(request, booking_id):
    """Cancel a booking"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if not booking.can_cancel:
        messages.error(request, 'Cannot cancel booking less than 24 hours before start time')
        return redirect('booking:my_bookings')
    
    if request.method == 'POST':
        booking.status = 'CANCELLED'
        booking.save()
        
        messages.success(request, 'Booking cancelled successfully')
        return redirect('booking:my_bookings')
    
    return render(request, 'booking/cancel_booking.html', {'booking': booking})


# === ADMIN VIEWS ===

class AdminTestMixin(UserPassesTestMixin):
    """Mixin to check if user is admin"""
    def test_func(self):
        return hasattr(self.request.user, 'profile') and self.request.user.profile.role == 'ADMIN'


class AdminDashboardView(LoginRequiredMixin, AdminTestMixin, ListView):
    """Admin dashboard with stats and overview"""
    model = PlayingField
    template_name = 'booking/admin_dashboard.html'
    context_object_name = 'fields'
    
    def get_queryset(self):
        return PlayingField.objects.filter(created_by=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Stats
        my_fields = self.get_queryset()
        all_bookings = Booking.objects.filter(field__in=my_fields)
        
        context['total_courts'] = my_fields.count()
        context['total_bookings'] = all_bookings.count()
        context['pending_confirmations'] = all_bookings.filter(status='PENDING_PAYMENT').count()
        
        # Calculate revenue
        confirmed_bookings = all_bookings.filter(status__in=['CONFIRMED', 'COMPLETED'])
        context['total_revenue'] = sum(b.total_price for b in confirmed_bookings)
        
        # Recent bookings needing attention
        context['pending_bookings'] = all_bookings.filter(
            status='PENDING_PAYMENT'
        ).select_related('field', 'user').order_by('-created_at')[:10]
        
        return context


class AdminFieldCreateView(LoginRequiredMixin, AdminTestMixin, CreateView):
    """Admin: Add new court"""
    model = PlayingField
    form_class = FieldForm
    template_name = 'booking/admin_field_form.html'
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Court added successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('booking:admin_fields')


class AdminFieldUpdateView(LoginRequiredMixin, AdminTestMixin, UpdateView):
    """Admin: Edit existing court"""
    model = PlayingField
    form_class = FieldForm
    template_name = 'booking/admin_field_form.html'
    
    def get_queryset(self):
        return PlayingField.objects.filter(created_by=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'Court updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('booking:admin_fields')


class AdminFieldListView(LoginRequiredMixin, AdminTestMixin, ListView):
    """Admin: Manage courts list"""
    model = PlayingField
    template_name = 'booking/admin_field_list.html'
    context_object_name = 'fields'
    
    def get_queryset(self):
        return PlayingField.objects.filter(created_by=self.request.user).annotate(
            booking_count=models.Count('bookings')
        )


@login_required
def admin_toggle_field_status(request, field_id):
    """Admin: Activate/Deactivate court"""
    field = get_object_or_404(PlayingField, id=field_id, created_by=request.user)
    
    field.is_active = not field.is_active
    field.save()
    
    status = "activated" if field.is_active else "deactivated"
    messages.success(request, f'Court {status} successfully')
    
    return redirect('booking:admin_fields')


class AdminBookingListView(LoginRequiredMixin, AdminTestMixin, ListView):
    """Admin: View and manage bookings"""
    model = Booking
    template_name = 'booking/admin_booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 20
    
    def get_queryset(self):
        # Only bookings for admin's courts
        my_fields = PlayingField.objects.filter(created_by=self.request.user)
        queryset = Booking.objects.filter(field__in=my_fields).select_related('field', 'user')
        
        # Filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        field_id = self.request.GET.get('field')
        if field_id:
            queryset = queryset.filter(field_id=field_id)
        
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(booking_date__gte=date_from)
        
        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(booking_date__lte=date_to)
        
        return queryset.order_by('-booking_date', '-start_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['my_fields'] = PlayingField.objects.filter(created_by=self.request.user)
        context['status_choices'] = Booking.STATUS_CHOICES
        return context


@login_required
def admin_verify_payment(request, booking_id):
    """Admin: Verify payment and confirm booking"""
    # Ensure admin owns the court
    booking = get_object_or_404(
        Booking.objects.select_related('field'),
        id=booking_id,
        field__created_by=request.user
    )
    
    if request.method == 'POST':
        decision = request.POST.get('decision')
        admin_notes = request.POST.get('admin_notes', '')
        
        if decision == 'confirm':
            booking.status = 'CONFIRMED'
            booking.confirmed_at = timezone.now()
            booking.save()
            messages.success(request, f'Booking #{booking.id} confirmed!')
        
        elif decision == 'deny':
            booking.status = 'CANCELLED'
            booking.save()
            messages.warning(request, f'Booking #{booking.id} cancelled')
        
        return redirect('booking:admin_bookings')
    
    return render(request, 'booking/admin_verify_payment.html', {
        'booking': booking
    })
```

---

## 6. Forms Implementation

```python
# booking/forms.py
from django import forms
from .models import PlayingField, Booking
from datetime import datetime, time, timedelta

class BookingStepOneForm(forms.Form):
    """Step 1: Identity and Contact Information"""
    booker_name = forms.CharField(
        max_length=100,
        label="Full Name",
        widget=forms.TextInput(attrs={
            'class': 'w-full border rounded px-3 py-2',
            'placeholder': 'Your full name'
        })
    )
    
    booker_phone = forms.CharField(
        max_length=20,
        label="Phone Number",
        widget=forms.TextInput(attrs={
            'class': 'w-full border rounded px-3 py-2',
            'placeholder': '+62 812-3456-7890'
        })
    )
    
    booker_email = forms.EmailField(
        required=False,
        label="Email (optional)",
        widget=forms.EmailInput(attrs={
            'class': 'w-full border rounded px-3 py-2',
            'placeholder': 'your@email.com'
        })
    )


class BookingStepTwoForm(forms.Form):
    """Step 2: Date and Time Selection"""
    booking_date = forms.DateField(
        label="Select Date",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full border rounded px-3 py-2',
            'min': datetime.now().strftime('%Y-%m-%d')
        })
    )
    
    start_time = forms.TimeField(
        label="Start Time",
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'w-full border rounded px-3 py-2'
        })
    )
    
    DURATION_CHOICES = [
        (1.0, '1 hour'),
        (1.5, '1.5 hours'),
        (2.0, '2 hours'),
        (2.5, '2.5 hours'),
        (3.0, '3 hours'),
        (3.5, '3.5 hours'),
        (4.0, '4 hours'),
    ]
    
    duration_hours = forms.ChoiceField(
        choices=DURATION_CHOICES,
        label="Duration",
        widget=forms.RadioSelect(attrs={
            'class': 'duration-radio'
        })
    )
    
    notes = forms.CharField(
        required=False,
        label="Notes (optional)",
        widget=forms.Textarea(attrs={
            'class': 'w-full border rounded px-3 py-2',
            'rows': 3,
            'placeholder': 'Any special requests...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.field = kwargs.pop('field', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        booking_date = cleaned_data.get('booking_date')
        start_time = cleaned_data.get('start_time')
        duration_hours = cleaned_data.get('duration_hours')
        
        if booking_date and start_time and duration_hours:
            # Calculate end time
            duration_hours = float(duration_hours)
            start_datetime = datetime.combine(booking_date, start_time)
            end_datetime = start_datetime + timedelta(hours=duration_hours)
            end_time = end_datetime.time()
            
            cleaned_data['end_time'] = end_time
            
            # Validate date is not in the past
            if booking_date < datetime.now().date():
                raise forms.ValidationError("Cannot book dates in the past")
            
            # Validate within operating hours (if field provided)
            if self.field:
                if start_time < self.field.opening_time:
                    raise forms.ValidationError(
                        f"Court opens at {self.field.opening_time.strftime('%H:%M')}"
                    )
                if end_time > self.field.closing_time:
                    raise forms.ValidationError(
                        f"Booking would extend past closing time ({self.field.closing_time.strftime('%H:%M')})"
                    )
        
        return cleaned_data


class BookingStepThreeForm(forms.ModelForm):
    """Step 3: Payment Confirmation"""
    terms_agreed = forms.BooleanField(
        required=True,
        label="I agree to the terms and cancellation policy",
        widget=forms.CheckboxInput(attrs={
            'class': 'mr-2'
        })
    )
    
    class Meta:
        model = Booking
        fields = ['payment_proof']
        widgets = {
            'payment_proof': forms.FileInput(attrs={
                'class': 'w-full border rounded px-3 py-2',
                'accept': 'image/*'
            })
        }
    
    def clean_payment_proof(self):
        proof = self.cleaned_data.get('payment_proof')
        if not proof:
            raise forms.ValidationError("Please upload payment proof to complete booking")
        
        # Validate file size (max 5MB)
        if proof.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Image file size must be under 5MB")
        
        return proof


class FieldForm(forms.ModelForm):
    """Admin: Create/Edit Court Form"""
    
    amenities_parking = forms.BooleanField(required=False, label="Parking")
    amenities_locker = forms.BooleanField(required=False, label="Locker Room")
    amenities_shower = forms.BooleanField(required=False, label="Shower")
    amenities_cafe = forms.BooleanField(required=False, label="Cafe")
    amenities_pro_shop = forms.BooleanField(required=False, label="Pro Shop")
    amenities_equipment_rental = forms.BooleanField(required=False, label="Equipment Rental")
    
    class Meta:
        model = PlayingField
        fields = [
            'name', 'address', 'city', 'latitude', 'longitude',
            'number_of_courts', 'court_surface', 'has_lights', 'has_backboard',
            'opening_time', 'closing_time', 'description', 'court_image',
            'price_per_hour', 'owner_name', 'owner_contact', 'owner_bank_account',
            'owner_qris_image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full border rounded px-3 py-2'}),
            'address': forms.Textarea(attrs={'class': 'w-full border rounded px-3 py-2', 'rows': 2}),
            'city': forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'}),
            'latitude': forms.NumberInput(attrs={'class': 'w-full border rounded px-3 py-2', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'w-full border rounded px-3 py-2', 'step': '0.000001'}),
            'number_of_courts': forms.NumberInput(attrs={'class': 'w-full border rounded px-3 py-2'}),
            'court_surface': forms.Select(attrs={'class': 'w-full border rounded px-3 py-2'}),
            'opening_time': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full border rounded px-3 py-2'}),
            'closing_time': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full border rounded px-3 py-2'}),
            'description': forms.Textarea(attrs={'class': 'w-full border rounded px-3 py-2', 'rows': 4}),
            'price_per_hour': forms.NumberInput(attrs={'class': 'w-full border rounded px-3 py-2'}),
            'owner_name': forms.TextInput(attrs={'class': 'w-full border rounded px-3 py-2'}),
            'owner_contact': forms.TextInput(attrs={'class': 'w-full border rounded px-3 py-2'}),
            'owner_bank_account': forms.TextInput(attrs={'class': 'w-full border rounded px-3 py-2'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Pre-populate amenities checkboxes if editing
        if self.instance and self.instance.amenities:
            amenities_list = self.instance.amenities
            self.fields['amenities_parking'].initial = 'parking' in amenities_list
            self.fields['amenities_locker'].initial = 'locker' in amenities_list
            self.fields['amenities_shower'].initial = 'shower' in amenities_list
            self.fields['amenities_cafe'].initial = 'cafe' in amenities_list
            self.fields['amenities_pro_shop'].initial = 'pro_shop' in amenities_list
            self.fields['amenities_equipment_rental'].initial = 'equipment_rental' in amenities_list
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Build amenities list from checkboxes
        amenities = []
        if self.cleaned_data.get('amenities_parking'):
            amenities.append('parking')
        if self.cleaned_data.get('amenities_locker'):
            amenities.append('locker')
        if self.cleaned_data.get('amenities_shower'):
            amenities.append('shower')
        if self.cleaned_data.get('amenities_cafe'):
            amenities.append('cafe')
        if self.cleaned_data.get('amenities_pro_shop'):
            amenities.append('pro_shop')
        if self.cleaned_data.get('amenities_equipment_rental'):
            amenities.append('equipment_rental')
        
        instance.amenities = amenities
        
        if commit:
            instance.save()
        return instance
```

---

## 7. URL Configuration

```python
# booking/urls.py
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
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/courts/', views.AdminFieldListView.as_view(), name='admin_fields'),
    path('admin/court/add/', views.AdminFieldCreateView.as_view(), name='admin_add_field'),
    path('admin/court/<int:pk>/edit/', views.AdminFieldUpdateView.as_view(), name='admin_edit_field'),
    path('admin/court/<int:field_id>/toggle/', views.admin_toggle_field_status, name='admin_toggle_field'),
    path('admin/bookings/', views.AdminBookingListView.as_view(), name='admin_bookings'),
    path('admin/booking/<int:booking_id>/verify/', views.admin_verify_payment, name='admin_verify_payment'),
]
```

---

## 8. Data Import Management Command

```python
# booking/management/commands/import_courts.py
from django.core.management.base import BaseCommand
from booking.models import PlayingField
import csv
from datetime import datetime

class Command(BaseCommand):
    help = 'Import tennis courts from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            created_count = 0
            
            for row in reader:
                try:
                    # Clean and parse data
                    name = row.get('Park Name', '').strip()
                    address = row.get('ADDRESS', '').strip()
                    city = row.get('City', '').strip()
                    
                    # Skip if essential data missing
                    if not name or not city:
                        continue
                    
                    # Parse numeric fields
                    try:
                        latitude = float(row.get('LATITUDE', 0))
                        longitude = float(row.get('LONGITUDE', 0))
                    except (ValueError, TypeError):
                        latitude = None
                        longitude = None
                    
                    try:
                        num_courts = int(row.get('# of Courts', 1))
                    except (ValueError, TypeError):
                        num_courts = 1
                    
                    try:
                        price = float(row.get('price_per_hour', 90000))
                    except (ValueError, TypeError):
                        price = 90000
                    
                    # Parse boolean fields
                    has_lights = row.get('Lights', 'No').strip().lower() == 'yes'
                    has_backboard = row.get('Backboard', 'No').strip().lower() == 'yes'
                    
                    # Create or update field
                    field, created = PlayingField.objects.update_or_create(
                        name=name,
                        city=city,
                        defaults={
                            'address': address,
                            'latitude': latitude,
                            'longitude': longitude,
                            'number_of_courts': num_courts,
                            'has_lights': has_lights,
                            'has_backboard': has_backboard,
                            'price_per_hour': price,
                            'created_by': None,  # System import
                        }
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Created: {name}'))
                    else:
                        self.stdout.write(f'Updated: {name}')
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error importing {name}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully imported {created_count} courts'))
```

**Usage:**
```bash
python manage.py import_courts courts_data.csv
```

---

## 9. Frontend Templates

### 9.1 Court List Template

```html
<!-- booking/templates/booking/field_list.html -->
{% extends 'base.html' %}
{% load static %}

{% block content %}
{% include 'navbar.html' %}

<div class="container mx-auto px-4 py-8">
    <div class="mb-8">
        <h1 class="text-4xl font-bold text-gray-800 mb-2">Find Your Perfect Court</h1>
        <p class="text-gray-600">Browse {{ fields|length }} tennis courts across Jakarta area</p>
    </div>

    <!-- Search and Filters -->
    <div class="bg-white rounded-lg shadow p-6 mb-8">
        <form method="get" class="space-y-4">
            <!-- Search Bar -->
            <div>
                <input 
                    type="text" 
                    name="search" 
                    value="{{ search_query }}"
                    placeholder="Search courts by name or location..."
                    class="w-full border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-green-500"
                />
            </div>

            <!-- Filters Row -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <!-- City Filter -->
                <select name="city" class="border border-gray-300 rounded-lg px-4 py-2">
                    <option value="">All Cities</option>
                    {% for value, label in cities %}
                    <option value="{{ value }}" {% if selected_city == value %}selected{% endif %}>
                        {{ label }}
                    </option>
                    {% endfor %}
                </select>

                <!-- Price Range -->
                <div class="flex items-center space-x-2">
                    <input 
                        type="number" 
                        name="price_min" 
                        placeholder="Min Price"
                        class="border border-gray-300 rounded-lg px-3 py-2 w-full"
                    />
                    <span>-</span>
                    <input 
                        type="number" 
                        name="price_max" 
                        placeholder="Max Price"
                        class="border border-gray-300 rounded-lg px-3 py-2 w-full"
                    />
                </div>

                <!-- Features -->
                <div class="flex items-center space-x-4">
                    <label class="flex items-center">
                        <input type="checkbox" name="has_lights" value="true" class="mr-2" />
                        <span class="text-sm">Lights</span>
                    </label>
                    <label class="flex items-center">
                        <input type="checkbox" name="has_backboard" value="true" class="mr-2" />
                        <span class="text-sm">Backboard</span>
                    </label>
                </div>

                <!-- Sort -->
                <select name="sort" class="border border-gray-300 rounded-lg px-4 py-2">
                    <option value="name">Sort by Name</option>
                    <option value="price_low">Price: Low to High</option>
                    <option value="price_high">Price: High to Low</option>
                </select>
            </div>

            <button type="submit" class="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700">
                Apply Filters
            </button>
        </form>
    </div>

    <!-- Courts Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {% for field in fields %}
        <div class="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-xl transition">
            <!-- Court Image -->
            <div class="h-48 bg-gradient-to-br from-green-400 to-green-600 relative">
                {% if field.court_image %}
                <img src="{{ field.court_image.url }}" alt="{{ field.name }}" class="w-full h-full object-cover" />
                {% else %}
                <div class="flex items-center justify-center h-full">
                    <span class="text-white text-6xl">🎾</span>
                </div>
                {% endif %}
                
                <!-- Features Badges -->
                <div class="absolute top-2 right-2 space-y-1">
                    {% if field.has_lights %}
                    <span class="bg-yellow-400 text-xs px-2 py-1 rounded-full block">💡 Lights</span>
                    {% endif %}
                </div>
            </div>

            <!-- Court Info -->
            <div class="p-4">
                <h3 class="text-xl font-bold text-gray-800 mb-2">{{ field.name }}</h3>
                <p class="text-gray-600 text-sm mb-2 flex items-start">
                    <span class="mr-2">📍</span>
                    <span>{{ field.city }}, {{ field.address|truncatewords:10 }}</span>
                </p>
                
                <div class="flex items-center justify-between text-sm text-gray-600 mb-3">
                    <span>🎾 {{ field.number_of_courts }} court{{ field.number_of_courts|pluralize }}</span>
                    <span>{{ field.get_court_surface_display }}</span>
                </div>

                <div class="flex items-center justify-between mb-4">
                    <div>
                        <p class="text-2xl font-bold text-green-600">Rp {{ field.price_per_hour|floatformat:0 }}</p>
                        <p class="text-xs text-gray-500">per hour</p>
                    </div>
                </div>

                <a href="{% url 'booking:field_detail' field.pk %}" 
                   class="block w-full bg-green-600 text-white text-center py-2 rounded-lg hover:bg-green-700 transition">
                    BOOK NOW
                </a>
            </div>
        </div>
        {% empty %}
        <div class="col-span-full text-center py-12">
            <p class="text-gray-500 text-lg">No courts found matching your criteria.</p>
            <a href="{% url 'booking:field_list' %}" class="text-green-600 hover:underline mt-2 inline-block">
                Clear filters
            </a>
        </div>
        {% endfor %}
    </div>

    <!-- Pagination -->
    {% if is_paginated %}
    <div class="mt-8 flex justify-center">
        <nav class="flex space-x-2">
            {% if page_obj.has_previous %}
            <a href="?page=1" class="px-3 py-2 border rounded">First</a>
            <a href="?page={{ page_obj.previous_page_number }}" class="px-3 py-2 border rounded">Previous</a>
            {% endif %}

            <span class="px-3 py-2 border rounded bg-green-600 text-white">
                Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}
            </span>

            {% if page_obj.has_next %}
            <a href="?page={{ page_obj.next_page_number }}" class="px-3 py-2 border rounded">Next</a>
            <a href="?page={{ page_obj.paginator.num_pages }}" class="px-3 py-2 border rounded">Last</a>
            {% endif %}
        </nav>
    </div>
    {% endif %}
</div>
{% endblock %}
```

---

### 9.2 Court Detail Template

```html
<!-- booking/templates/booking/field_detail.html -->
{% extends 'base.html' %}
{% load static %}

{% block content %}
{% include 'navbar.html' %}

<div class="container mx-auto px-4 py-8">
    <!-- Back Button -->
    <a href="{% url 'booking:field_list' %}" class="text-green-600 hover:underline mb-4 inline-block">
        ← Back to Courts
    </a>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Main Content -->
        <div class="lg:col-span-2">
            <!-- Court Image -->
            <div class="h-96 bg-gradient-to-br from-green-400 to-green-600 rounded-lg mb-6 overflow-hidden">
                {% if field.court_image %}
                <img src="{{ field.court_image.url }}" alt="{{ field.name }}" class="w-full h-full object-cover" />
                {% else %}
                <div class="flex items-center justify-center h-full">
                    <span class="text-white text-9xl">🎾</span>
                </div>
                {% endif %}
            </div>

            <!-- Court Name and Location -->
            <h1 class="text-4xl font-bold text-gray-800 mb-2">{{ field.name }}</h1>
            <p class="text-gray-600 mb-4 flex items-center">
                <span class="mr-2">📍</span>
                {{ field.address }}, {{ field.city }}
            </p>

            {% if field.latitude and field.longitude %}
            <a href="https://www.google.com/maps?q={{ field.latitude }},{{ field.longitude }}" 
               target="_blank"
               class="text-green-600 hover:underline text-sm mb-6 inline-block">
                📍 View on Google Maps
            </a>
            {% endif %}

            <!-- Court Details -->
            <div class="bg-white rounded-lg shadow p-6 mb-6">
                <h2 class="text-2xl font-bold mb-4">Court Details</h2>
                
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <p class="text-gray-600 text-sm">Number of Courts</p>
                        <p class="font-semibold">{{ field.number_of_courts }} court{{ field.number_of_courts|pluralize }}</p>
                    </div>
                    <div>
                        <p class="text-gray-600 text-sm">Court Surface</p>
                        <p class="font-semibold">{{ field.get_court_surface_display }}</p>
                    </div>
                    <div>
                        <p class="text-gray-600 text-sm">Night Play (Lights)</p>
                        <p class="font-semibold">{% if field.has_lights %}✅ Available{% else %}❌ Not Available{% endif %}</p>
                    </div>
                    <div>
                        <p class="text-gray-600 text-sm">Practice Wall</p>
                        <p class="font-semibold">{% if field.has_backboard %}✅ Available{% else %}❌ Not Available{% endif %}</p>
                    </div>
                    <div>
                        <p class="text-gray-600 text-sm">Operating Hours</p>
                        <p class="font-semibold">{{ field.opening_time|time:"H:i" }} - {{ field.closing_time|time:"H:i" }}</p>
                    </div>
                </div>

                <!-- Amenities -->
                {% if field.amenities %}
                <div class="mt-6">
                    <h3 class="font-bold mb-2">Amenities</h3>
                    <div class="flex flex-wrap gap-2">
                        {% for amenity in field.amenities %}
                        <span class="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm">
                            ✓ {{ amenity|title }}
                        </span>
                        {% endfor %}
                    </div>
                </div>
                {% endif %}

                <!-- Description -->
                {% if field.description %}
                <div class="mt-6">
                    <h3 class="font-bold mb-2">About This Court</h3>
                    <p class="text-gray-600">{{ field.description }}</p>
                </div>
                {% endif %}
            </div>

            <!-- Availability Preview -->
            <div class="bg-white rounded-lg shadow p-6">
                <h2 class="text-2xl font-bold mb-4">Availability (Next 14 Days)</h2>
                
                <div class="grid grid-cols-7 gap-2">
                    {% for day in availability_calendar %}
                    <div class="text-center">
                        <p class="text-xs text-gray-600 mb-1">{{ day.date|date:"D" }}</p>
                        <p class="text-sm font-semibold mb-2">{{ day.date|date:"d" }}</p>
                        
                        {% if day.status == 'available' %}
                        <div class="w-10 h-10 mx-auto bg-green-500 rounded-full flex items-center justify-center">
                            <span class="text-white text-xs">✓</span>
                        </div>
                        <p class="text-xs text-green-600 mt-1">Open</p>
                        {% elif day.status == 'limited' %}
                        <div class="w-10 h-10 mx-auto bg-yellow-500 rounded-full flex items-center justify-center">
                            <span class="text-white text-xs">~</span>
                        </div>
                        <p class="text-xs text-yellow-600 mt-1">Limited</p>
                        {% else %}
                        <div class="w-10 h-10 mx-auto bg-red-500 rounded-full flex items-center justify-center">
                            <span class="text-white text-xs">✗</span>
                        </div>
                        <p class="text-xs text-red-600 mt-1">Full</p>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- Sidebar - Booking Card -->
        <div class="lg:col-span-1">
            <div class="bg-white rounded-lg shadow-lg p-6 sticky top-4">
                <div class="text-center mb-6">
                    <p class="text-4xl font-bold text-green-600">Rp {{ field.price_per_hour|floatformat:0 }}</p>
                    <p class="text-gray-600">per hour</p>
                </div>

                {% if user.is_authenticated %}
                <a href="{% url 'booking:create_booking' field.pk %}" 
                   class="block w-full bg-green-600 text-white text-center py-3 rounded-lg hover:bg-green-700 transition text-lg font-semibold">
                    BOOK NOW
                </a>
                {% else %}
                <a href="{% url 'profil:login' %}?next={{ request.path }}" 
                   class="block w-full bg-green-600 text-white text-center py-3 rounded-lg hover:bg-green-700 transition text-lg font-semibold">
                    LOGIN TO BOOK
                </a>
                {% endif %}

                <div class="mt-6 space-y-2 text-sm text-gray-600">
                    <p class="flex items-start">
                        <span class="mr-2">✓</span>
                        Instant booking confirmation
                    </p>
                    <p class="flex items-start">
                        <span class="mr-2">✓</span>
                        Easy QRIS payment
                    </p>
                    <p class="flex items-start">
                        <span class="mr-2">✓</span>
                        Free cancellation (24h notice)
                    </p>
                </div>

                <!-- Contact Info -->
                {% if field.owner_contact %}
                <div class="mt-6 pt-6 border-t">
                    <p class="text-sm text-gray-600 mb-2">Questions? Contact the court:</p>
                    <a href="https://wa.me/{{ field.owner_contact }}" 
                       target="_blank"
                       class="text-green-600 hover:underline text-sm flex items-center">
                        <span class="mr-2">📱</span>
                        WhatsApp {{ field.owner_contact }}
                    </a>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

### 9.3 Booking Form Template (Multi-Step)

```html
<!-- booking/templates/booking/booking_form.html -->
{% extends 'base.html' %}
{% load static %}

{% block content %}
{% include 'navbar.html' %}

<div class="container mx-auto px-4 py-8 max-w-2xl">
    <!-- Progress Indicator -->
    <div class="mb-8">
        <div class="flex items-center justify-between mb-2">
            <div class="flex-1 text-center {% if step == '1' %}text-green-600 font-bold{% endif %}">
                <div class="w-10 h-10 mx-auto rounded-full border-2 {% if step == '1' %}bg-green-600 text-white border-green-600{% else %}border-gray-300{% endif %} flex items-center justify-center mb-2">
                    1
                </div>
                <p class="text-sm">Your Info</p>
            </div>
            <div class="flex-1 border-t-2 border-gray-300 mx-4 mt-5"></div>
            <div class="flex-1 text-center {% if step == '2' %}text-green-600 font-bold{% endif %}">
                <div class="w-10 h-10 mx-auto rounded-full border-2 {% if step == '2' %}bg-green-600 text-white border-green-600{% else %}border-gray-300{% endif %} flex items-center justify-center mb-2">
                    2
                </div>
                <p class="text-sm">Date & Time</p>
            </div>
            <div class="flex-1 border-t-2 border-gray-300 mx-4 mt-5"></div>
            <div class="flex-1 text-center {% if step == '3' %}text-green-600 font-bold{% endif %}">
                <div class="w-10 h-10 mx-auto rounded-full border-2 {% if step == '3' %}bg-green-600 text-white border-green-600{% else %}border-gray-300{% endif %} flex items-center justify-center mb-2">
                    3
                </div>
                <p class="text-sm">Payment</p>
            </div>
        </div>
    </div>

    <!-- Court Info Header -->
    <div class="bg-white rounded-lg shadow p-4 mb-6">
        <h2 class="text-xl font-bold text-gray-800">{{ field.name }}</h2>
        <p class="text-gray-600 text-sm">{{ field.city }} • Rp {{ field.price_per_hour|floatformat:0 }}/hour</p>
    </div>

    <!-- Form Content -->
    <div class="bg-white rounded-lg shadow p-6">
        <form method="post" enctype="multipart/form-data" id="booking-form">
            {% csrf_token %}
            
            {% if step == '1' %}
            <!-- Step 1: Identity & Contact -->
            <h2 class="text-2xl font-bold mb-4">Your Information</h2>
            <p class="text-gray-600 mb-6">Please provide your contact details for the booking.</p>
            
            {{ form.as_p }}

            <div class="mt-6">
                <button type="submit" class="w-full bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 transition">
                    Next: Select Time →
                </button>
            </div>

            {% elif step == '2' %}
            <!-- Step 2: Date & Time Selection -->
            <h2 class="text-2xl font-bold mb-4">Pick Date & Time</h2>
            
            {{ form.booking_date.as_field_group }}
            {{ form.start_time.as_field_group }}
            
            <div class="mb-4">
                <label class="block text-gray-700 font-semibold mb-2">Duration</label>
                <div class="grid grid-cols-3 gap-2">
                    {% for value, label in form.duration_hours.field.choices %}
                    <label class="border-2 rounded-lg p-3 text-center cursor-pointer hover:border-green-600 transition">
                        <input type="radio" name="duration_hours" value="{{ value }}" class="hidden duration-radio" />
                        <span class="font-semibold">{{ label }}</span>
                    </label>
                    {% endfor %}
                </div>
            </div>

            <div id="availability-check" class="mb-4 p-3 rounded-lg hidden">
                <!-- Real-time availability feedback -->
            </div>

            <div id="price-display" class="mb-4 p-4 bg-gray-50 rounded-lg hidden">
                <div class="flex justify-between items-center">
                    <span class="text-gray-700">Total Price:</span>
                    <span class="text-2xl font-bold text-green-600" id="total-price">Rp 0</span>
                </div>
            </div>

            {{ form.notes.as_field_group }}

            <div class="mt-6 flex space-x-3">
                <a href="?step=1" class="flex-1 bg-gray-300 text-gray-700 py-3 rounded-lg hover:bg-gray-400 transition text-center">
                    ← Back
                </a>
                <button type="submit" class="flex-1 bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 transition">
                    Next: Payment →
                </button>
            </div>

            {% elif step == '3' %}
            <!-- Step 3: Payment & Confirmation -->
            <h2 class="text-2xl font-bold mb-4">Payment & Confirmation</h2>

            <!-- Booking Summary -->
            <div class="bg-gray-50 rounded-lg p-4 mb-6">
                <h3 class="font-bold mb-3">📋 Booking Summary</h3>
                <div class="space-y-2 text-sm">
                    <div class="flex justify-between">
                        <span class="text-gray-600">Court:</span>
                        <span class="font-semibold">{{ field.name }}</span>
                    </div>
                    <!-- Additional summary details populated from session -->
                </div>
            </div>

            <!-- QRIS Payment -->
            <div class="mb-6">
                <h3 class="font-bold mb-3">💳 Payment Instructions</h3>
                <ol class="text-sm text-gray-700 space-y-2 mb-4">
                    <li>1. Scan the QRIS code below with your banking app</li>
                    <li>2. Pay the exact amount shown</li>
                    <li>3. Take a screenshot of the payment confirmation</li>
                    <li>4. Upload the screenshot below</li>
                </ol>

                <div class="bg-white border-2 border-gray-300 rounded-lg p-4 mb-4">
                    <img src="{% static 'image/dummy_qris.jpg' %}" alt="PlayServe QRIS Payment" class="max-w-xs mx-auto" />
                </div>
                <div class="flex space-x-2 mb-4">
                    <a href="{% static 'image/dummy_qris.jpg' %}" download class="flex-1 bg-gray-200 text-gray-700 py-2 rounded text-center text-sm hover:bg-gray-300">
                        Download QRIS
                    </a>
                    <button type="button" onclick="copyAmount()" class="flex-1 bg-gray-200 text-gray-700 py-2 rounded text-sm hover:bg-gray-300">
                        Copy Amount
                    </button>
                </div>
            </div>

            <!-- Upload Payment Proof -->
            {{ form.payment_proof.as_field_group }}

            <!-- Terms -->
            <div class="mb-6">
                {{ form.terms_agreed.as_field_group }}
                <p class="text-xs text-gray-600 ml-6">
                    By booking, you agree to our cancellation policy: Free cancellation up to 24 hours before your booking time.
                </p>
            </div>

            <div class="mt-6 flex space-x-3">
                <a href="?step=2" class="flex-1 bg-gray-300 text-gray-700 py-3 rounded-lg hover:bg-gray-400 transition text-center">
                    ← Back
                </a>
                <button type="submit" class="flex-1 bg-green-600 text-white py-3 rounded-lg hover:bg-green-700 transition font-bold">
                    CONFIRM BOOKING ✓
                </button>
            </div>
            {% endif %}
        </form>
    </div>
</div>

<script>
// Real-time availability checking for Step 2
{% if step == '2' %}
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('booking-form');
    const dateInput = document.querySelector('input[name="booking_date"]');
    const timeInput = document.querySelector('input[name="start_time"]');
    const durationRadios = document.querySelectorAll('.duration-radio');
    const availabilityDiv = document.getElementById('availability-check');
    const priceDiv = document.getElementById('price-display');
    const priceDisplay = document.getElementById('total-price');

    function checkAvailability() {
        const date = dateInput.value;
        const startTime = timeInput.value;
        const duration = document.querySelector('.duration-radio:checked')?.value;

        if (date && startTime && duration) {
            // Calculate end time
            const [hours, minutes] = startTime.split(':');
            const startDate = new Date();
            startDate.setHours(parseInt(hours), parseInt(minutes));
            const endDate = new Date(startDate.getTime() + parseFloat(duration) * 60 * 60 * 1000);
            const endTime = endDate.toTimeString().slice(0, 5);

            // Check availability via AJAX
            fetch(`/booking/check-availability/?field_id={{ field.id }}&date=${date}&start_time=${startTime}&end_time=${endTime}`)
                .then(response => response.json())
                .then(data => {
                    availabilityDiv.classList.remove('hidden');
                    if (data.available) {
                        availabilityDiv.className = 'mb-4 p-3 rounded-lg bg-green-100 border border-green-300';
                        availabilityDiv.innerHTML = '<span class="text-green-800">✅ ' + data.message + '</span>';
                        
                        // Show price
                        const totalPrice = {{ field.price_per_hour }} * parseFloat(duration);
                        priceDisplay.textContent = 'Rp ' + totalPrice.toLocaleString('id-ID');
                        priceDiv.classList.remove('hidden');
                    } else {
                        availabilityDiv.className = 'mb-4 p-3 rounded-lg bg-red-100 border border-red-300';
                        availabilityDiv.innerHTML = '<span class="text-red-800">❌ ' + data.message + '</span>';
                        priceDiv.classList.add('hidden');
                    }
                });
        }
    }

    dateInput.addEventListener('change', checkAvailability);
    timeInput.addEventListener('change', checkAvailability);
    durationRadios.forEach(radio => radio.addEventListener('change', checkAvailability));

    // Style selected duration radio
    durationRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            durationRadios.forEach(r => r.parentElement.classList.remove('border-green-600', 'bg-green-50'));
            if (this.checked) {
                this.parentElement.classList.add('border-green-600', 'bg-green-50');
            }
        });
    });
});
{% endif %}

// Copy amount function for Step 3
function copyAmount() {
    const amount = document.getElementById('total-price')?.textContent || '';
    navigator.clipboard.writeText(amount.replace(/[^0-9]/g, ''));
    alert('Amount copied to clipboard!');
}
</script>
{% endblock %}
                