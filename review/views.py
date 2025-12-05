from django.shortcuts import render, redirect, get_object_or_404
from review.forms import ReviewForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.utils.html import strip_tags
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.db.models import Q, Avg, Count, Value
from django.db.models.functions import Coalesce
from django.core import serializers
from django.http import HttpResponse
import requests, json

from review.models import Review
from booking.models import PlayingField

import statistics

def add_review(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({
                'status': 'error',
                'toast_type': 'error',
                'message': 'You must be logged in to submit a review.'
            }, status=403)

        form = ReviewForm(request.POST)

        if form.is_valid():
            field = form.cleaned_data['field']

            # Check if user already reviewed this field
            existing = Review.objects.filter(user=request.user, field=field).first()

            if existing:
                # Update existing review
                existing.rating = form.cleaned_data['rating']
                existing.komentar = form.cleaned_data['komentar']
                existing.save()

                return JsonResponse({
                    'status': 'success',
                    'toast_type': 'success',
                    'message': 'Review updated successfully.'
                })

            # Create new review
            review = form.save(commit=False)
            review.user = request.user
            review.save()

            return JsonResponse({
                'status': 'success',
                'toast_type': 'success',
                'message': 'Review added successfully.'
            })

        return JsonResponse({
            'status': 'error',
            'errors': dict(form.errors),
            'toast_type': 'error',
            'message': 'Failed to add review.'
        }, status=400)

    # GET request (modal form rendering)
    field = None
    field_id = request.GET.get('field')
    if field_id:
        field = get_object_or_404(PlayingField, pk=field_id)

    form = ReviewForm()
    context = {'form': form, 'field': field}

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('add_review.html', context, request=request)
        return HttpResponse(html)

    return redirect('review:review_list')

# Also handles sorting logic and admin analytics
def review_list(request):
    """
    Displays playing fields with review previews. Supports sorting by average rating
    (highest->lowest or lowest->highest). Also computes admin analytics (mean, median, mode, total).
    """

    # Base queryset: only active fields (keep your previous behavior)
    fields = PlayingField.objects.all()

    # Annotate with average rating and review count.
    # Coalesce ensures avg_rating is 0 if there are no reviews (Q2: treat as 0).
    fields = fields.annotate(
        avg_rating=Coalesce(Avg('review__rating'), Value(0.0)),
        review_count=Coalesce(Count('review'), Value(0))
    )

    # Sorting: read from GET param 'sort'
    # supported values: 'avg_desc' (highest to lowest), 'avg_asc' (lowest to highest)
    sort = request.GET.get('sort', 'none')
    if sort == 'avg_desc':
        fields = fields.order_by('-avg_rating', '-review_count', 'name')
    elif sort == 'avg_asc':
        fields = fields.order_by('avg_rating', '-review_count', 'name')
    else:
        # default ordering (you can tweak)
        fields = fields.order_by('-id')

    # Admin analytics: compute across ALL reviews (Q3)
    analytics = {}
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        ratings_qs = Review.objects.values_list('rating', flat=True)
        ratings = list(ratings_qs)

        total_reviews = len(ratings)
        mean = None
        median = None
        mode = None

        if total_reviews > 0:
            # Mean
            # Use Avg from DB for high precision, but fallback to python statistics.mean if needed
            db_mean = Review.objects.aggregate(avg=Avg('rating'))['avg']
            mean = float(db_mean) if db_mean is not None else statistics.mean(ratings)

            # Median
            try:
                median = float(statistics.median(ratings))
            except Exception:
                # fallback: compute manually
                ratings_sorted = sorted(ratings)
                n = len(ratings_sorted)
                mid = n // 2
                if n % 2 == 1:
                    median = float(ratings_sorted[mid])
                else:
                    median = (ratings_sorted[mid - 1] + ratings_sorted[mid]) / 2.0

            # Mode: use multimode and choose the smallest rating in case of tie
            try:
                modes = statistics.multimode(ratings)
                mode = float(min(modes))
            except Exception:
                mode = None

        analytics = {
            'mean': mean,
            'median': median,
            'mode': mode,
            'total_reviews': total_reviews
        }

    context = {
        'fields': fields,
        'sort': sort,
        'analytics': analytics
    }

    return render(request, 'review_list.html', context)


def view_comments(request, field_id):
    field = get_object_or_404(PlayingField, pk=field_id)
    reviews = Review.objects.filter(field=field).order_by('-id')

    is_admin_user = (
        request.user.is_authenticated and
        (request.user.is_staff or request.user.is_superuser)
    )

    context = {
        'field': field,
        'reviews': reviews,
        'is_admin': is_admin_user
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('view_comments.html', context, request=request)
        return HttpResponse(html)

    return redirect('review:review_list')


# Admin
def is_admin(user):
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_admin)
def delete_review(request, review_id):
    if request.method == 'POST':
        review = get_object_or_404(Review, pk=review_id)
        field_id = review.field.id if hasattr(review, 'field') and review.field else None
        review.delete()

        return JsonResponse({
            'status': 'success',
            'toast_type': 'success',
            'message': 'Review deleted successfully.',
            'field_id': field_id
        })

    return JsonResponse({
        'status': 'error',
        'toast_type': 'error',
        'message': 'Invalid request method.'
    }, status=400)


# Search bar 
def review_list_search_bar(request):
    search_query = request.GET.get('search', '')
    fields = PlayingField.objects.filter(is_active=True)

    if search_query:
        fields = fields.filter(
            Q(name__icontains=search_query) | Q(city__icontains=search_query) | Q(address__icontains=search_query)
        )

    return render(request, 'review_list.html', {'fields': fields})

# JSON helpers (for dev)
def show_json(request):
    review_list = Review.objects.all()
    data = [
        {
            'username': review.user.username,
            'rating': review.rating,
            'comment': review.komentar,
            'fieldName': review.field.name,
        }
        for review in review_list
    ]
    return JsonResponse(data, safe=False)

# Flutter views
def proxy_image(request):
    image_url = request.GET.get('url')
    if not image_url:
        return HttpResponse('No URL provided', status=400)
    
    try:
        # Fetch image from external source
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        
        # Return the image with proper content type
        return HttpResponse(
            response.content,
            content_type=response.headers.get('Content-Type', 'image/jpeg')
        )
    except requests.RequestException as e:
        return HttpResponse(f'Error fetching image: {str(e)}', status=500)

@csrf_exempt
def add_review_flutter(request):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "Unauthenticated"}, status=401)

    try:
        data = json.loads(request.body)

        field_name = strip_tags(data.get("field_name", ""))
        rating = int(data.get("rating", 0))
        komentar = strip_tags(data.get("comment", ""))

        field = PlayingField.objects.filter(name=field_name).first()
        if field is None:
            return JsonResponse({"status": "error", "message": "Field not found"}, status=404)

        # Replace review if exists, else create
        review_obj, created = Review.objects.update_or_create(
            user=request.user,
            field=field,
            defaults={
                "rating": rating,
                "komentar": komentar,
            }
        )

        return JsonResponse({
            "status": "success",
            "action": "created" if created else "updated"
        }, status=200)

    except Exception as e:
        print("ADD REVIEW ERROR:", e)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@csrf_exempt
def delete_review_flutter(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

    # Admin check
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({"status": "error", "message": "Unauthorized"}, status=401)

    try:
        data = json.loads(request.body)
        username = data.get("username")
        field_name = data.get("field_name")

        review = Review.objects.filter(
            user__username=username,
            field__name=field_name
        ).first()

        if review is None:
            return JsonResponse({"status": "error", "message": "Review not found"}, status=404)

        review.delete()

        return JsonResponse({"status": "success"}, status=200)

    except Exception as e:
        print("DELETE REVIEW ERROR:", e)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
