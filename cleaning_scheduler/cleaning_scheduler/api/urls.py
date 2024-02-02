from django.urls import path
from .views import ApartmentListCreateView, ApartmentDetailView, ApartmentUpdateView, ApartmentDeleteView, CalendarAPIView, CleaningScheduleAPIView

urlpatterns = [
    path('apartments/', ApartmentListCreateView.as_view(), name='apartments_list_create'),
    path('apartments/<int:id>/', ApartmentDetailView.as_view(), name='apartment_detail'),
    path('apartments/<int:id>/update/', ApartmentUpdateView.as_view(), name='apartment_update'),
    path('apartments/<int:id>/delete/', ApartmentDeleteView.as_view(), name='apartment_delete'),
    path('calendar/bookings/', CalendarAPIView.as_view(), name='calendar_bookings'),
    path('calendar/cleaning/', CleaningScheduleAPIView.as_view(), name='calendar_cleaning'),

]
