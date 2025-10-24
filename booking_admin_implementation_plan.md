# PlayServe Booking Admin Implementation Plan

## Overview

This plan outlines a **minimalist Django admin integration** for the Booking module, following the established patterns from the Community module. The focus is enabling admins to perform **full CRUD operations on courts** while maintaining the existing user experience unchanged.

## Current Admin Patterns (from Community Module)

### ReadOnlyAdmin Base Class
```python
class ReadOnlyAdmin(admin.ModelAdmin):
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
```

## Minimalist Booking Admin Implementation

### 1. Core Admin Classes

#### PlayingFieldAdmin (Full CRUD for Courts)
**Purpose**: Enable admins to add, edit, and manage tennis courts

**Key Features**:
- **Full CRUD Operations**: Add, edit, delete courts
- **Scoped Access**: Admins only see courts they created
- **Basic List Display**: Name, city, price, status
- **Essential Filtering**: By city, active status
- **Simple Search**: By name and address

**Admin Interface**:
```
List View:
┌─────┬──────────────┬────────┬───────┬─────────┬─────────┐
│ ID  │ Court Name   │ City   │ Price │ Status  │ Actions │
├─────┼──────────────┼────────┼───────┼─────────┼─────────┤
│ 001 │ TC7 Tennis   │ Bekasi │ 90K   │ Active  │ Edit    │
│     │ Court        │        │       │         │ Delete  │
└─────┴──────────────┴────────┴───────┴─────────┴─────────┘

Add/Edit Form:
- Basic Information (Name, Address, City)
- Court Details (Surface, Lights, Backboard)
- Pricing (Price per hour)
- Owner Information (Name, Contact)
- Operating Hours (Open/Close times)
```

#### BookingAdmin (Read-Only Monitoring)
**Purpose**: Allow admins to monitor bookings for their courts

**Key Features**:
- **Read-Only Access**: View booking details only
- **Scoped to Admin's Courts**: Only bookings for owned courts
- **Basic List Display**: Customer, court, date, status
- **Simple Filtering**: By status and date

### 2. Implementation Code

#### booking/admin.py
```python
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
    list_display = ['name', 'city', 'price_per_hour', 'is_active']
    list_filter = ['city', 'is_active', 'court_surface']
    search_fields = ['name', 'address']
    readonly_fields = ['created_at', 'updated_at']

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

@admin.register(Booking)
class BookingAdmin(ReadOnlyAdmin):
    """Read-only admin for booking monitoring"""
    list_display = ['id', 'booker_name', 'field', 'booking_date', 'status']
    list_filter = ['status', 'booking_date']
    search_fields = ['booker_name', 'booker_phone', 'user__username']

    def get_queryset(self, request):
        """Admins only see bookings for their courts"""
        qs = super().get_queryset(request)
        if hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN':
            return qs.filter(field__created_by=request.user)
        return qs.none()
```

### 3. Admin Capabilities

#### Court Management (Full CRUD)
- **Create**: Add new tennis courts with complete information
- **Read**: View court details and booking statistics
- **Update**: Modify court information, pricing, contact details
- **Delete**: Remove courts (with confirmation)

#### Booking Monitoring (Read-Only)
- **View**: Monitor bookings for owned courts
- **Filter**: Find bookings by status, date, customer
- **Track**: Follow booking lifecycle and payment status

### 4. Data Integrity & Access Control

#### Scoped Access
- **Court Ownership**: `get_queryset()` filters courts by `created_by`
- **Booking Visibility**: Only bookings for admin's courts are visible
- **Role Verification**: Checks `user.profile.role == 'ADMIN'`

#### Validation
- **Required Fields**: Name, address, city, price enforced
- **Data Types**: Proper field validation maintained
- **Relationships**: Foreign key constraints preserved

### 5. Integration with Existing System

#### Complement Custom Admin Views
- **Django Admin**: For basic CRUD operations on courts
- **Custom Views**: Continue using `/booking/admin/*` for complex workflows
- **Payment Verification**: Keep existing verification process

#### User Experience Unchanged
- **Public Interface**: No changes to user-facing booking system
- **Admin Workflow**: Existing custom admin views remain functional
- **Data Consistency**: Same database, different access methods

### 6. Implementation Steps

#### Step 1: Update booking/admin.py
- Add ReadOnlyAdmin base class
- Register PlayingField with full CRUD
- Register Booking as read-only

#### Step 2: Test Admin Access
- Verify role-based filtering works
- Confirm CRUD operations function
- Test data integrity

#### Step 3: Update Documentation
- Document admin capabilities
- Update admin workflow guides

### 7. Minimal Changes Approach

#### What Stays the Same
- User booking interface and custom admin views
- Database schema and relationships
- Authentication and profile system
- Payment verification workflow

#### What Gets Added
- Django admin access for court CRUD operations
- Read-only booking monitoring in admin
- Scoped data access by court ownership

This minimalist implementation provides essential admin functionality while maintaining system stability and following established patterns from the Community module.