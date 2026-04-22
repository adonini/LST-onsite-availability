from datetime import date, datetime

from django.core import mail
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from calendar_app.management.commands.send_orm_staff_email import send_email

from .models import Activity


class ActivityCalendarSerializationTests(TestCase):
    def test_single_day_activity_is_sent_as_one_all_day_cell(self):
        activity = Activity.objects.create(
            name_activity="Visit Apinsa",
            start=timezone.make_aware(datetime(2026, 4, 15, 0, 0)),
            end=timezone.make_aware(datetime(2026, 4, 15, 0, 0)),
            status="C",
            telescope="LST1",
        )

        response = self.client.get(reverse("all_activities"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [{
            "id": activity.id,
            "title": "[LST1] Visit Apinsa - Completed",
            "start": "2026-04-15",
            "end": "2026-04-16",
            "allDay": True,
            "color": "#2E7D32",
            "classNames": ["activity-event"],
        }])

    def test_multi_day_activity_keeps_inclusive_end_for_display(self):
        activity = Activity.objects.create(
            name_activity="Visit Apinsa",
            start=timezone.make_aware(datetime(2026, 4, 15, 0, 0)),
            end=timezone.make_aware(datetime(2026, 4, 16, 0, 0)),
            status="C",
            telescope="LST1",
        )

        response = self.client.get(reverse("all_activities"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [{
            "id": activity.id,
            "title": "[LST1] Visit Apinsa - Completed",
            "start": "2026-04-15",
            "end": "2026-04-17",
            "allDay": True,
            "color": "#2E7D32",
            "classNames": ["activity-event"],
        }])


class OrmStaffEmailTests(TestCase):
    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="lst-onsite@cta-observatory.org",
        ORM_STAFF_EMAIL_TO=["receporm@iac.es"],
        ORM_STAFF_EMAIL_CC=["lst-lapalma-team@cta-observatory.org"],
    )
    def test_send_email_includes_configured_cc_recipient(self):
        context = {
            "subject": "Personal en el ORM - LST Collaboration",
            "report_date": date(2026, 4, 22),
            "daytime_staff": ["Day Person"],
            "nighttime_staff": ["Night Person"],
        }

        send_email(context)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["receporm@iac.es"])
        self.assertEqual(mail.outbox[0].cc, ["lst-lapalma-team@cta-observatory.org"])
