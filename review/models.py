from django.db import models
from main.models import Lapangan

"""
Mending ini reviewnya bikin ada tombol tambah review -> kasih form yang minta nama court +
semua lainnya yg ada di figma -> tampilin semua komentar yang ud dibuat di review_list.html
"""
class Review(models.Model):
    lapangan = models.ForeignKey(Lapangan, on_delete=models.CASCADE, null=True, blank=True)
    rating = models.PositiveSmallIntegerField(default=0)
    komentar = models.TextField()

    def __str__(self):
        return f"Review for {self.lapangan.nama if self.lapangan else 'Unknown'} - {self.rating}"