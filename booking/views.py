import json
from datetime import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from .models import PlayingField, Booking
from .forms import BookingStepOneForm, BookingStepTwoForm, BookingStepThreeForm, FieldForm
from django.http import HttpResponse
from django.core import serializers


def _serialize_field(field, request):
    """Serialize PlayingField to dict for JSON APIs."""
    return {
        "id": str(field.id),
        "name": field.name,
        "address": field.address,
        "city": field.city,
        "latitude": float(field.latitude) if field.latitude is not None else None,
        "longitude": float(field.longitude) if field.longitude is not None else None,
        "number_of_courts": field.number_of_courts,
        "has_lights": field.has_lights,
        "has_backboard": field.has_backboard,
        "court_surface": field.court_surface,
        "price_per_hour": float(field.price_per_hour),
        "owner_name": field.owner_name,
        "owner_contact": field.owner_contact,
        "owner_bank_account": field.owner_bank_account,
        "opening_time": field.opening_time.isoformat() if field.opening_time else None,
        "closing_time": field.closing_time.isoformat() if field.closing_time else None,
        "description": field.description,
        "amenities": field.amenities,
        "court_image": (
            request.build_absolute_uri(field.court_image.url)
            if field.court_image else None
        ),
        "image_url": field.image_url,
        "created_by": field.created_by.username if field.created_by else None,
        "created_at": field.created_at.isoformat() if field.created_at else None,
        "updated_at": field.updated_at.isoformat() if field.updated_at else None,
        "is_active": field.is_active,
        "price_range_category": field.price_range_category,
    }


def _serialize_booking(booking, request):
    """Serialize Booking to dict for JSON APIs."""
    return {
        "id": booking.id,
        "field": {
            "id": booking.field.id,
            "name": booking.field.name,
            "city": booking.field.city,
            "image_url": booking.field.image_url,
            "court_image": (
                request.build_absolute_uri(booking.field.court_image.url)
                if booking.field.court_image else None
            ),
        },
        "booking_date": booking.booking_date.isoformat(),
        "start_time": booking.start_time.isoformat(),
        "end_time": booking.end_time.isoformat(),
        "duration_hours": float(booking.duration_hours),
        "total_price": float(booking.total_price),
        "status": booking.status,
        "notes": booking.notes,
        "booker_name": booking.booker_name,
        "booker_phone": booking.booker_phone,
        "booker_email": booking.booker_email,
        "payment_proof_url": request.build_absolute_uri(booking.payment_proof.url) if booking.payment_proof else None,
        "can_cancel": booking.can_cancel,
        "created_at": booking.created_at.isoformat() if booking.created_at else None,
        "confirmed_at": booking.confirmed_at.isoformat() if booking.confirmed_at else None,
        "cancelled_at": booking.cancelled_at.isoformat() if booking.cancelled_at else None,
    }

class FieldListView(ListView):
    """Court listing with search and filters"""
    model = PlayingField
    template_name = 'booking/field_list.html'
    context_object_name = 'fields'
    paginate_by = 12

    def get_queryset(self):
        queryset = PlayingField.objects.filter(is_active=True)

        # Search 
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
        user_profile = self.request.user.profile
        context['profile'] = user_profile
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
            elif len(booked_slots) >= 10:  
                status = 'full'
            else:
                status = 'limited'

            availability_data.append({
                'date': date,
                'status': status,
                'booked_count': len(booked_slots)
            })

        context['availability_calendar'] = availability_data
        user_profile = self.request.user.profile
        context['profile'] = user_profile
        return context


