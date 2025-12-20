from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from .models import Community, Post, Reply
from profil.models import Profile
from django.db.models import Q
from django.urls import reverse 
from profil.models import Profile
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Community, Post, Reply
from django.views.decorators.csrf import csrf_exempt
import json


def main_view(request):
    context = {}
    if request.user.is_authenticated:
        try:
            context['profile'] = request.user.profile
        except Profile.DoesNotExist:
            context['profile'] = None
            
    return render(request, 'main.html', context)

def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
def get_user(request):
    profile = getattr(request.user, "profile", None)

    data = {
        "status": True,
        "username": request.user.username,
        "rank": getattr(profile, "rank", None),
        "avatar": getattr(profile, "avatar", None),
        "instagram": getattr(profile, "instagram", None),
        "lokasi": getattr(profile, "lokasi", None),
        "is_superuser": request.user.is_superuser,
        "is_staff": request.user.is_staff,
        "is_admin": request.user.is_superuser or request.user.is_staff,
    }

    return JsonResponse(data)

@login_required
def discover_communities(request):
    query = request.GET.get('q', '')

    if query:
        communities = Community.objects.filter(name__icontains=query)
    else:
        communities = Community.objects.all()

    joined_community_ids = request.user.joined_communities.values_list('id', flat=True)

    context = {
        'communities': communities,
        'joined_community_ids': joined_community_ids,
        'search_query': query,
    }

    if request.user.is_authenticated:
        try:
            context['profile'] = request.user.profile
        except Profile.DoesNotExist:
            context['profile'] = None
    return render(request, 'discover_communities.html', context)

from django.views.decorators.http import require_GET
from django.http import JsonResponse

@require_GET
def discover_communities_json(request):
    query = request.GET.get('q', '').strip()

    if query:
        communities = Community.objects.filter(name__icontains=query)
    else:
        communities = Community.objects.all()

    if request.user.is_authenticated:
        joined_ids = set(
            request.user.joined_communities.values_list('id', flat=True)
        )
    else:
        joined_ids = set()

    data = []
    for c in communities:
        is_joined = c.id in joined_ids
        is_creator = request.user.is_authenticated and c.creator_id == request.user.id

        data.append({
            "id": c.id,
            "name": c.name,
            "description": c.description or "",
            "members_count": c.members.count(),
            "is_joined": is_joined,
            "is_creator": is_creator,
            "creator_username": c.creator.username if c.creator else "",
            "can_open": is_joined or is_creator,
        })

    return JsonResponse(data, safe=False, status=200)



@login_required
def my_communities(request):
    is_admin = request.user.is_staff or request.user.is_superuser

    if is_admin:
        communities = Community.objects.filter(creator=request.user).order_by('-created_at')
        mode = 'created'         
        subtitle = 'Created by Me'
    else:
        communities = request.user.joined_communities.all().order_by('-created_at')
        mode = 'joined'
        subtitle = 'Joined'

    context = {
        'communities': communities,
        'is_admin': is_admin,
        'mode': mode,            
        'subtitle': subtitle,
        'profile': getattr(request.user, 'profile', None) if request.user.is_authenticated else None,
    }
    return render(request, 'my_communities.html', context)

@csrf_exempt
@login_required
def join_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
    if request.user in community.members.all():
        return JsonResponse({
            'status': 'already_joined',
            'community_name': community.name,
            'members_count': community.members.count(),
        })

    community.members.add(request.user)
    return JsonResponse({
        'status': 'joined',
        'community_name': community.name,
        'members_count': community.members.count(),
    })

@login_required
@user_passes_test(is_admin)
@csrf_exempt  
def create_community(request):
    is_json = request.headers.get("Content-Type", "").startswith("application/json")
    is_ajax = is_json or request.headers.get("x-requested-with") == "XMLHttpRequest"

    if request.method != 'POST':
        if is_ajax:
            return JsonResponse(
                {"status": "error", "message": "Method not allowed."},
                status=405
            )
        
        return render(request, 'create_community.html', {
            'profile': getattr(request.user, 'profile', None)
        })

    if is_json:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {}
        name = (payload.get('name') or '').strip()
        description = (payload.get('description') or '').strip()
    else:
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()

    if not name:
        msg = 'Name is required.'
        if is_ajax:
            return JsonResponse(
                {
                    'status': 'error',
                    'message': msg,
                    'code': 'name_required',
                },
                status=400
            )
        messages.error(request, msg)
        return redirect('discover_communities')

    existing = Community.objects.filter(name__iexact=name).first()
    if existing:
        msg = f'Community with name "{name}" already exists. Please use a different name.'

        if is_json:
            return JsonResponse(
                {
                    'status': 'error',
                    'message': 'Community name already exists. Please use a different name.',
                    'code': 'duplicate_name',
                },
                status=200
            )

        if is_ajax:
            return JsonResponse(
                {
                    'status': 'error',
                    'toast_type': 'error',
                    'message': msg,
                    'code': 'duplicate_name',
                },
                status=409
            )

        messages.error(request, msg)
        return redirect('discover_communities')

    try:
        community = Community.objects.create(
            name=name,
            description=description,
            creator=request.user
        )
        msg = f'Community "{community.name}" created successfully.'

        if is_ajax:
            return JsonResponse(
                {
                    'status': 'success',
                    'toast_type': 'success',
                    'message': msg,
                    'code': 'created',
                    'redirect_url': reverse('discover_communities'),
                },
                status=200
            )

        messages.success(request, msg)
        return redirect('discover_communities')

    except Exception:
        generic = 'Something went wrong. Please try again.'
        if is_ajax:
            return JsonResponse(
                {
                    'status': 'error',
                    'toast_type': 'error',
                    'message': generic,
                },
                status=500
            )
        messages.error(request, generic)
        return redirect('discover_communities')



