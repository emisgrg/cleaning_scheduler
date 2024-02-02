from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()

class Apartment(models.Model):
    """
    Apartment model for cleaning_scheduler.
    This model represents an apartment available for cleaning scheduling.
    """

    owner = models.ForeignKey(User, related_name='apartments', on_delete=models.CASCADE)
    name = models.CharField(_("Name of Apartment"), max_length=255)
    location = models.CharField(_("Location"), max_length=500)
    size = models.CharField(_("Size of Apartment"), max_length=255)

    class Meta:
        app_label = 'cleaning_scheduler'
        unique_together = ('name', 'owner',)

    def get_absolute_url(self) -> str:
        """Get URL for apartment's detail view.

        Returns:
            str: URL for apartment detail.
        """
        # Assuming you have set up the URL patterns correctly
        return reverse("apartments:detail", kwargs={"id": self.id})

    def __str__(self):
        """String representation of the Apartment model.

        Returns:
            str: Name of the Apartment.
        """
        return self.name

class Booking(models.Model):
    apartment = models.ForeignKey(Apartment, on_delete=models.CASCADE)
    guest_name = models.CharField(max_length=100)
    check_in_date = models.DateTimeField()
    check_out_date = models.DateTimeField()
    
    class Meta:
        app_label = 'cleaning_scheduler'   

    def __str__(self):
        return f"{self.guest_name} - {self.apartment.name}"

class CleaningSchedule(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    cleaning_date = models.DateTimeField(null=True, blank=True)
    window_start = models.DateTimeField(null=True, blank=True)
    window_end = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        app_label = 'cleaning_scheduler'   
        
    def __str__(self):
        return f"{self.apartment.name} - {self.cleaning_date}"
