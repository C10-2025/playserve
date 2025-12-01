from django.shortcuts import render
from django.contrib.auth.models import User
from profil.models import Profile
from community.models import Community
from review.models import Review
from booking.models import PlayingField
from django.http import HttpResponse
import requests

def main_view(request):
    context = {}

    if request.user.is_authenticated:
        try:
            user_profile = request.user.profile
            context['profile'] = user_profile

            is_superuser = request.user.is_superuser
            is_biz_admin = user_profile.role == 'ADMIN'
            is_admin_access = is_superuser or is_biz_admin

            context['is_admin_access'] = is_admin_access

            if is_admin_access:
                total_users = User.objects.count()
                total_community = Community.objects.count()
                total_reviews = Review.objects.count()
                total_courts = PlayingField.objects.count()

                context.update({
                    'total_users': total_users,
                    'total_community': total_community,
                    'total_reviews': total_reviews,
                    'total_courts': total_courts
                })

        except Profile.DoesNotExist:
            context['profile'] = None
            context['is_admin_access'] = False

    return render(request, 'main.html', context)

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