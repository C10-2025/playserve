from django.shortcuts import render
from profil.models import Profile

def main_view(request):
    context = {}
    if request.user.is_authenticated:
        try:
            context['profile'] = request.user.profile
        except Profile.DoesNotExist:
            context['profile'] = None
            
    return render(request, 'main.html', context)