from django.contrib import admin
from .models import Activity, Places, Availability

# Register your models here.
admin.site.register(Activity)
admin.site.register(Places)
admin.site.register(Availability)