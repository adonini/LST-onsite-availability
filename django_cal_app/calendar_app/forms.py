from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Availability, MagicSecondFloorRequest, OnCallAssignment, UserContact


ON_CALL_GROUP = "On-call personnel"


class ContactForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    phone = forms.CharField(max_length=32, required=False, validators=[
        RegexValidator(r"^\+?[0-9 ()-]{6,32}$", "Enter a valid phone number.")
    ])


class OnCallDatesForm(forms.Form):
    all_day = forms.BooleanField(required=False)
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    start_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))
    end_time = forms.TimeField(required=False, widget=forms.TimeInput(attrs={"type": "time"}))

    def clean(self):
        data = super().clean()
        start_date, end_date = data.get("start_date"), data.get("end_date")
        if not start_date or not end_date:
            return data
        if data.get("all_day"):
            start = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
            end = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), datetime.min.time()))
        else:
            if not data.get("start_time") or not data.get("end_time"):
                raise ValidationError("Start and end times are required for timed assignments.")
            start = timezone.make_aware(datetime.combine(start_date, data["start_time"]))
            end = timezone.make_aware(datetime.combine(end_date, data["end_time"]))
        if end <= start:
            raise ValidationError("End must be later than start.")
        data["start_datetime"], data["end_datetime"] = start, end
        return data


class OnCallAssignmentForm(OnCallDatesForm):
    user = forms.ModelChoiceField(queryset=get_user_model().objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = get_user_model().objects.filter(
            groups__name=ON_CALL_GROUP, is_active=True
        ).order_by("first_name", "last_name", "username")

    def clean(self):
        data = super().clean()
        user = data.get("user")
        if user and (not user.email or not UserContact.objects.filter(user=user).exclude(phone="").exists()):
            raise ValidationError("The selected person needs an email and phone number in their profile.")
        return data


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
