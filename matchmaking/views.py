from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q 
from django.db.models import F
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import MatchRequest, MatchSession 
from profil.models import Profile 
from django.contrib.auth.models import User
import json
from django.views.decorators.csrf import csrf_exempt

# Dashboard utama
@login_required 
def matchmaking_dashboard(request):
    user = request.user
    
    try:
        current_user_profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        return render(request, 'dashboard.html', {'view_type': 'NO_PROFILE', 'profile': None})
        
    base_context = {
        'profile': current_user_profile,
    }


    # Cek pertandingan aktif
    active_session = MatchSession.objects.filter(
        Q(player1=user) | Q(player2=user),
        result='PENDING'
    ).first()

    if active_session:
        # Jika ada sesi aktif, tampilkan halaman pertandingan
        opponent = active_session.player2 if active_session.player1 == user else active_session.player1
        
        try:
            opponent_profile = Profile.objects.get(user=opponent) 
        except Profile.DoesNotExist:
            opponent_profile = None
            
        context = {
            **base_context, 
            'view_type': 'ACTIVE_MATCH',
            'session': active_session,
            'opponent': opponent,
            'opponent_profile': opponent_profile
        }
        return render(request, 'dashboard.html', context)
        
        
    # Tampilkan Idle
    context = {
        **base_context,
        'view_type': 'IDLE_FRAME'
    }
    return render(request, 'dashboard.html', context)

