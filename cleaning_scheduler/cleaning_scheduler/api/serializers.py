from rest_framework import serializers
from icalendar import Calendar
from datetime import datetime, time

from django.db import transaction

from cleaning_scheduler.cleaning_scheduler.models import Apartment, Booking, CleaningSchedule
from ..utils import validate_booking_dates


class ApartmentSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Apartment
        fields = ['id', 'owner', 'name', 'location', 'size']
    
    def validate_name(self, value):
        user = self.context['request'].user
        if Apartment.objects.filter(name=value, owner=user).exists():
            raise serializers.ValidationError("You already have an apartment with this name.")
        return value

class BookingResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['check_in_date', 'check_out_date', 'guest_name', 'apartment']

class BookingSerializer(serializers.Serializer):
    ics_file = serializers.FileField(write_only=True)

    class Meta:
        fields = ['ics_file']

    def validate_ics_file(self, value):
        if not value.name.endswith('.ics'):
            raise serializers.ValidationError("Invalid file type. Only .ics files are supported.")
        return value

    def create(self, validated_data):
        ics_file = validated_data['ics_file']
        cal = Calendar.from_ical(ics_file.read())
        apartment_name = cal.get('prodid')
        try:
            apartment = Apartment.objects.get(name=apartment_name, owner=self.context['request'].user)
        except Apartment.DoesNotExist:
            raise serializers.ValidationError(f'Apartment with name {apartment_name} does not exist')

        new_bookings = []
        with transaction.atomic():
            for component in cal.walk():
                if component.name == "VEVENT":
                    dtstart = component.get('dtstart')
                    dtend = component.get('dtend')
                    summary = component.get('summary')
                    if dtstart is None or dtend is None:
                        raise serializers.ValidationError('Missing or invalid DTSTART or DTEND in one of the events in the calendar file')

                    if not summary:
                        raise serializers.ValidationError('Missing or invalid SUMMARY in one of the events in the calendar file')

                    check_in_date = datetime.combine(dtstart.dt, time(15, 0))
                    check_out_date = datetime.combine(dtend.dt, time(11, 0))

                    error = validate_booking_dates(apartment, check_in_date, check_out_date)
                    if error:
                        raise serializers.ValidationError(error)

                    new_booking = Booking.objects.create(
                        check_in_date=check_in_date, 
                        check_out_date=check_out_date, 
                        guest_name=summary, 
                        apartment=apartment
                    )
                    new_bookings.append(new_booking)
        return new_bookings

class CleaningScheduleSerializer(serializers.ModelSerializer):
    apartment = serializers.ReadOnlyField(source='booking.apartment.id')
    
    class Meta:
        model = CleaningSchedule
        fields = ['id', 'apartment', 'cleaning_date']
