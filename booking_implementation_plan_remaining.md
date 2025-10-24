# PlayServe Booking System - Remaining Implementation Plan

## 1. Current State Analysis

### ✅ Implemented Components
- **Models**: `PlayingField`, `Booking` with relationships and validations
- **Basic Views**: Court listing, detail, booking creation (multi-step)
- **Forms**: `FieldForm`, `BookingStepOneForm`, `BookingStepTwoForm`, `BookingStepThreeForm`
- **Templates**: `field_list.html`, `field_detail.html`, `booking_form.html`, `booking_success.html`
- **URLs**: User-facing booking routes
- **Admin Integration**: Basic admin registration and scoped access

### ❌ Missing/Incomplete Components
- **Admin Court Management**: Edit/delete courts, duplicate handling
- **Admin Booking Verification**: `admin_verify_payment.html` template missing
- **Form Validations**: Enhanced duplicate checking, better error messages
- **Template Enhancements**: AJAX error handling, better UX
- **Navigation**: Links between admin pages

## 2. Detailed Implementation Plan

### Phase 1: Views.py Enhancements
**File**: `booking/views.py`

#### **AdminFieldCreateView Improvements**
- Add duplicate name validation with user-friendly messages
- Enhance `form_invalid` method for better error logging
- Add success redirects to admin dashboard

#### **New AdminFieldUpdateView**
- Create view for editing existing courts
- Pre-populate form with existing data
- Handle amenities checkboxes properly

#### **New AdminFieldDeleteView**
- Add confirmation dialog
- Soft delete (deactivate) instead of hard delete
- Success messaging

#### **admin_verify_payment View Enhancement**
- Complete the existing function
- Add proper error handling
- Ensure admin ownership validation

### Phase 2: Forms.py Enhancements
**File**: `booking/forms.py`

#### **FieldForm Improvements**
- Add `clean_name()` method for duplicate checking
- Enhance validation messages
- Add custom validation for required fields
- Improve amenities handling

#### **New Validation Methods**
- Court name uniqueness per admin
- QRIS image requirement validation
- Operating hours logical validation

### Phase 3: Template Completions
**Files**: `booking/templates/booking/`

#### **admin_court_management.html**
- Add "View Details" links for recent bookings
- Add "Verify Payment" buttons for pending bookings
- Improve empty state messaging
- Add court edit/delete links

#### **admin_field_form.html**
- Complete all form fields display
- Add JavaScript for amenities checkboxes
- Enhance error display styling
- Add form validation feedback

#### **NEW: admin_verify_payment.html**
- Payment proof image display
- Booking details summary
- Accept/Reject decision buttons
- Admin notes field

### Phase 4: URL and Navigation Updates
**File**: `booking/urls.py`

#### **Additional Admin URLs**
- Court edit: `admin/court/<int:pk>/edit/`
- Court delete: `admin/court/<int:pk>/delete/`
- Booking verification: Already exists but needs template

#### **Navigation Links**
- Update navbar for admin-specific links
- Add breadcrumbs in admin templates
- Cross-page navigation improvements

### Phase 5: JavaScript Enhancements
**File**: `admin_court_management.html`

#### **AJAX Improvements**
- Better error handling for court creation
- Real-time form validation
- Toast notification improvements
- Modal state management

## 3. Specific Code Changes Required

### **Views.py Changes**
```python
# Add to AdminFieldCreateView
def form_valid(self, form):
    # Check for duplicate names
    existing = PlayingField.objects.filter(
        name__iexact=form.cleaned_data['name'],
        created_by=self.request.user
    ).exclude(pk=self.instance.pk if self.instance else None)

    if existing.exists():
        form.add_error('name', 'You already have a court with this name.')
        return self.form_invalid(form)

    return super().form_valid(form)
```

### **Forms.py Changes**
```python
# Add to FieldForm
def clean_name(self):
    name = self.cleaned_data.get('name')
    if name:
        existing = PlayingField.objects.filter(
            name__iexact=name,
            created_by=self.request.user if hasattr(self, 'request') else None
        )
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("Court name already exists.")
    return name
```

### **Template Changes**
- Add missing form fields to `admin_field_form.html`
- Create `admin_verify_payment.html` with payment verification UI
- Update `admin_court_management.html` with action links

## 4. Testing Strategy

### **Unit Tests**
- Form validation tests
- View permission tests
- Model method tests

### **Integration Tests**
- Admin workflow testing
- AJAX form submissions
- Cross-page navigation

### **Manual Testing**
- Court CRUD operations
- Payment verification flow
- Error handling scenarios

## 5. Implementation Order

1. **Views.py enhancements** (AdminFieldCreateView, new views)
2. **Forms.py validations** (duplicate checking, custom validations)
3. **admin_field_form.html completion** (all fields, JavaScript)
4. **admin_verify_payment.html creation** (payment verification UI)
5. **admin_court_management.html updates** (navigation links)
6. **URL updates** (new admin routes)
7. **Testing and verification**

This plan ensures all admin functionality is complete and properly integrated with the existing booking system.