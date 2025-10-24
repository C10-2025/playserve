from django.shortcuts import render, redirect, get_list_or_404, get_object_or_404
from review.forms import ReviewForm
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from review.models import Review

def add_review(request):
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save() # langsung simpen saja
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

    form = ReviewForm()
    context = {
        'form': form,
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('add_review.html', context, request=request)
        return HttpResponse(html)

    # Non-AJAX GET: redirect back to review list (we only show the form via modal)
    return redirect('review:review_list')


def review_list(request):
    reviews = Review.objects.all()
    context = {'reviews': reviews}
    return render(request, 'review_list.html', context)