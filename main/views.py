from django.shortcuts import render
from django.contrib.auth.models import User
from profil.models import Profile
from community.models import Community

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

                context.update({
                    'total_users': total_users,
                    'total_community': total_community,
                })

        except Profile.DoesNotExist:
            context['profile'] = None
            context['is_admin_access'] = False

    return render(request, 'main.html', context)