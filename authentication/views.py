from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login as auth_login, update_session_auth_hash
from django.contrib.auth import logout as auth_logout
from django.http import JsonResponse
from django.contrib.auth.models import User
from profil.models import Profile
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from profil.models import Profile  
import json
import re

@csrf_exempt
def login(request):
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "Invalid method"}, status=405)

    username = request.POST.get("username")
    password = request.POST.get("password")

    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            auth_login(request, user)
            return JsonResponse({
                "status": True,
                "message": "Login successful!",
                "username": user.username,
                "is_admin": user.is_superuser,
            }, status=200)
        else:
            return JsonResponse({
                "status": False,
                "message": "Login failed, account is disabled."
            }, status=401)

    return JsonResponse({
        "status": False,
        "message": "Login failed, please check your username or password."
    }, status=401)

@csrf_exempt
def register_step1(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        password1 = data.get('password1')
        password2 = data.get('password2')

        if not username or not password1 or not password2:
            return JsonResponse({
                "status": False,
                "message": "All fields are required."
            }, status=400)

        if len(password1) < 8:
            return JsonResponse({
                "status": False, 
                "message": "Password must be at least 8 characters long."
            }, status=400)

        if password1 != password2:
            return JsonResponse({
                "status": False,
                "message": "Passwords do not match."
            }, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({
                "status": False,
                "message": "Username already exists."
            }, status=400)

        user = User.objects.create_user(username=username, password=password1)
        Profile.objects.get_or_create(user=user)
        return JsonResponse({
            "status": "success",
            "username": username,
            "message": "Step 1 complete. Proceed to step 2."
        }, status=200)

    return JsonResponse({
        "status": False,
        "message": "Invalid request method."
    }, status=400)

@csrf_exempt
def register_step2(request):
    if request.method != "POST":
        return JsonResponse({
            "status": False,
            "message": "Invalid request method."
        }, status=400)

    try:
        data = json.loads(request.body)
        username = data.get("username")
        lokasi = data.get("lokasi")
        instagram = data.get("instagram", "")
        avatar_path = data.get("avatar", "image/avatar1.svg").replace("assets/", "")

        if not username:
            return JsonResponse({
                "status": False,
                "message": "Username is required."
            }, status=400)
        if instagram:
            if instagram.startswith('@'):
                return JsonResponse({"status": False, "message": "No need for @ at the beginning."}, status=400)
            if not re.match(r'^[a-zA-Z0-9._]+$', instagram):
                return JsonResponse({"status": False, "message": "Invalid Instagram characters."}, status=400)
        
        user = User.objects.get(username=username)
        profile = Profile.objects.get(user=user)
        profile.lokasi = lokasi
        profile.instagram = instagram
        profile.avatar = avatar_path
        profile.save()

        return JsonResponse({
            "status": "success",
            "username": username,
            "message": "Registration completed successfully!"
        }, status=200)

    except User.DoesNotExist:
        return JsonResponse({
            "status": "error",
            "message": "User not found."
        }, status=404)
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": str(e)
        }, status=500)

@csrf_exempt
def check_login(request):
    if request.user.is_authenticated:
        return JsonResponse({
            "is_logged_in": True,
            "username": request.user.username
        }, status=200)
    else:
        return JsonResponse({
            "is_logged_in": False
        }, status=200)

@csrf_exempt
def logout(request):
    if request.user.is_authenticated:
        auth_logout(request)
        return JsonResponse({
            "status": True,
            "message": "Successfully logged out."
        }, status=200)
    else:
        return JsonResponse({
            "status": False,
            "message": "No active session found."
        }, status=400)

