from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

class Places(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name


class Availability(models.Model):
    name_person = models.CharField(max_length=100)
    start = models.DateTimeField()
    end = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    place = models.ForeignKey(Places, on_delete=models.SET_NULL, null=True, related_name='place')
    notes = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_availability')
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_availability')

    def __str__(self):
        return self.name_person
    
class Activity(models.Model):
    name_activity = models.CharField(max_length=200)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True)
    status = models.CharField(choices={"OG": "On Going", "OH": "On hold", "C": "Completed"}, max_length=100)
    telescope = models.CharField(choices={"Common": "Common", "LST1": "LST1", "LST2": "LST2", "LST3": "LST3", "LST4":"LST4"}, max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_activity')
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='deleted_activity')
    comments = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="assigned_activities",
        blank=True,
        through="ActivityAssignment",
        through_fields=("activity", "user"),
    )
    
    def __str__(self):
        return "["+self.telescope+"] "+self.name_activity+" - "+self.status

class ActivityAssignment(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="activity_assignments_made",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("activity", "user")


class MagicSecondFloorRequest(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    STATUS_CHOICES = {
        PENDING: "Pending",
        APPROVED: "Approved",
        REJECTED: "Rejected",
    }

    name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)
    institution = models.CharField(max_length=200)
    email = models.EmailField()
    task = models.CharField(max_length=250)
    start = models.DateTimeField()
    end = models.DateTimeField()
    comments = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
    )
    rejection_reason = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="magic_second_floor_requests_created",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="magic_second_floor_requests_reviewed",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["start", "created_at"]

    def __str__(self):
        return f"{self.name} {self.surname} - {self.task}"
