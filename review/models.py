import uuid
from django.db import models
from booking.models import PlayingField

class Review(models.Model):
    field = models.ForeignKey(PlayingField, on_delete=models.CASCADE, null=True, blank=True)
    rating = models.PositiveSmallIntegerField(default=0)
    komentar = models.TextField()

    def __str__(self):
        return f"Review for {self.field.nama if self.field else 'Unknown'} - {self.rating}"