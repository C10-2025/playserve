# Generated migration: replace nama_lapangan with FK to main.Lapangan
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('review', '0001_initial'),
        ('main', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='review',
            name='nama_lapangan',
        ),
        migrations.AddField(
            model_name='review',
            name='lapangan',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, to='main.lapangan'),
        ),
    ]