from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.urls import reverse, reverse_lazy
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
        sort = self.request.GET.get('sort', '-price_per_hour')
        if sort == 'price_low':
            queryset = queryset.order_by('price_per_hour')
        elif sort == 'name':
            queryset = queryset.order_by('name')
        else:
            queryset = queryset.order_by('-price_per_hour')


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

    def get_form_kwargs(self):
        """Override to remove 'instance' for non-ModelForm steps"""
        kwargs = super().get_form_kwargs()
        step = self.request.GET.get('step', '1')
        if step in ['1', '2']:  # Regular forms don't accept 'instance'
            kwargs.pop('instance', None)
        return kwargs

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

            # Skip validation during creation since we already validated in step 2
            booking._skip_validation = True

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


def admin_court_management(request):
    """Custom admin dashboard for court and booking management - similar to community my_communities"""
    is_admin = hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN'

    if not is_admin:
        from django.contrib import messages
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('main:home')

    # Get admin's courts
    courts = PlayingField.objects.filter(created_by=request.user).order_by('-created_at')

    # Stats for admin's courts
    my_courts = courts
    all_bookings = Booking.objects.filter(field__in=my_courts)

    context = {
        'courts': courts,
        'is_admin': is_admin,
        'profile': getattr(request.user, 'profile', None) if request.user.is_authenticated else None,
        'total_courts': my_courts.count(),
        'active_courts': my_courts.filter(is_active=True).count(),
        'total_bookings': all_bookings.count(),
        'pending_verifications': all_bookings.filter(status='PENDING_PAYMENT').count(),
        'confirmed_bookings': all_bookings.filter(status='CONFIRMED').count(),
        'total_revenue': sum(b.total_price for b in all_bookings.filter(status__in=['CONFIRMED', 'COMPLETED'])),
        'recent_bookings': all_bookings.select_related('field', 'user').order_by('-created_at')[:5],
    }

    return render(request, 'booking/admin_court_management.html', context)


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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # Pass user for duplicate validation
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Court added successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('booking:admin_court_management')

    def form_invalid(self, form):
        # Debug form errors
        print("Form errors:", form.errors)
        print("Non-field errors:", form.non_field_errors())
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class AdminFieldUpdateView(LoginRequiredMixin, AdminTestMixin, UpdateView):
    """Admin: Edit existing court"""
    model = PlayingField
    form_class = FieldForm
    template_name = 'booking/admin_field_form.html'

    def get_queryset(self):
        return PlayingField.objects.filter(created_by=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user  # Pass user for duplicate validation
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f'Court "{form.instance.name}" updated successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('booking:admin_court_management')


class AdminFieldDeleteView(LoginRequiredMixin, AdminTestMixin, DeleteView):
    """Admin: Delete court (soft delete by deactivating)"""
    model = PlayingField
    template_name = 'booking/admin_field_confirm_delete.html'
    success_url = reverse_lazy('booking:admin_court_management')

    def get_queryset(self):
        return PlayingField.objects.filter(created_by=self.request.user)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Soft delete by deactivating instead of hard delete
        self.object.is_active = False
        self.object.save()
        messages.success(request, f'Court "{self.object.name}" has been deactivated.')
        return redirect(self.success_url)


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
