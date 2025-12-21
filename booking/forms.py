from django import forms
from .models import PlayingField, Booking
from datetime import datetime, time, timedelta

class BookingStepOneForm(forms.Form):
    """Step 1: Identity and Contact Information"""
    booker_name = forms.CharField(
        max_length=100,
        label="Full Name",
        widget=forms.TextInput(attrs={
            'class': 'w-full border rounded px-3 py-2 text-gray-600',
            'placeholder': 'Your full name'
        })
    )

    booker_phone = forms.CharField(
        max_length=20,
        label="Phone Number",
        widget=forms.TextInput(attrs={
            'class': 'w-full border rounded px-3 py-2 text-gray-600',
            'placeholder': '+62 812-3456-7890 or 081234567890'
        })
    )

    booker_email = forms.EmailField(
        required=False,
        label="Email (optional)",
        widget=forms.EmailInput(attrs={
            'class': 'w-full border rounded px-3 py-2 text-black',
            'placeholder': 'your@email.com'
        })
    )

    def clean_booker_phone(self):
        phone = self.cleaned_data.get('booker_phone')
        if phone:
            phone = phone.strip()
            clean_phone = phone.lstrip('+')
            if not clean_phone.isdigit():
                raise forms.ValidationError("Phone number must contain only digits.")
            if not (10 <= len(clean_phone) <= 15):
                raise forms.ValidationError("Phone number must be 10-15 digits long.")
            if not (phone.startswith('0') or phone.startswith('+62')):
                raise forms.ValidationError("Phone number must start with '0' or '+62'.")
        return phone


class BookingStepTwoForm(forms.Form):
    """Step 2: Date and Time Selection"""
    booking_date = forms.DateField(
        label="Select Date",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full border rounded px-3 py-2 text-gray-600',
            'min': datetime.now().strftime('%Y-%m-%d')
        })
    )

    start_time = forms.TimeField(
        label="Start Time",
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'w-full border rounded px-3 py-2 text-gray-600'
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
            'class': 'w-full border rounded px-3 py-2 text-gray-600',
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
            'price_per_hour', 'owner_name', 'owner_contact', 'owner_bank_account'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500'}),
            'address': forms.Textarea(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500', 'rows': 2}),
            'city': forms.Select(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500'}),
            'latitude': forms.NumberInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500', 'step': '0.000001'}),
            'number_of_courts': forms.NumberInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500'}),
            'court_surface': forms.Select(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500'}),
            'opening_time': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500'}),
            'closing_time': forms.TimeInput(attrs={'type': 'time', 'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500'}),
            'description': forms.Textarea(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500', 'rows': 4}),
            'price_per_hour': forms.NumberInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500'}),
            'owner_name': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500'}),
            'owner_contact': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500'}),
            'owner_bank_account': forms.TextInput(attrs={'class': 'w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-blue-500'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  # Extract user for validation
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

    def clean_name(self):
        """Validate court name uniqueness for this admin"""
        name = self.cleaned_data.get('name')
        if name and self.user:
            existing = PlayingField.objects.filter(
                name__iexact=name,
                created_by=self.user
            )
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError("You already have a court with this name. Please choose a different name.")
        return name

    def clean(self):
        """Additional form-wide validation"""
        cleaned_data = super().clean()
        opening_time = cleaned_data.get('opening_time')
        closing_time = cleaned_data.get('closing_time')

        # Validate operating hours make sense
        if opening_time and closing_time and opening_time >= closing_time:
            raise forms.ValidationError("Closing time must be after opening time.")

        return cleaned_data

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