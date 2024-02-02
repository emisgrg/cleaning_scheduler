# cleaning_scheduler/apartment/views.py
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.db.models import Q
from django.utils.dateparse import parse_date


from ..models import Apartment, Booking, CleaningSchedule
from .serializers import ApartmentSerializer, BookingSerializer, BookingResponseSerializer, CleaningScheduleSerializer
from ..utils import update_cleaning_schedule



class ApartmentListCreateView(generics.ListCreateAPIView):
    queryset = Apartment.objects.all()
    serializer_class = ApartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ApartmentDetailView(generics.RetrieveAPIView):
    queryset = Apartment.objects.all()
    serializer_class = ApartmentSerializer
    lookup_url_kwarg = 'id'
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)


class ApartmentUpdateView(generics.UpdateAPIView):
    queryset = Apartment.objects.all()
    serializer_class = ApartmentSerializer
    lookup_url_kwarg = 'id'
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)


class ApartmentDeleteView(generics.DestroyAPIView):
    queryset = Apartment.objects.all()
    serializer_class = ApartmentSerializer
    lookup_url_kwarg = 'id'
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)

class CalendarAPIView(generics.ListCreateAPIView):
    serializer_class = BookingResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = BookingSerializer(data=request.data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            new_bookings = serializer.save()
            if new_bookings:
                update_cleaning_schedule(request.user, new_bookings)
            new_bookings_serializer = BookingResponseSerializer(new_bookings, many=True)
            return Response(new_bookings_serializer.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        queryset = Booking.objects.filter(apartment__owner=self.request.user)
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)

        if start_date is not None and end_date is not None:
            start_date = parse_date(start_date)
            end_date = parse_date(end_date)
            queryset = queryset.filter(check_in_date__range=[start_date, end_date])

        return queryset

class CleaningScheduleAPIView(generics.ListAPIView):
    serializer_class = CleaningScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)

        if start_date is not None and end_date is not None:
            queryset = CleaningSchedule.objects.filter(
            Q(cleaning_date__gte=start_date) & Q(cleaning_date__lte=end_date),
            booking__apartment__owner=self.request.user
        )
        else:
            queryset = CleaningSchedule.objects.filter(booking__apartment__owner=self.request.user)

        return queryset
