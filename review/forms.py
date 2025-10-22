from django.forms import ModelForm, CharField, ChoiceField, PasswordInput, ValidationError
from review.models import Review

class ReviewForm(ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'komentar'] 