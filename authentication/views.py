from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth import logout as auth_logout
from django.http import JsonResponse
from django.contrib.auth.models import User
from profil.models import Profile
import json


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
                "username": user.username,
                "status": True,
                "message": "Login successful!"
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
        Profile.objects.get_or_create(user=user)  # ✅ aman dari IntegrityError

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
    """
    Step 2: Lengkapi profil user yang sudah dibuat di Step 1.
    """
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