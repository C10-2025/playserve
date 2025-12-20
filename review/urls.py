from django.urls import path
from review.views import add_review, review_list, view_comments, delete_review, show_json, proxy_image, add_review_flutter, delete_review_flutter

app_name = 'review'

urlpatterns = [
    path("add-review/", add_review, name='add_review'),
    path("add-review-flutter/", add_review_flutter, name='add_review_flutter'),
    path("", review_list, name='review_list'),
    path("field/<int:field_id>/comments/", view_comments, name='view_comments'),
    path("delete-review/<int:review_id>/", delete_review, name='delete-review'),
    path("delete-review-flutter/", delete_review_flutter, name="delete_review_flutter"),
    path('json/', show_json, name="show_json"),
    path('proxy-image/', proxy_image, name='proxy_image'),
]
