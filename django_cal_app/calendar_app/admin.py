from django.contrib import admin
from .models import Activity, Places, Availability, MagicSecondFloorRequest

# Register your models here.
admin.site.register(Activity)
admin.site.register(Places)
admin.site.register(Availability)


@admin.register(MagicSecondFloorRequest)
class MagicSecondFloorRequestAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "surname",
        "institution",
        "email",
        "task",
        "start",
        "end",
        "status",
        "created_at",
    )
    list_filter = ("status", "institution", "start")
    search_fields = ("name", "surname", "institution", "email", "task")
    readonly_fields = ("created_at", "reviewed_at")
