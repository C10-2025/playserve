from django.contrib.auth.models import User
from django.db import models
from booking.models import PlayingField

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True) 
    field = models.ForeignKey(PlayingField, on_delete=models.CASCADE)
    rating = models.IntegerField()
    komentar = models.TextField()

    class Meta:
        unique_together = ('user', 'field')

    def __str__(self):
        return f"{self.user.username} - {self.field.name}"
