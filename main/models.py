from django.db import models

# Create your models here.
class Lapangan(models.Model):
    nama = models.CharField(max_length=200, default="Player")
    KOTA_CHOICES = [
        ('Jakarta', 'Jakarta'),
        ('Bogor', 'Bogor'),
        ('Depok', 'Depok'),
        ('Tangerang', 'Tangerang'),
        ('Bekasi', 'Bekasi'),
    ]
    lokasi = models.CharField(max_length=50, choices=KOTA_CHOICES)
    harga = models.PositiveIntegerField(default=0)
