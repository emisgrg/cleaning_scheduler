from django.conf import settings
from django.contrib import admin
from cleaning_scheduler.cleaning_scheduler.models import Apartment

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://docs.allauth.org/en/latest/common/admin.html#admin
    admin.site.login = decorators.login_required(admin.site.login)  # type: ignore[method-assign]


@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    # Define the fields that will be displayed in the admin list view
    list_display = ['name', 'location', 'size', 'owner']

    # Add a search bar to the admin list view
    search_fields = ['name', 'location', 'owner__username']

    # Define the fields that will be editable in the admin detail view
    # You can organize fields into sections using tuples
    fieldsets = (
        (None, {"fields": ("owner", "name")}),
        ("Location Information", {"fields": ("location",)}),
        # Add more sections as needed
    )
