from django.db import models
from main.models import Lapangan

class Review(models.Model):
    lapangan = models.ForeignKey(Lapangan, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(default=0)
    komentar = models.TextField()