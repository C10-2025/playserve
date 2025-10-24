import uuid
from django.db import models
from main.models import Lapangan

class Review(models.Model):
    lapangan = models.ForeignKey(Lapangan, on_delete=models.CASCADE, null=True, blank=True)
    rating = models.PositiveSmallIntegerField(default=0)
    komentar = models.TextField()

    def __str__(self):
        return f"Review for {self.lapangan.nama if self.lapangan else 'Unknown'} - {self.rating}"