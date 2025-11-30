from django.db import migrations


def create_stub_lapangans(apps, schema_editor):
    Lapangan = apps.get_model('main', 'Lapangan')
    # create a few sample lapangans if none exist
    if Lapangan.objects.exists():
        return

    Lapangan.objects.bulk_create([
        Lapangan(nama='Green Court Senayan', thumbnail='https://jurnaldepok.id/wp-content/uploads/2024/05/unnamed-file-12.jpg', lokasi='Jakarta', harga=150000),
        Lapangan(nama='Kota Futsal Bogor', thumbnail='https://via.placeholder.com/150', lokasi='Bogor', harga=90000),
        Lapangan(nama='Depok Arena', thumbnail='https://via.placeholder.com/150', lokasi='Depok', harga=80000),
        Lapangan(nama='Bekasi Sports Park', thumbnail='https://via.placeholder.com/150', lokasi='Bekasi', harga=100000),
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_stub_lapangans),
    ]