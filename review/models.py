from django.db import models

"""
Mending ini reviewnya bikin ada tombol tambah review -> kasih form yang minta nama court +
semua lainnya yg ada di figma -> tampilin semua komentar yang ud dibuat di review_list.html
"""
class Review(models.Model):
    nama_lapangan = models.CharField(max_length=255)
    rating = models.PositiveSmallIntegerField(default=0)
    komentar = models.TextField()