class BookingCreateView(LoginRequiredMixin, CreateView):
    """
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
        if step in ['1', '2']:  # Regular forms ga accept instance
            kwargs.pop('instance', None)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['field'] = self.field
        context['step'] = self.request.GET.get('step', '1')
        user_profile = self.request.user.profile
        context['profile'] = user_profile

        if context['step'] == '1':
            context['form'].initial = {
                'booker_name': self.request.user.get_full_name() or self.request.user.username,
                'booker_email': self.request.user.email,
            }

        return context

    def form_valid(self, form):
        step = self.request.GET.get('step', '1')

        if step == '1':
            self.request.session['booking_step1'] = form.cleaned_data
            return redirect(f"{self.request.path}?step=2")

        elif step == '2':
            booking_data = form.cleaned_data

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

        else:  
            step1_data = self.request.session.get('booking_step1', {})
            step2_data = self.request.session.get('booking_step2', {})

            booking = form.save(commit=False)
            booking.user = self.request.user
            booking.field = self.field

            booking.booker_name = step1_data['booker_name']
            booking.booker_phone = step1_data['booker_phone']
            booking.booker_email = step1_data.get('booker_email', '')

            from datetime import datetime
            booking.booking_date = datetime.strptime(step2_data['booking_date'], '%Y-%m-%d').date()
            booking.start_time = datetime.strptime(step2_data['start_time'], '%H:%M:%S').time()
            booking.end_time = datetime.strptime(step2_data['end_time'], '%H:%M:%S').time()
            booking.duration_hours = step2_data['duration_hours']
            booking.notes = step2_data.get('notes', '')

            booking.total_price = booking.calculate_price()

            booking._skip_validation = True

            try:
                booking.save()

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

        user_profile = self.request.user.profile
        context['profile'] = user_profile
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

    # Get all courts for admin management (including system-imported ones)
    courts = PlayingField.objects.all().order_by('-created_at')

    # Stats for all courts (admin can manage all)
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

        user_profile = self.request.user.profile
        context['profile'] = user_profile

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
        # Allow editing all courts for admin management
        return PlayingField.objects.all()

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
        # Allow deleting all courts for admin management
        return PlayingField.objects.all()

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
        user_profile = self.request.user.profile
        context['profile'] = user_profile
        return context


@login_required
def admin_verify_payment(request, booking_id):
    """Admin: Verify payment and confirm booking"""
    from django.contrib import messages

    # Ensure user is admin and booking exists (admins can verify any booking)
    is_admin = hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN'
    if not is_admin:
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('main:home')

    booking = get_object_or_404(Booking.objects.select_related('field'), id=booking_id)

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

        return redirect('booking:admin_court_management')

    return render(request, 'booking/admin_verify_payment.html', {
        'booking': booking
    })

# === JSON API endpoints ===

def api_fields(request):
    """List active fields for mobile with filtering and pagination support."""
    from django.core.paginator import Paginator

    queryset = PlayingField.objects.filter(is_active=True)

    # Search
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(address__icontains=search) |
            Q(city__icontains=search)
        )

    # City filter
    city = request.GET.get('city')
    if city:
        queryset = queryset.filter(city=city)

    # Price range filter
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min:
        queryset = queryset.filter(price_per_hour__gte=price_min)
    if price_max:
        queryset = queryset.filter(price_per_hour__lte=price_max)

    # Features filter
    if request.GET.get('has_lights') == 'true':
        queryset = queryset.filter(has_lights=True)
    if request.GET.get('has_backboard') == 'true':
        queryset = queryset.filter(has_backboard=True)

    # Sorting
    sort = request.GET.get('sort', 'default')
    if sort == 'price_low':
        queryset = queryset.order_by('price_per_hour')
    elif sort == 'name':
        queryset = queryset.order_by('name')
    else:
        queryset = queryset.order_by('-price_per_hour')

    # Pagination
    page_number = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 20))

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page_number)

    data = [_serialize_field(field, request) for field in page_obj]

    return JsonResponse({
        "status": "success",
        "data": data,
        "pagination": {
            "page": page_obj.number,
            "page_size": page_size,
            "total_pages": paginator.num_pages,
            "total_items": paginator.count,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
        }
    }, safe=False)


def api_availability(request):
    """Check availability (wrapper around check_availability_ajax)."""
    field_id = request.GET.get('field_id')
    date = request.GET.get('date')
    start_time = request.GET.get('start_time')
    end_time = request.GET.get('end_time')

    if not all([field_id, date, start_time, end_time]):
        return JsonResponse({
            "status": "error",
            "available": False,
            "message": "Missing parameters"
        }, status=400)

    try:
        field = PlayingField.objects.get(id=field_id)
        temp_booking = Booking(
            field=field,
            booking_date=datetime.strptime(date, '%Y-%m-%d').date(),
            start_time=datetime.strptime(start_time, '%H:%M').time(),
            end_time=datetime.strptime(end_time, '%H:%M').time(),
        )
        is_available, message = temp_booking.check_availability()
        return JsonResponse({
            "status": "success",
            "available": is_available,
            "message": message
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "available": False,
            "message": str(e)
        }, status=400)


@csrf_exempt
@login_required
def api_book(request):
    """Create a booking via JSON."""
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    required = ["field_id", "booking_date", "start_time", "end_time", "booker_name", "booker_phone"]
    if any(k not in payload or not payload[k] for k in required):
        return JsonResponse({"status": "error", "message": "Missing required fields"}, status=400)

    try:
        field = PlayingField.objects.get(id=payload["field_id"], is_active=True)
    except PlayingField.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Field not found"}, status=404)

    try:
        booking_date = datetime.strptime(payload["booking_date"], "%Y-%m-%d").date()
        start_time = datetime.strptime(payload["start_time"], "%H:%M").time()
        end_time = datetime.strptime(payload["end_time"], "%H:%M").time()
    except ValueError:
        return JsonResponse({"status": "error", "message": "Invalid date/time format"}, status=400)

    temp_booking = Booking(
        field=field,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
    )
    is_available, message = temp_booking.check_availability()
    if not is_available:
        return JsonResponse({"status": "error", "message": message}, status=409)

    duration_hours = payload.get("duration_hours")
    if not duration_hours:
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        duration_hours = (end_minutes - start_minutes) / 60

    booking = Booking(
        user=request.user,
        field=field,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        duration_hours=duration_hours,
        booker_name=payload["booker_name"],
        booker_phone=payload["booker_phone"],
        booker_email=payload.get("booker_email", ""),
        notes=payload.get("notes", ""),
        status="PENDING_PAYMENT",
    )

    booking.total_price = booking.calculate_price()
    booking.save()

    return JsonResponse({
        "status": "success",
        "message": "Booking created",
        "data": _serialize_booking(booking, request)
    }, status=201)


@login_required
def api_my_bookings(request):
    """List bookings for the current user."""
    bookings = Booking.objects.filter(user=request.user).select_related("field").order_by('-booking_date', '-start_time')
    data = [_serialize_booking(b, request) for b in bookings]
    return JsonResponse({"status": "success", "data": data}, safe=False)


@csrf_exempt
@login_required
def api_cancel_booking(request):
    """Cancel a booking if allowed."""
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

    booking_id = payload.get("booking_id")
    if not booking_id:
        return JsonResponse({"status": "error", "message": "Missing booking_id"}, status=400)

    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if not booking.can_cancel:
        return JsonResponse({"status": "error", "message": "Cannot cancel this booking"}, status=403)

    booking.status = 'CANCELLED'
    booking.cancelled_at = timezone.now()
    booking.save()

    return JsonResponse({"status": "success", "message": "Booking cancelled"})


# JSON helpers (dev only)
# Disclaimer: It should give you the necessary info for flutter version, but some 'ghost' fields are initialized as empty string
# or None/null
def show_json(request):
    fields = PlayingField.objects.all()
    data = [_serialize_field(field, request) for field in fields]
    return JsonResponse(data, safe=False)


# === Helper ===
def _is_admin(user):
    return hasattr(user, 'profile') and user.profile.role == 'ADMIN'


# === User: upload payment proof ===
@login_required
def api_upload_payment_proof(request, pk):
    """
    Upload payment proof for a user's pending booking.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    booking = get_object_or_404(
        Booking, pk=pk, user=request.user, status='PENDING_PAYMENT'
    )

    form = BookingStepThreeForm(
        data={"terms_agreed": True}, files=request.FILES, instance=booking
    )
    if form.is_valid():
        form.save()
        return JsonResponse({
            "status": "success",
            "message": "Payment proof uploaded",
            "data": _serialize_booking(booking, request)
        })
    return JsonResponse({"status": "error", "errors": form.errors}, status=400)


