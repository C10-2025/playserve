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
        ('image/avatar1.png', 'Avatar 1'),
        ('image/avatar2.png', 'Avatar 2'),
        ('image/avatar3.png', 'Avatar 3'),
        ('image/avatar4.png', 'Avatar 4'),
        ('image/avatar5.png', 'Avatar 5'),
    ]
    avatar = models.CharField(max_length=100, choices=AVATAR_CHOICES, default='image/avatar1.png')
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

    def __str__(self):
        return f'{self.user.username} Profile ({self.get_role_display()})'