@login_required
@user_passes_test(is_admin)
@csrf_exempt
def update_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if request.user != community.creator:
        msg = "You can only edit your own communities."
        is_json = request.headers.get("Content-Type", "").startswith("application/json")
        is_ajax = is_json or request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if is_ajax:
            return JsonResponse(
                {'status': 'error', 'message': msg},
                status=403
            )
        messages.error(request, msg)
        return redirect("discover_communities")

    is_json = request.headers.get("Content-Type", "").startswith("application/json")
    is_ajax = is_json or request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if request.method != "POST":
        if is_ajax:
            return JsonResponse(
                {"status": "error", "message": "Method not allowed."},
                status=405
            )
        return redirect("discover_communities")

    # --- ambil data ---
    if is_json:
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {}
        name = (payload.get("name") or "").strip()
        description = (payload.get("description") or "").strip()
    else:
        name = request.POST.get("name", "").strip()
        description = (request.POST.get("description") or "").strip()

    if not name:
        msg = "Name is required."
        if is_ajax:
            return JsonResponse(
                {"status": "error", "message": msg, "code": "name_required"},
                status=400
            )
        messages.error(request, msg)
        return redirect("discover_communities")

    duplicate = Community.objects.filter(name__iexact=name).exclude(id=community.id).first()
    if duplicate:
        msg = f'Community with name "{name}" already exists. Please use a different name.'
        if is_json:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Community name already exists. Please use a different name.",
                    "code": "duplicate_name",
                },
                status=200
            )
        if is_ajax:
            return JsonResponse(
                {
                    "status": "error",
                    "message": msg,
                    "code": "duplicate_name",
                },
                status=409
            )
        messages.error(request, msg)
        return redirect("discover_communities")

    community.name = name
    community.description = description  
    community.save()

    success_msg = f"Community '{community.name}' updated successfully."

    if is_ajax:
        return JsonResponse(
            {
                "status": "success",
                "message": success_msg,
                "code": "updated",
            },
            status=200
        )

    messages.success(request, success_msg)
    return redirect("discover_communities")




@login_required
@user_passes_test(is_admin)
@csrf_exempt
def delete_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if request.user != community.creator:
        msg = "You can only delete communities you created."
        is_json = request.headers.get("Content-Type", "").startswith("application/json")
        is_ajax = is_json or request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if is_ajax:
            return JsonResponse({"status": "error", "message": msg}, status=403)

        messages.error(request, msg)
        return redirect("discover_communities")

    if request.method != "POST":
        is_json = request.headers.get("Content-Type", "").startswith("application/json")
        is_ajax = is_json or request.headers.get('x-requested-with') == 'XMLHttpRequest'

        if is_ajax:
            return JsonResponse(
                {"status": "error", "message": "Method not allowed."},
                status=405
            )
        return redirect("discover_communities")

    deleted_name = community.name
    community.delete()
    msg = f'Community "{deleted_name}" deleted successfully.'

    is_json = request.headers.get("Content-Type", "").startswith("application/json")
    is_ajax = is_json or request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if is_ajax:
        # Flutter OR AJAX fetch response
        return JsonResponse(
            {"status": "success", "message": msg},
            status=200
        )

    # Browser HTML fallback (Redirect + Django Messages)
    messages.success(request, msg)
    return redirect("discover_communities")



