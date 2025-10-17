from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    class Role(models.TextChoices):
        PLAYER = 'PLAYER', 'Player'
        ADMIN = 'ADMIN', 'Admin'
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=Role.choices, default=Role.PLAYER)

    KOTA_CHOICES = [
        ('Jakarta', 'Jakarta'),
        ('Bogor', 'Bogor'),
        ('Depok', 'Depok'),
        ('Tangerang', 'Tangerang'),
        ('Bekasi', 'Bekasi'),
    ]
    lokasi = models.CharField(max_length=50, choices=KOTA_CHOICES)
    instagram = models.CharField(max_length=100, blank=True, null=True)

    AVATAR_CHOICES = [
        ('static/image/avatar1.png', 'Avatar 1'),
        ('static/image/avatar2.png', 'Avatar 2'),
        ('static/image/avatar3.png', 'Avatar 3'),
        ('static/image/avatar4.png', 'Avatar 4'),
        ('static/image/avatar5.png', 'Avatar 5'),
    ]
    avatar = models.CharField(max_length=100, choices=AVATAR_CHOICES, default='avatars/avatar1.png')
    jumlah_kemenangan = models.PositiveIntegerField(default=0)

    @property
    def rank(self):
        wins = self.jumlah_kemenangan
        if wins < 10:
            return "Bronze"
        elif wins < 25:
            return "Silver"
        elif wins < 50:
            return "Gold"
        elif wins < 100:
            return "Platinum"
        else:
            return "Diamond"

    def _str_(self):
        return f'{self.user.username} Profile ({self.get_role_display()})'