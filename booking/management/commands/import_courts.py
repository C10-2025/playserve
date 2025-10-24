from django.core.management.base import BaseCommand
from booking.models import PlayingField
import csv
from datetime import datetime

class Command(BaseCommand):
    help = 'Import tennis courts from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            created_count = 0

            for row in reader:
                try:
                    # Clean and parse data
                    name = row.get('Park Name', '').strip()
                    address = row.get('ADDRESS', '').strip()
                    city = row.get('City', '').strip()

                    # Skip if essential data missing
                    if not name or not city:
                        continue

                    try:
                        latitude = float(row.get('LATITUDE', 0))
                        longitude = float(row.get('LONGITUDE', 0))
                    except (ValueError, TypeError):
                        latitude = None
                        longitude = None

                    try:
                        num_courts = int(row.get('# of Courts', 1))
                    except (ValueError, TypeError):
                        num_courts = 1

                    try:
                        price = float(row.get('price_per_hour', 90000))
                    except (ValueError, TypeError):
                        price = 90000

                    has_lights = row.get('Lights', 'No').strip().lower() == 'yes'
                    has_backboard = row.get('Backboard', 'No').strip().lower() == 'yes'

                    # Get image URL
                    image_url = row.get('image_url', '').strip()

                    # Create or update field
                    field, created = PlayingField.objects.update_or_create(
                        name=name,
                        city=city,
                        defaults={
                            'address': address,
                            'latitude': latitude,
                            'longitude': longitude,
                            'number_of_courts': num_courts,
                            'has_lights': has_lights,
                            'has_backboard': has_backboard,
                            'price_per_hour': price,
                            'image_url': image_url,
                            'created_by': None,
                        }
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(self.style.SUCCESS(f'Created: {name}'))
                    else:
                        self.stdout.write(f'Updated: {name}')

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error importing {name}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully imported {created_count} courts'))