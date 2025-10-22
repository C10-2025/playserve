from django.shortcuts import render
from review.forms import ReviewForm
from django.http import JsonResponse

# Create your views here.

""" def review(request):
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=request.lapangan.profile)
        if form.is_valid():
            review = form.save(commit=False)
            review.lapangan = request.lapangan
            review.save()
            return JsonResponse({
                'status': 'success',
                'toast_type': 'success',
                'message': 'Review added successfully.'
            })
        errors = dict(form.errors.items())
        return JsonResponse({'status': 'error', 'errors': errors, 'toast_type': 'error', 'message': 'Failed to add review.'}, status=400)
    else:
        form = ReviewForm(instance=request.user.profile) """