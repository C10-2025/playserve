from django.forms import ModelForm, CharField, ChoiceField, PasswordInput, ValidationError
from django.contrib.auth.models import User
from .models import Profile
import re
from django.core.exceptions import ValidationError

class RegistrationFormStep1(ModelForm):
    password = CharField(label='Password', widget=PasswordInput(attrs={'placeholder': 'Min. 8 characters'}), min_length=8, error_messages={'min_length': 'Password must be at least 8 characters long.'})
    password2 = CharField(label='Confirm Password', widget=PasswordInput())
    
    class Meta:
        model = User
        fields = ['username']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean_password2(self):
        cd = self.cleaned_data
        if cd.get('password') and cd.get('password2') and cd.get('password') != cd.get('password2'):
            raise ValidationError("Passwords do not match.")
        return cd.get('password2')
    
class RegistrationFormStep2(ModelForm):
    class Meta:
        model = Profile
        fields = ['lokasi', 'instagram', 'avatar']

    def clean_instagram(self):
        instagram = self.cleaned_data.get('instagram')
        if instagram:
            if instagram.startswith('@'):
                raise ValidationError("No need for @ at the beginning.")
            if not re.match(r'^[a-zA-Z0-9._]+$', instagram):
                raise ValidationError("Instagram username can only contain letters, numbers, periods, and underscores.")
        return instagram

class ProfileUpdateForm(ModelForm):
    new_password = CharField(required=False, widget=PasswordInput(attrs={'placeholder': 'New Password (min 8 chars)'}), min_length=8)
    confirm_password = CharField(required=False, widget=PasswordInput(attrs={'placeholder': 'Confirm New Password'}), min_length=8)

    class Meta:
        model = Profile
        fields = ['lokasi', 'instagram', 'avatar']

    def clean_instagram(self):
        instagram = self.cleaned_data.get('instagram')
        if instagram:
            if instagram.startswith('@'):
                raise ValidationError("No need for @ at the beginning.")
            if not re.match(r'^[a-zA-Z0-9._]+$', instagram):
                raise ValidationError("Instagram username can only contain letters, numbers, periods, and underscores.")
        return instagram

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        if new_password or confirm_password:
            if new_password != confirm_password:
                raise ValidationError("Passwords do not match.")
        return cleaned_data