# === Admin Courts JSON APIs ===
@login_required
def admin_api_fields_list(request):
    if not _is_admin(request.user):
        return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)
    # Admin can manage ALL courts (consistent with web interface)
    fields = PlayingField.objects.all().order_by('-created_at')
    data = [_serialize_field(f, request) for f in fields]
    return JsonResponse({"status": "success", "data": data})

@login_required
def admin_api_field_create(request):
    if not _is_admin(request.user):
        return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    form = FieldForm(data=request.POST, files=request.FILES, user=request.user)
    if form.is_valid():
        field = form.save(commit=False)
        field.created_by = request.user
        field.save()
        return JsonResponse({"status": "success", "data": _serialize_field(field, request)})
    return JsonResponse({"status": "error", "errors": form.errors}, status=400)


@login_required
def admin_api_field_update(request, pk):
    if not _is_admin(request.user):
        return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    field = get_object_or_404(PlayingField, pk=pk, created_by=request.user)
    form = FieldForm(data=request.POST, files=request.FILES, instance=field, user=request.user)
    if form.is_valid():
        field = form.save()
        return JsonResponse({"status": "success", "data": _serialize_field(field, request)})
    return JsonResponse({"status": "error", "errors": form.errors}, status=400)


@login_required
def admin_api_field_delete(request, pk):
    if not _is_admin(request.user):
        return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    field = get_object_or_404(PlayingField, pk=pk, created_by=request.user)
    field.is_active = False
    field.save()
    return JsonResponse({"status": "success", "message": "Field deactivated"})


