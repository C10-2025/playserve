from django.urls import path
from review.views import add_review, review_list, view_comments, delete_review, review_list_search_bar, show_json

app_name = 'review'

urlpatterns = [
    path("add-review/", add_review, name='add_review'),
    path("", review_list, name='review_list'),
    path("field/<int:field_id>/comments/", view_comments, name='view_comments'),
    path("delete-review/<int:review_id>/", delete_review, name='delete-review'),
    path('search-review/', review_list_search_bar, name='review_list_search_bar'),
    path('json/', show_json, name="show_json")
]
