from django.db import models
from django.contrib.auth.models import User


class Event(models.Model):
    name_person = models.CharField(max_length=100)
    start = models.DateTimeField()
    end = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    place = models.CharField(max_length=100)
    notes = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_events')
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_events')

    def __str__(self):
        return self.name_person
