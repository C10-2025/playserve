from django.forms import ModelForm
from review.models import Review


class ReviewForm(ModelForm):
    class Meta:
        model = Review
        fields = ['field', 'rating', 'komentar']