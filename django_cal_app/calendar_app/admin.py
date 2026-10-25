from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from .models import Activity, Places, Availability, MagicSecondFloorRequest, UserContact, OnCallAssignment


phone_field = forms.CharField(
    label="Phone", max_length=32, required=False,
    validators=[RegexValidator(r"^\+?[0-9 ()-]{6,32}$", "Enter a valid phone number.")],
)


class UserWithPhoneChangeForm(UserChangeForm):
    phone = phone_field

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["phone"].initial = (
                UserContact.objects.filter(user=self.instance).values_list("phone", flat=True).first() or ""
            )


class UserWithPhoneCreationForm(UserCreationForm):
    phone = phone_field


admin.site.unregister(User)


@admin.register(User)
class UserWithPhoneAdmin(UserAdmin):
    form = UserWithPhoneChangeForm
    add_form = UserWithPhoneCreationForm
    fieldsets = (
        UserAdmin.fieldsets[0],
        (UserAdmin.fieldsets[1][0], {
            **UserAdmin.fieldsets[1][1],
            "fields": ("first_name", "last_name", "email", "phone"),
        }),
        *UserAdmin.fieldsets[2:],
    )
    add_fieldsets = (
        (UserAdmin.add_fieldsets[0][0], {
            **UserAdmin.add_fieldsets[0][1],
            "fields": ("username", "email", "phone", "password1", "password2"),
        }),
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        phone = form.cleaned_data["phone"]
        if phone or UserContact.objects.filter(user=obj).exists():
            UserContact.objects.update_or_create(user=obj, defaults={"phone": phone})

# Register your models here.
admin.site.register(Activity)
admin.site.register(Places)
admin.site.register(Availability)


@admin.register(UserContact)
class UserContactAdmin(admin.ModelAdmin):
    list_display = ("user", "phone")
    search_fields = ("user__username", "user__first_name", "user__last_name", "phone")


@admin.register(OnCallAssignment)
class OnCallAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "start", "end", "all_day", "assigned_by")
    list_filter = ("all_day", "start")


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
