from django.shortcuts import render, redirect, get_object_or_404
from review.forms import ReviewForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string

from review.models import Review
from booking.models import PlayingField


def add_review(request):
    # POST: create a review (AJAX expected)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save()
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

    # GET: render AJAX form. Expect optional field id as ?field=ID
    field = None
    field_id = request.GET.get('field')
    if field_id:
        field = get_object_or_404(PlayingField, pk=field_id)

    form = ReviewForm()
    context = {
        'form': form,
        'field': field
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('add_review.html', context, request=request)
        return HttpResponse(html)

    return redirect('review:review_list')


def review_list(request):
    fields = PlayingField.objects.all()
    context = {'fields': fields}

    return render(request, 'review_list.html', context)


def view_comments(request, field_id):
    field = get_object_or_404(PlayingField, pk=field_id)
    comments = Review.objects.filter(field=field).order_by('-id')

    is_admin_user = (
        request.user.is_authenticated and
        (request.user.is_staff or request.user.is_superuser)
    )

    context = {
        'field': field,
        'comments': comments,
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

