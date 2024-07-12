from django import forms
from django.core.exceptions import ValidationError
from .models import Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name_person', 'start', 'end', 'place', 'notes', 'all_day']

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start')
        end = cleaned_data.get('end')
        all_day = cleaned_data.get('all_day')

        if not all_day and start and end:
            # Ensure end time is not before start time on the same day
            if start.date() == end.date() and start.time() > end.time():
                raise ValidationError("End time cannot be before start time on the same day.")

        return cleaned_data