@csrf_exempt
def edit_profile(request):
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "Invalid request method."}, status=400)

    if not request.user.is_authenticated:
        return JsonResponse({"status": False, "message": "User not logged in."}, status=401)

    try:
        data = json.loads(request.body)
        username = data.get("username")
        lokasi = data.get("lokasi")
        instagram = data.get("instagram")
        avatar = data.get("avatar")
        new_password = data.get("new_password")
        confirm_password = data.get("confirm_password")

        user = request.user
        profile = Profile.objects.get(user=user)
        
        if instagram:
            if instagram.startswith('@'):
                return JsonResponse({"status": False, "message": "No need for @ at the beginning."}, status=400)
            if not re.match(r'^[a-zA-Z0-9._]+$', instagram):
                return JsonResponse({"status": False, "message": "Invalid Instagram characters."}, status=400)

        if new_password:
            if len(new_password) < 8:
                return JsonResponse({"status": False, "message": "Password must be at least 8 characters."}, status=400)
            if new_password != confirm_password:
                return JsonResponse({"status": False, "message": "Passwords do not match."}, status=400)
            
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
        
        if username and username != user.username:
            if hasattr(profile, "username_changed") and profile.username_changed:
                return JsonResponse({"status": False, "message": "Username cannot be changed again."}, status=400)
            if User.objects.filter(username=username).exists():
                return JsonResponse({"status": False, "message": "Username already exists."}, status=400)
            user.username = username
            user.save()
            profile.username_changed = True

        if lokasi:
            profile.lokasi = lokasi
        if instagram is not None:
            profile.instagram = instagram
        if avatar:
            profile.avatar = avatar

        profile.save()

        return JsonResponse({
            "status": True,
            "message": "Profile updated successfully.",
            "username": user.username,
            "lokasi": profile.lokasi,
            "instagram": profile.instagram,
            "avatar": profile.avatar,
        }, status=200)
    except Exception as e:
        return JsonResponse({"status": False, "message": str(e)}, status=500)

def get_user(request):
    user = request.user
    profile = getattr(user, 'profile', None)

    if user.is_superuser or user.is_staff:
        rank = "ADMIN"
    else:
        rank = getattr(profile, 'rank', 'BRONZE')

    data = {
        "status": True,
        "username": user.username,
        "rank": rank,
        "avatar": getattr(profile, 'avatar', 'image/avatar1.svg'),
        "instagram": getattr(profile, 'instagram', ''),
        "lokasi": getattr(profile, 'lokasi', 'Jakarta'),
    }
    return JsonResponse(data)

@csrf_exempt
def check_admin_status(request):
    if not request.user.is_authenticated:
        return JsonResponse({
            "status": False,
            "is_admin": False,
            "message": "User not logged in."
        }, status=401)

    return JsonResponse({
        "status": True,
        "is_admin": request.user.is_superuser,
        "username": request.user.username
    }, status=200)

@csrf_exempt
def get_all_users(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({"status": False, "message": "Unauthorized"}, status=403)

    users = User.objects.all().select_related('profile')
    data = []

    for u in users:
        if u.is_superuser:
            continue
            
        try:
            profile = u.profile
        except:
            profile = None
        data.append({
            "username": str(u.username) if u.username else "Unknown",
            "avatar": str(profile.avatar) if (profile and profile.avatar) else "image/avatar1.png",
            "rank": str(profile.rank) if (profile and profile.rank) else "BRONZE",
            "instagram": str(profile.instagram) if (profile and profile.instagram) else "",
            "lokasi": str(profile.lokasi) if (profile and profile.lokasi) else "Unknown",
        })

    return JsonResponse({"status": True, "users": data}, status=200)

@csrf_exempt
def admin_delete_user(request):
    if not request.user.is_authenticated or not request.user.is_superuser:
        return JsonResponse({
            "status": False,
            "message": "Unauthorized. Only admins can delete users."
        }, status=403)

    try:
        username = request.POST.get("username")

        if not username:
            return JsonResponse({
                "status": False,
                "message": "Username is required."
            }, status=400)

        target_user = User.objects.get(username=username)

        if target_user.is_superuser:
            return JsonResponse({
                "status": False,
                "message": "Cannot delete an admin account."
            }, status=400)

        if hasattr(target_user, 'profile'):
            target_user.profile.delete()
            
        target_user.delete()

        return JsonResponse({
            "status": True,
            "message": f"User '{username}' has been deleted successfully."
        }, status=200)

    except User.DoesNotExist:
        return JsonResponse({
            "status": False,
            "message": "User not found."
        }, status=404)
    except Exception as e:
        return JsonResponse({
            "status": False,
            "message": str(e)
        }, status=500)