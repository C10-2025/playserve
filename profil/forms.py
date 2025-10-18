from django.forms import ModelForm, CharField, ChoiceField, PasswordInput, ValidationError
from django.contrib.auth.models import User
from .models import Profile

class RegistrationFormStep1(ModelForm):
    password = CharField(label='Password', widget=PasswordInput)
    password2 = CharField(label='Confirm Password', widget=PasswordInput)
    
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

class ProfileUpdateForm(ModelForm):
    class Meta:
        model = Profile
        fields = ['lokasi', 'instagram', 'avatar']