from django import forms
from django.core.exceptions import ValidationError
from .models import Availability, MagicSecondFloorRequest


class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
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


class MagicSecondFloorRequestForm(forms.ModelForm):
    class Meta:
        model = MagicSecondFloorRequest
        fields = [
            'name',
            'surname',
            'institution',
            'email',
            'task',
            'start',
            'end',
            'comments',
        ]
        widgets = {
            'start': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'comments': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start')
        end = cleaned_data.get('end')

        if start and end and end <= start:
            raise ValidationError("End must be later than start.")

        return cleaned_data


class MagicSecondFloorRejectForm(forms.Form):
    rejection_reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