@login_required
def community_detail(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if request.user == community.creator and request.user not in community.members.all():
        community.members.add(request.user)


    if request.user not in community.members.all():
        messages.error(request, "You must join this community to see its posts.")
        return redirect('discover_communities')

    posts = community.posts.all().prefetch_related('replies', 'replies__author')

    context = {
        'community': community,
        'posts': posts,
    }

    if request.user.is_authenticated:
        try:
            context['profile'] = request.user.profile
        except Profile.DoesNotExist:
            context['profile'] = None
    return render(request, 'community_detail.html', context)

@login_required
@require_GET
def community_detail_json(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if request.user == community.creator and request.user not in community.members.all():
        community.members.add(request.user)

    is_admin = request.user.is_superuser or request.user.is_staff
    is_member = community.members.filter(pk=request.user.pk).exists()
    is_creator = (request.user == community.creator)

    if not (is_member or is_creator or is_admin):
        return JsonResponse(
            {"error": "You must join this community to see its posts."},
            status=403
        )

    posts_qs = community.posts.all().prefetch_related(
        'author', 'replies', 'replies__author'
    ).order_by('-created_at')

    posts_data = []
    for p in posts_qs:
        posts_data.append({
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "author": p.author.username,
            "created_at": p.created_at.isoformat(),
            "replies": [
                {
                    "id": r.id,
                    "content": r.content,
                    "author": r.author.username,
                    "created_at": r.created_at.isoformat(),
                }
                for r in p.replies.all().order_by('created_at')
            ],
        })

    data = {
        "id": community.id,
        "name": community.name,
        "description": community.description or "",
        "members_count": community.members.count(),
        "is_creator": is_creator,
        "is_admin": is_admin,
        "is_joined": is_member,
        "posts": posts_data,
    }
    return JsonResponse(data, status=200)

@csrf_exempt
@login_required
@require_POST
def delete_post_api(request, post_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse(
            {"error": "Forbidden"}, status=403
        )

    post = get_object_or_404(Post, pk=post_id)
    post.delete()
    return JsonResponse(
        {
            "status": "success",
            "message": "Post deleted."
        }
    )

@csrf_exempt
@login_required
@require_POST
def delete_reply_api(request, reply_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse(
            {"error": "Forbidden"}, status=403
        )

    reply = get_object_or_404(Reply, pk=reply_id)
    reply.delete()
    return JsonResponse(
        {
            "status": "success",
            "message": "Reply deleted."
        }
    )

@csrf_exempt
@login_required
@require_POST
def create_post_json(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    if request.user not in community.members.all():
        return JsonResponse(
            {"error": "You must join this community before posting."},
            status=403
        )
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = request.POST

    title = (payload.get('title') or '').strip()
    content = (payload.get('content') or '').strip()

    if not title or not content:
        return JsonResponse(
            {"error": "Both title and content are required."},
            status=400
        )

    post = Post.objects.create(
        community=community,
        author=request.user,
        title=title,
        content=content,
    )

    return JsonResponse({
        "status": "success",
        "message": "Post created.",
        "post": {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "author": post.author.username,
            "created_at": post.created_at.isoformat(),
            "replies": [],
        }
    }, status=201)
@csrf_exempt
@login_required
@require_POST
def create_reply_json(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    community = post.community

    if request.user not in community.members.all():
        return JsonResponse(
            {"error": "You must join this community before replying."},
            status=403
        )

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = request.POST

    content = (payload.get('content') or '').strip()
    if not content:
        return JsonResponse(
            {"error": "Content is required."},
            status=400
        )

    reply = Reply.objects.create(
        post=post,
        author=request.user,
        content=content,
    )

    return JsonResponse({
        "status": "success",
        "message": "Reply created.",
        "reply": {
            "id": reply.id,
            "content": reply.content,
            "author": reply.author.username,
            "created_at": reply.created_at.isoformat(),
        }
    }, status=201)


@login_required
def create_post(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if request.user not in community.members.all():
        messages.warning(request, "You must join this community before posting.")
        return redirect('discover_communities')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()

        if not title or not content:
            messages.error(request, "Both title and content are required.")
        else:
            Post.objects.create(
                community=community,
                author=request.user,
                title=title,
                content=content
            )
            messages.success(request, "Your discussion has been posted!")

        return redirect('community_detail', community_id=community_id)

    return redirect('community_detail', community_id=community_id)


@login_required
def create_reply(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    community = post.community

    if request.user not in community.members.all():
        return redirect('discover_communities')

    if request.method == 'POST':
        content = request.POST.get('content')
        if content and content.strip():
            Reply.objects.create(
                post=post,
                author=request.user,
                content=content
            )

    return redirect('community_detail', community_id=community.id)

@login_required
@user_passes_test(is_admin)
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    community_id = post.community_id
    if request.method == 'POST':
        post.delete()
        messages.success(request, "Post has been removed.")
    return redirect('community_detail', community_id=community_id)

@login_required
@user_passes_test(is_admin)
def delete_reply(request, reply_id):
    reply = get_object_or_404(Reply, id=reply_id)
    community_id = reply.post.community_id
    if request.method == 'POST':
        reply.delete()
        messages.success(request, "Reply has been removed.")
    return redirect('community_detail', community_id=community_id)
