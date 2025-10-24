from django.contrib import admin
from .models import Community, Post, Reply

class ReadOnlyAdmin(admin.ModelAdmin):
    list_display = ("id",)  # sesuaikan per model
    search_fields = ()
    list_filter = ()
    readonly_fields = ()     # kalau mau tampilkan field di halaman detail tapi non-edit

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # kalau mau benar-benar read-only, kembalikan False
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # hilangkan aksi mass delete
    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)
        return actions

@admin.register(Community)
class CommunityAdmin(ReadOnlyAdmin):
    list_display = ("id", "name", "description")

@admin.register(Post)
class PostAdmin(ReadOnlyAdmin):
    list_display = ("id", "community", "author", "created_at")
    search_fields = ("content", "author__username", "community__name")

@admin.register(Reply)
class ReplyAdmin(ReadOnlyAdmin):
    list_display = ("id", "post", "author", "created_at")
    search_fields = ("content", "author__username", "post__community__name")