# === Admin Payment Verification JSON APIs ===
@login_required
def admin_api_pending_bookings(request):
    if not _is_admin(request.user):
        return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)
    # Admin can manage ALL pending bookings (consistent with web interface)
    bookings = Booking.objects.filter(
        status='PENDING_PAYMENT'
    ).select_related('field', 'user').order_by('-created_at')
    data = [_serialize_booking(b, request) for b in bookings]
    return JsonResponse({"status": "success", "data": data})


@login_required
def admin_api_booking_detail(request, pk):
    if not _is_admin(request.user):
        return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)
    # Admin can view ANY booking detail (consistent with web interface)
    booking = get_object_or_404(
        Booking.objects.select_related('field', 'user'),
        pk=pk
    )
    return JsonResponse({"status": "success", "data": _serialize_booking(booking, request)})


@login_required
def admin_api_verify_payment(request, pk):
    if not _is_admin(request.user):
        return JsonResponse({"status": "error", "message": "Forbidden"}, status=403)
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    # Admin can verify ANY booking (consistent with web interface)
    booking = get_object_or_404(
        Booking.objects.select_related('field', 'user'),
        pk=pk
    )

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        payload = {}

    decision = payload.get("decision")
    if decision not in ["CONFIRM", "REJECT"]:
        return JsonResponse({"status": "error", "message": "Invalid decision"}, status=400)

    if decision == "CONFIRM":
        booking.status = "CONFIRMED"
        booking.confirmed_at = timezone.now()
    else:
        booking.status = "CANCELLED"
        booking.cancelled_at = timezone.now()

    booking.save()
    return JsonResponse({"status": "success", "data": _serialize_booking(booking, request)})
