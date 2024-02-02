from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, UpdateView, ListView, DeleteView, CreateView, View
from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import redirect
from django.db.models import Q, F, Exists, OuterRef
from django.db import transaction
from django.http import Http404
from django.core.exceptions import ValidationError



import calendar
import intervaltree
from icalendar import Calendar
from datetime import datetime, timedelta, time
from collections import defaultdict

from .forms import ApartmentUpdateForm, ApartmentCreationForm
from cleaning_scheduler.cleaning_scheduler.models import Apartment, Booking
from .utils import update_cleaning_schedule,validate_booking_dates


import logging

logger = logging.getLogger(__name__)

def root(request):
    if request.user.is_authenticated:
        return redirect('scheduler:calendar')
    else:
        return redirect('account_login')

class ApartmentDetailView(LoginRequiredMixin, DetailView):
    model = Apartment
    pk_url_kwarg = 'id'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.owner != self.request.user:
            raise Http404()
        return obj

apartment_detail_view = ApartmentDetailView.as_view()

class ApartmentUpdateView(LoginRequiredMixin, UpdateView):
    model = Apartment
    form_class = ApartmentUpdateForm
    pk_url_kwarg = 'id'
    template_name = 'cleaning_scheduler/apartment_detail.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.owner != self.request.user:
            raise Http404()
        return obj
    
    def get_success_url(self):
        logger.info(f"ApartmentUpdateView.get_success_url: {self.object.id}")
        return reverse_lazy('scheduler:apartments_detail', kwargs={'id': self.object.id})

apartment_update_view = ApartmentUpdateView.as_view()

class ApartmentListView(LoginRequiredMixin, ListView):
    model = Apartment
    context_object_name = 'apartments' 

    def get_queryset(self):
        # This line ensures that only apartments belonging to the logged-in user are returned
        logger.info(f"User: {self.request.user}")
        apartments=Apartment.objects.filter(owner=self.request.user)
        logger.info(f"apartments: {apartments}")
        return Apartment.objects.filter(owner=self.request.user)

apartment_list_view = ApartmentListView.as_view()

class ApartmentDeleteView(LoginRequiredMixin, DeleteView):
    model = Apartment
    pk_url_kwarg = 'id'
    success_url = reverse_lazy('scheduler:apartments_list')

    def get_object(self, queryset=None):
        """ Override the method to check object permissions. """
        logger.info(f"ApartmentDeleteView.get_object: {self.request.user}")
        obj = super().get_object(queryset)
        if obj.owner != self.request.user:
            raise Http404()
        return obj

apartment_delete_view = ApartmentDeleteView.as_view()

class ApartmentCreateView(LoginRequiredMixin, CreateView):
    model = Apartment
    form_class = ApartmentCreationForm
    template_name = 'cleaning_scheduler/apartment_create.html'

    def form_valid(self, form):
        form.instance.owner = self.request.user
        if Apartment.objects.filter(name=form.instance.name, owner=form.instance.owner).exists():
            form.add_error('name', ValidationError("You already have an apartment with this name."))
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        logger.info(f"ApartmentCreateView.get_success_url: {self.object.id}")
        return reverse_lazy('scheduler:apartments_list')

apartment_create_view = ApartmentCreateView.as_view()

