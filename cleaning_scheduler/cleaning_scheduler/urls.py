from django.urls import path

from cleaning_scheduler.cleaning_scheduler.views import (
    apartment_detail_view,
    apartment_update_view,
    apartment_delete_view,
    apartment_list_view,
    apartment_create_view,
    calendar_view,
    cleaning_schedule_view
    )
app_name = "scheduler"
urlpatterns = [
    path("apartments/", view=apartment_list_view, name="apartments_list"),
    path("apartments/create/", view=apartment_create_view, name="apartments_create"),
    path("apartments/<int:id>/update/", view=apartment_update_view, name="apartments_update"),
    path("apartments/<int:id>/delete/", view=apartment_delete_view, name="apartments_delete"),
    path("apartments/<int:id>", view=apartment_detail_view, name="apartments_detail"),
    path("calendar/", view=calendar_view, name="calendar"),
    path('cleaning-schedule/', cleaning_schedule_view, name='cleaning_schedule'),
]