# Menampilkan available users
@login_required
def get_available_users_ajax(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = request.user
    try:
        user_profile = Profile.objects.get(user=user)
        target_lokasi = user_profile.lokasi
        target_rank = user_profile.rank
    except Profile.DoesNotExist:
        return JsonResponse({'error': 'User profile not found'}, status=404)

    ids_sent_to = MatchRequest.objects.filter(sender=user, status='PENDING').values_list('receiver_id', flat=True)
    ids_received_from = MatchRequest.objects.filter(receiver=user, status='PENDING').values_list('sender_id', flat=True)
    excluded_ids = list(set(list(ids_sent_to) + list(ids_received_from) + [user.id]))

    potential_profiles = (
        Profile.objects.select_related('user')
        .filter(lokasi=target_lokasi)
        .exclude(user__is_superuser=True)
        .exclude(role=Profile.Role.ADMIN)
        .exclude(user_id__in=excluded_ids)
        .order_by('user__username')
    )

    available_users = [
        {
            'user_id': p.user.id,
            'username': p.user.username,
            'rank': p.rank,
            'lokasi': p.lokasi,
            'avatar': p.avatar,
            'kemenangan': p.jumlah_kemenangan,
            'instagram': p.instagram,
        }
        for p in potential_profiles
        if p.rank == target_rank
    ]

    return JsonResponse({'users': available_users})

# Menampilkan users yang memberi request
@login_required
def get_incoming_requests_ajax(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    user = request.user
    
    # Ambil request yang masuk, status PENDING, dan preload data pengirim
    incoming_requests_qs = MatchRequest.objects.filter(
        receiver=user, 
        status='PENDING'
    ).select_related('sender__profile').order_by('-timestamp')
    
    requests_data = []
    for req in incoming_requests_qs:
        # Cek apakah sender memiliki profile
        if hasattr(req.sender, 'profile'):
            sender_profile = req.sender.profile
            sender_rank = sender_profile.rank
            sender_lokasi = sender_profile.lokasi
            sender_avatar = sender_profile.avatar
            sender_instagram = sender_profile.instagram
        else:
            # Fallback
            sender_rank = "N/A"
            sender_lokasi = "N/A"
            sender_avatar = "N/A"
            sender_instagram = "N/A"
            
        requests_data.append({
            'request_id': req.id,
            'sender_id': req.sender.id,
            'sender_username': req.sender.username,
            'sender_rank': sender_rank,
            'sender_lokasi': sender_lokasi,
            'sender_avatar': sender_avatar,
            'sender_instagram': sender_instagram,
            'timestamp': req.timestamp.strftime('%Y-%m-%d %H:%M'),
        })
    
    return JsonResponse({'requests': requests_data})

# Handle pengiriman MatchRequest via AJAX
@csrf_exempt
@login_required
@require_POST
def create_match_request(request):
    user = request.user
    
    try:
        data = json.loads(request.body)
        receiver_id = data.get('receiver_id')
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON data.'}, status=400)

    if not receiver_id:
        return JsonResponse({'success': False, 'error': 'Receiver ID is required.'}, status=400)

    if str(user.id) == str(receiver_id):
        return JsonResponse({'success': False, 'error': 'Cannot send request to yourself.'}, status=400)
        
    try:
        receiver = User.objects.get(id=receiver_id)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Target user not found.'}, status=404)

    existing_request = MatchRequest.objects.filter(
        sender=user, 
        receiver=receiver, 
        status='PENDING'
    ).exists()

    if existing_request:
        return JsonResponse({'success': False, 'error': 'You already have a pending request to this user.'}, status=409)

    # Buat request baru
    MatchRequest.objects.create(
        sender=user,
        receiver=receiver,
        status='PENDING' 
    )
    
    # Beri respons sukses
    return JsonResponse({
        'success': True, 
        'message': f'',
    }, status=201)

# Handle accept dan reject
@csrf_exempt
@login_required
@require_POST
def handle_match_request(request):
    user = request.user

    try:
        data = json.loads(request.body)
        request_id = data.get('request_id')
        action = data.get('action')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data.'}, status=400)
    
    if not request_id or action not in ['ACCEPT', 'REJECT']:
        return JsonResponse({'success': False, 'error': 'Invalid parameters.'}, status=400)

    try:
        # Ambil request yang akan diproses
        match_request = MatchRequest.objects.get(id=request_id, receiver=user, status='PENDING')
    except MatchRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Pending request not found or already processed.'}, status=404)

    # Reject
    if action == 'REJECT':
        match_request.status = 'REJECTED'
        match_request.save()
        return JsonResponse({
            'success': True, 
            'message': f''
        })

    # Accept
    elif action == 'ACCEPT':
        sender = match_request.sender
        
        # Gunakan transaction untuk memastikan semua query sukses atau gagal bersamaan
        try:
            with transaction.atomic():
                # Update MatchRequest yang diterima
                match_request.status = 'ACCEPTED'
                match_request.save()
                
                # Buat MatchSession baru
                # Player 1 adalah sender, Player 2 adalah receiver
                MatchSession.objects.create(
                    player1=sender,
                    player2=user,
                    request=match_request,
                    result='PENDING' 
                )
                
                # Batalkan semua MatchRequest lain yang melibatkan sender
                MatchRequest.objects.filter(
                    sender=sender, 
                    status='PENDING'
                ).exclude(id=match_request.id).update(status='AUTO_CANCELLED')

                # Batalkan semua MatchRequest lain yang melibatkan receiver
                MatchRequest.objects.filter(
                    sender=user, 
                    status='PENDING'
                ).update(status='AUTO_CANCELLED')
                
                # Batalkan semua request PENDING lain yang diterima sender dari user lain
                MatchRequest.objects.filter(
                    receiver=sender, 
                    status='PENDING'
                ).update(status='AUTO_CANCELLED')
                
            return JsonResponse({
                'success': True, 
                'message': f'',
                'redirect': '/matchmaking/dashboard/'
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Failed to start match: {str(e)}'}, status=500)

# Handle Win/Lose/Cancel  
@csrf_exempt      
@login_required
@require_POST
def finish_match_session(request):
    user = request.user 
    
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        action = data.get('action') 
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data.'}, status=400)
    
    if not session_id or action not in ['WIN', 'LOSE', 'CANCEL']:
        return JsonResponse({'success': False, 'error': 'Invalid parameters.'}, status=400)

    try:
        session = MatchSession.objects.get(
            Q(player1=user) | Q(player2=user), 
            id=session_id, 
            result='PENDING'
        )
    except MatchSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Active session not found or already finished.'}, status=404)

    is_player1 = (session.player1 == user)

    try:
        with transaction.atomic():
            
            if action == 'WIN':
                session.result = 'P1_WIN' if is_player1 else 'P2_WIN'
                
                winner = session.player1 if is_player1 else session.player2
                
                Profile.objects.filter(user=winner).update(jumlah_kemenangan=F('jumlah_kemenangan') + 1)
                
                winner_profile = Profile.objects.get(user=winner)
                
                if winner == user:
                    request.user.profile.refresh_from_db()
                
                message = f''
                
            elif action == 'LOSE':
                session.result = 'P2_WIN' if is_player1 else 'P1_WIN'
                message = ''
                
            elif action == 'CANCEL':
                session.result = 'CANCELLED'
                message = ''
            
            # Simpan update sesi
            session.save(update_fields=['result'])

            return JsonResponse({
                'success': True, 
                'message': message,
                'redirect': '/matchmaking/dashboard/'
            })

    except Profile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Profile missing for one of the players.'}, status=500)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Failed to finalize match: {str(e)}'}, status=500)
    
@login_required
def get_active_session(request):
    user = request.user

    session = MatchSession.objects.filter(
        Q(player1=user) | Q(player2=user),
        result='PENDING'
    ).select_related('player1', 'player2').first()

    if not session:
        return JsonResponse({"has_session": False})

    return JsonResponse({
        "has_session": True,
        "session_id": session.id,
        "player1": {
            "id": session.player1.id,
            "username": session.player1.username,
        },
        "player2": {
            "id": session.player2.id,
            "username": session.player2.username,
        },
        "you_are_player1": session.player1 == user
    })

def get_opponent_profile(request, user_id):
    try:
        user = User.objects.get(id=user_id)
        profile = user.profile

        return JsonResponse({
            "user_id": user.id,
            "username": user.username,
            "instagram": profile.instagram or "",
            "avatar": profile.avatar,
            "lokasi": profile.lokasi,
            "rank": profile.rank,
            "kemenangan": profile.jumlah_kemenangan,
        })
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)