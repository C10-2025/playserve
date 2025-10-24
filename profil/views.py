from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from .forms import RegistrationFormStep1, RegistrationFormStep2, ProfileUpdateForm
from .models import Profile
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q

def register1(request):
    if request.method == 'POST':
        form = RegistrationFormStep1(request.POST)
        if form.is_valid():
            request.session['registration_data'] = {
                'username': form.cleaned_data['username'],
                'password': form.cleaned_data['password'],
            }
            return JsonResponse({'status': 'success', 'redirect_url': '/profile/register/step2/'})
        else:
            errors = dict(form.errors.items())
            return JsonResponse({'status': 'error', 'errors': errors, 'toast_type': 'error', 'message': 'Please correct the errors in step 1.'}, status=400)
    
    form = RegistrationFormStep1()
    return render(request, 'register1.html', {'form': form})

def register2(request):
    if 'registration_data' not in request.session:
        return redirect('profil:register1')
    
    if request.method == 'POST':
        form = RegistrationFormStep2(request.POST)
        if form.is_valid():
            user_data = request.session['registration_data']
            username = user_data['username']
           
            if User.objects.filter(username=username).exists():
                return JsonResponse({'status': 'error', 'message': 'This username has already been taken.'}, status=400)
            user = User.objects.create_user(
                username=username,
                password=user_data['password']
            )
           
            profile = user.profile
            profile.lokasi = form.cleaned_data['lokasi']
            profile.instagram = form.cleaned_data.get('instagram', '')
            profile.avatar = form.cleaned_data['avatar']
            profile.save()
            
            del request.session['registration_data']
            login(request, user)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Registration successful! Welcome.',
                'redirect_url': '/'
            })
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid data provided.', 'errors': form.errors}, status=400)
            
    return render(request, 'register2.html')

def login_ajax(request):
    if request.method == 'POST':
        data = request.POST
        username = data.get('username')
        password = data.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return JsonResponse({
                'status': 'success', 
                'toast_type': 'success', 
                'message': 'Login successful.',
                'redirect_url': '/'
            })
        else:
            return JsonResponse({
                'status': 'error', 
                'toast_type': 'error', 
                'message': 'Invalid username or password.',
            }, status=401)
            
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('main:home')

@login_required
def profile_update_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return JsonResponse({
                'status': 'success',
                'toast_type': 'success',
                'message': 'Profile updated successfully.'
            })
        errors = dict(form.errors.items())
        return JsonResponse({'status': 'error', 'errors': errors, 'toast_type': 'error', 'message': 'Failed to update profile.'}, status=400)
    else:
        form = ProfileUpdateForm(instance=request.user.profile)

    return render(request, 'profile_update.html', {'form': form, 'profile' : request.user.profile})

def is_admin(user):
    if not user.is_authenticated:
        return False
    return user.is_superuser or (hasattr(user, 'profile') and user.profile.role == Profile.Role.ADMIN)

@login_required
@user_passes_test(is_admin, login_url='/')
def manage_users_view(request):
    query = request.GET.get('q', '')
    profiles_list = Profile.objects.exclude(user=request.user).select_related('user').order_by('user__username')
    if query:
        profiles_list = profiles_list.filter(user__username__icontains=query)
    context = {
        'profiles': profiles_list,
        'search_query': query,
    }
    return render(request, 'admin_profile.html', context)

@login_required
@user_passes_test(is_admin, login_url='/')
def delete_user_view(request, user_id):
    if request.method == 'POST':
        user_to_delete = get_object_or_404(User, id=user_id)
        if user_to_delete == request.user:
            return JsonResponse({'status': 'error', 'message': 'Cannot delete yourself.'}, status=403)
        try:
            username = user_to_delete.username
            user_to_delete.delete()
            return JsonResponse({'status': 'success', 'message': f'User {username} deleted successfully.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)