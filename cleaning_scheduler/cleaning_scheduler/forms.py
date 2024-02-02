from django import forms
from cleaning_scheduler.cleaning_scheduler.models import Apartment
from django.core.exceptions import ValidationError


class ApartmentCreationForm(forms.ModelForm):
    class Meta:
        model = Apartment
        fields = ['name', 'location', 'size']

class ApartmentUpdateForm(forms.ModelForm):
    class Meta:
        model = Apartment
        fields = ['name', 'location', 'size']
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Apartment.objects.filter(name=name, owner=self.request.user).exclude(pk=self.instance.pk).exists():
            raise ValidationError("You already have an apartment with this name.")
        return name

class ApartmentDeletionForm(forms.ModelForm):
    class Meta:
        model = Apartment
        fields = [] 

    def save(self, commit=True):
        if commit:
            self.instance.delete()
        return self.instance