class CalendarView(LoginRequiredMixin, View):
    template_name = 'cleaning_scheduler/calendar.html'
    def post(self, request, *args, **kwargs):
        if 'ics_file' not in request.FILES:
            messages.error(request, 'No file selected for upload')
            return redirect('scheduler:calendar')

        ics_file = request.FILES['ics_file']
        cal = Calendar.from_ical(ics_file.read())
        logger.info(f"cal: {cal}")
        apartment_name = cal.get('prodid')
        try:
            apartment = Apartment.objects.get(name=apartment_name, owner=request.user)
        except Apartment.DoesNotExist:
            messages.error(request, f'Apartment with name {apartment_name} does not exist')
            return redirect('scheduler:calendar')

        new_bookings = []
        with transaction.atomic():
            for component in cal.walk():
                if component.name == "VEVENT":
                    dtstart = component.get('dtstart')
                    dtend = component.get('dtend')
                    
                    if dtstart is None or dtend is None:
                        messages.error(request, 'Missing or invalid DTSTART or DTEND in one of the events in the calendar file')
                        return redirect('scheduler:calendar')
                    
                    check_in_date = datetime.combine(dtstart.dt, time(15, 0))
                    check_out_date = datetime.combine(dtend.dt, time(11, 0))


                    summary = component.get('summary')

                    if not summary:
                        messages.error(request, 'Missing or invalid SUMMARY in one of the events in the calendar file')
                        return redirect('scheduler:calendar')
                
                    logger.info(f"dtstart: {check_in_date}, dtend: {check_out_date}, summary: {summary}, apartment: {apartment_name}")

                    error = validate_booking_dates(apartment, check_in_date, check_out_date)
                    if error is not None:
                        messages.error(request, error)
                        return redirect('scheduler:calendar')
                    
                    # Create a new booking without updating the cleaning schedule yet
                    new_booking = Booking.objects.create(
                        check_in_date=check_in_date, 
                        check_out_date=check_out_date, 
                        guest_name=summary, 
                        apartment=apartment
                    )
                    new_bookings.append(new_booking)
        
        # Update the cleaning schedule after processing all bookings
        if new_bookings:
            update_cleaning_schedule(request.user, new_bookings)

        return redirect('scheduler:calendar')
               
    def get(self, request, *args, **kwargs):
        year = int(request.GET.get('year', datetime.now().year))
        month = int(request.GET.get('month', datetime.now().month))
        my_calendar = calendar.monthcalendar(year, month)
        previous_year, previous_month = (year, month - 1) if month > 1 else (year - 1, 12)
        next_year, next_month = (year, month + 1) if month < 12 else (year + 1, 1)


        # Fetch the reserved dates and cleaning dates from your database
        bookings = Booking.objects.filter(
            Q(check_in_date__year=year, check_in_date__month=month) |
            Q(check_out_date__year=year, check_out_date__month=month),
            apartment__owner=request.user
        ).select_related('cleaningschedule').annotate(
            cleaning_date=F('cleaningschedule__cleaning_date')
        ).values_list('apartment__name', 'check_in_date', 'check_out_date', 'cleaning_date')

        # Generate a dictionary where each key is a date and the value is a list of apartment names
        reserved_dates_dict = defaultdict(list)
        for apartment_name, start_date, end_date, cleaning_date in bookings:
            delta = end_date - start_date
            for i in range(delta.days + 1):
                day = start_date + timedelta(days=i)
                reserved_dates_dict[day.strftime('%Y-%m-%d')].append(apartment_name)

            # Add the cleaning date to the dictionary with the "*Cleaning Needed*" suffix
            if cleaning_date and cleaning_date.year == year and cleaning_date.month == month:
                reserved_dates_dict[cleaning_date.strftime('%Y-%m-%d')].append(f"{apartment_name} *Cleaning Needed*")

        # Generate a list of dictionaries for the calendar
        calendar_data = []
        for week in my_calendar:
            week_data = []
            for day in week:
                if day != 0:
                    date = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
                    week_data.append({
                        'day': day,
                        'apartments': reserved_dates_dict.get(date, [])
                    })
                else:
                    week_data.append({'day': 0, 'apartments': []})
            calendar_data.append(week_data)
        
        logger.info(f"calendar_data: {calendar_data}")
        
        context = {
            'calendar': calendar_data,
            'month': month,
            'year': year,
            'previous_month': previous_month,
            'previous_year': previous_year,
            'next_month': next_month,
            'next_year': next_year,
            'months': range(1, 13),
            'now_year': datetime.now().year,
            'now_month': datetime.now().month,
        }
        return render(request, self.template_name, context)

calendar_view = CalendarView.as_view()

class CleaningScheduleView(LoginRequiredMixin, View):
    template_name = 'cleaning_scheduler/cleaning_schedule.html'

    def get(self, request, *args, **kwargs):

        year = int(request.GET.get('year', datetime.now().year))
        month = int(request.GET.get('month', datetime.now().month))
        previous_year, previous_month = (year, month - 1) if month > 1 else (year - 1, 12)
        next_year, next_month = (year, month + 1) if month < 12 else (year + 1, 1)

        # Fetch the reserved dates and cleaning dates from your database
        bookings = Booking.objects.filter(
            Q(check_in_date__year=year, check_in_date__month=month) |
            Q(check_out_date__year=year, check_out_date__month=month),
            apartment__owner=request.user
        ).select_related('cleaningschedule').annotate(
            cleaning_date=F('cleaningschedule__cleaning_date')
        ).values_list('apartment__name', 'check_in_date', 'check_out_date', 'cleaning_date')

        # Fetch apartments of the logged-in user
        apartments = Apartment.objects.filter(owner=request.user)

        # Create a mapping from apartment names to indices
        apartment_indices = {apartment.name: i for i, apartment in enumerate(apartments)}

        # Initialize the schedule_dict with empty lists for each apartment
        schedule_dict = defaultdict(lambda: ['Empty'] * len(apartments))

        for apartment_name, start_date, end_date, cleaning_date in bookings:
            start_date = start_date.date()
            end_date = end_date.date()
            cleaning_date = cleaning_date.date() if cleaning_date else None
            delta = end_date - start_date
            for i in range(delta.days + 1):  # Include the last day in the range
                day = start_date + timedelta(days=i)
                if day == start_date:
                    # This is the first day of the booking
                    schedule_dict[day.strftime('%Y-%m-%d')][apartment_indices[apartment_name]] = 'Enter'
                elif day == end_date:
                    # This is the last day of the booking
                    if cleaning_date == end_date:
                        schedule_dict[day.strftime('%Y-%m-%d')][apartment_indices[apartment_name]] = 'Exit/Cleaning'
                    else:
                        schedule_dict[day.strftime('%Y-%m-%d')][apartment_indices[apartment_name]] = 'Exit'
                else:
                    # This is a day in between
                    schedule_dict[day.strftime('%Y-%m-%d')][apartment_indices[apartment_name]] = 'Occupied'

            # Check the cleaning date separately
            if cleaning_date and cleaning_date not in [start_date, end_date]:
                schedule_dict[cleaning_date.strftime('%Y-%m-%d')][apartment_indices[apartment_name]] = 'Cleaning Needed'

        logger.info(f"schedule_dict: {schedule_dict}")

        # Fetch apartments of the logged-in user
        context = {
            'apartments':apartments,
            'schedule': dict(sorted(schedule_dict.items())),
            'year': year,
            'month': month,
            'months': range(1, 13),
            'previous_month': previous_month,
            'previous_year': previous_year,
            'next_month': next_month,
            'next_year': next_year,
            'now_year': datetime.now().year,
            'now_month': datetime.now().month,
        }

        return render(request, self.template_name, context)

cleaning_schedule_view = CleaningScheduleView.as_view()
