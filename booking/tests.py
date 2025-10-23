from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from .models import PlayingField, Booking

class BookingModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.field = PlayingField.objects.create(
            name='Test Court',
            city='Jakarta',
            court_surface='HARD',
            price_per_hour=100000,
            created_by=self.user
        )

    def test_field_creation(self):
        self.assertEqual(self.field.name, 'Test Court')
        self.assertEqual(self.field.city, 'Jakarta')
        self.assertEqual(self.field.price_per_hour, 100000)

    def test_slot_creation(self):
        # Test that slots can be created (though we don't have TimeSlot model yet)
        # This would test the availability logic
        pass

    def test_booking_creation(self):
        from datetime import date, time
        booking = Booking.objects.create(
            user=self.user,
            field=self.field,
            booking_date=date(2024, 1, 1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            duration_hours=1.0,
            booker_name='John Doe',
            booker_phone='+62123456789'
        )
        self.assertEqual(booking.total_price, 100000)
        self.assertEqual(str(booking), 'John Doe - Test Court on 2024-01-01')

    def test_booking_availability_check(self):
        # Test booking conflict detection
        from datetime import date, time
        booking1 = Booking.objects.create(
            user=self.user,
            field=self.field,
            booking_date=date(2024, 1, 1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            duration_hours=1.0,
            booker_name='John Doe',
            booker_phone='+62123456789'
        )

        # Try to create overlapping booking
        booking2 = Booking(
            user=self.user,
            field=self.field,
            booking_date=date(2024, 1, 1),
            start_time=time(10, 30),
            end_time=time(11, 30),
            duration_hours=1.0,
            booker_name='Jane Doe',
            booker_phone='+62123456789'
        )

        is_available, message = booking2.check_availability()
        self.assertFalse(is_available)
        self.assertIn('conflicts', message.lower())

    def test_cancellation_policy(self):
        # Test cancellation rules
        from datetime import time
        future_booking = Booking.objects.create(
            user=self.user,
            field=self.field,
            booking_date=timezone.now().date() + timezone.timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(11, 0),
            duration_hours=1.0,
            booker_name='John Doe',
            booker_phone='+62123456789'
        )

        # Should be cancellable (more than 24 hours away)
        self.assertTrue(future_booking.can_cancel)

        # Past booking should not be cancellable
        past_booking = Booking.objects.create(
            user=self.user,
            field=self.field,
            booking_date=timezone.now().date() - timezone.timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            duration_hours=1.0,
            booker_name='John Doe',
            booker_phone='+62123456789'
        )

        self.assertFalse(past_booking.can_cancel)
