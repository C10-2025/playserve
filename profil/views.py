from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .forms import RegistrationFormStep1, RegistrationFormStep2, ProfileUpdateForm
from .models import Profile

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
    
    user_data = request.session['registration_data']

    if request.method == 'POST':
        form = RegistrationFormStep2(request.POST)
        if form.is_valid():
            profile_data = form.cleaned_data
            
            username = user_data['username']
            password = user_data['password']
            
            try:
                user = User.objects.create_user(username=username, password=password)
            except Exception:
                return JsonResponse({'status': 'error', 'toast_type': 'error', 'message': 'Registration failed due to a server error.'}, status=500)

            Profile.objects.create(
                user=user,
                lokasi=profile_data['lokasi'],
                instagram=profile_data.get('instagram', ''),
                avatar=profile_data['avatar']
            )

            user_auth = authenticate(request, username=username, password=password)
            if user_auth is not None:
                login(request, user_auth)
            
            del request.session['registration_data'] 
            
            return JsonResponse({
                'status': 'success', 
                'toast_type': 'success', 
                'message': 'Registration successful! Welcome to PlayServe.', 
                'redirect_url': '/'
            })
        else:
            errors = dict(form.errors.items())
            return JsonResponse({'status': 'error', 'errors': errors, 'toast_type': 'error', 'message': 'Please correct the profile details.'}, status=400)
    
    form = RegistrationFormStep2()
    return render(request, 'register2.html', {'form': form, 'user_data': user_data})


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

    return render(request, 'profile_update.html', {'form': form})