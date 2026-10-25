from datetime import date, datetime

from django.core import mail
from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from calendar_app.management.commands.send_orm_staff_email import send_email

from .models import Activity, Availability, MagicSecondFloorRequest, Places, OnCallAssignment, UserContact


class UserAdminPhoneTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin_phone_test", password="test-password", email="admin@example.test"
        )
        self.client.force_login(self.admin_user)

    def test_change_user_shows_phone_below_email_and_saves_it(self):
        person = User.objects.create_user(username="phone_user", email="before@example.test")
        change_url = reverse("admin:auth_user_change", args=[person.pk])
        page = self.client.get(change_url)
        self.assertEqual(page.status_code, 200)
        self.assertLess(page.content.index(b'name="email"'), page.content.index(b'name="phone"'))

        response = self.client.post(change_url, {
            "username": person.username, "email": "after@example.test", "phone": "+34 600 123 456",
            "date_joined_0": person.date_joined.strftime("%Y-%m-%d"),
            "date_joined_1": person.date_joined.strftime("%H:%M:%S"),
            "is_active": "on", "_save": "Save",
        })
        self.assertEqual(response.status_code, 302, response.context["adminform"].form.errors if response.status_code == 200 else "")
        person.refresh_from_db()
        self.assertEqual(person.email, "after@example.test")
        self.assertEqual(person.contact.phone, "+34 600 123 456")
        self.assertContains(self.client.get(change_url), 'value="+34 600 123 456"')

        response = self.client.post(change_url, {
            "username": person.username, "email": person.email, "phone": "invalid!",
            "date_joined_0": person.date_joined.strftime("%Y-%m-%d"),
            "date_joined_1": person.date_joined.strftime("%H:%M:%S"),
            "is_active": "on", "_save": "Save",
        })
        self.assertEqual(response.status_code, 200)
        person.contact.refresh_from_db()
        self.assertEqual(person.contact.phone, "+34 600 123 456")

        response = self.client.post(change_url, {
            "username": person.username, "email": person.email, "phone": "",
            "date_joined_0": person.date_joined.strftime("%Y-%m-%d"),
            "date_joined_1": person.date_joined.strftime("%H:%M:%S"),
            "is_active": "on", "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        person.contact.refresh_from_db()
        self.assertEqual(person.contact.phone, "")

    def test_add_user_shows_phone_below_email_and_saves_it(self):
        add_url = reverse("admin:auth_user_add")
        page = self.client.get(add_url)
        self.assertEqual(page.status_code, 200)
        self.assertLess(page.content.index(b'name="email"'), page.content.index(b'name="phone"'))

        response = self.client.post(add_url, {
            "username": "new_phone_user", "email": "new@example.test", "phone": "+34 611 222 333",
            "password1": "test-password-123!", "password2": "test-password-123!", "_save": "Save",
        })
        self.assertEqual(response.status_code, 302)
        person = User.objects.get(username="new_phone_user")
        self.assertEqual(person.email, "new@example.test")
        self.assertEqual(person.contact.phone, "+34 611 222 333")


class OnCallTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staff_on_call", password="pass", is_staff=True)
        self.person = User.objects.create_user(username="on_call", password="pass", email="oncall@example.test")
        self.other = User.objects.create_user(username="other", password="pass", email="other@example.test")
        group, _ = Group.objects.get_or_create(name="On-call personnel")
        self.person.groups.add(group)
        UserContact.objects.create(user=self.person, phone="+34 600 000 000")

    def test_profile_updates_current_user_contact(self):
        self.client.force_login(self.person)
        response = self.client.post(reverse("my_profile"), {
            "first_name": "Ada", "last_name": "Test", "email": "ada@example.test", "phone": "+34 611 111 111",
        })
        self.assertRedirects(response, reverse("my_profile"))
        self.person.refresh_from_db()
        self.assertEqual(self.person.email, "ada@example.test")
        self.assertEqual(self.person.contact.phone, "+34 611 111 111")
        self.assertFalse(UserContact.objects.filter(user=self.other).exists())

    def test_only_staff_can_assign_group_members_with_contact_details(self):
        payload = {"user": self.person.pk, "all_day": "on", "start_date": "2026-10-26", "end_date": "2026-10-28"}
        self.client.force_login(self.person)
        self.assertNotEqual(self.client.post(reverse("create_on_call_assignment"), payload).status_code, 201)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.post(reverse("create_on_call_assignment"), {**payload, "user": self.other.pk}).status_code, 400)
        self.assertEqual(self.client.post(reverse("create_on_call_assignment"), payload).status_code, 201)
        assignment = OnCallAssignment.objects.get()
        self.assertEqual(assignment.end.date().isoformat(), "2026-10-29")

        self.client.logout()
        self.assertEqual(self.client.get(reverse("on_call_calendar")).status_code, 200)
        self.assertEqual(len(self.client.get(reverse("on_call_events")).json()), 1)
        details = self.client.get(reverse("on_call_details", args=[assignment.pk])).json()
        self.assertEqual(details["phone"], "+34 600 000 000")
        self.assertEqual(details["email"], "oncall@example.test")

    def test_timed_assignment_requires_valid_times(self):
        self.client.force_login(self.staff)
        payload = {"user": self.person.pk, "start_date": "2026-10-26", "end_date": "2026-10-26", "start_time": "18:00", "end_time": "09:00"}
        self.assertEqual(self.client.post(reverse("create_on_call_assignment"), payload).status_code, 400)
        payload["end_time"] = "22:00"
        self.assertEqual(self.client.post(reverse("create_on_call_assignment"), payload).status_code, 201)
        self.assertFalse(OnCallAssignment.objects.get().all_day)

    def test_staff_can_edit_only_assignment_dates(self):
        assignment = OnCallAssignment.objects.create(
            user=self.person,
            start=timezone.make_aware(datetime(2026, 10, 26)),
            end=timezone.make_aware(datetime(2026, 10, 29)),
            all_day=True,
            assigned_by=self.staff,
        )
        url = reverse("update_on_call_assignment", args=[assignment.pk])
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {
            "start_date": "2026-10-28", "end_date": "2026-10-28",
            "start_time": "18:00", "end_time": "09:00",
        }).status_code, 400)
        assignment.refresh_from_db()
        self.assertEqual(assignment.start.date().isoformat(), "2026-10-26")

        self.assertEqual(self.client.post(url, {
            "start_date": "2026-10-28", "end_date": "2026-10-28",
            "start_time": "18:00", "end_time": "22:00", "user": self.other.pk,
        }).status_code, 200)
        assignment.refresh_from_db()
        self.assertEqual(assignment.user, self.person)
        self.assertFalse(assignment.all_day)
        self.assertEqual(assignment.start.hour, 18)
        self.assertEqual(assignment.end.hour, 22)

        self.assertEqual(self.client.post(url, {
            "all_day": "on", "start_date": "2026-11-02", "end_date": "2026-11-04",
        }).status_code, 200)
        assignment.refresh_from_db()
        self.assertTrue(assignment.all_day)
        self.assertEqual(assignment.start.date().isoformat(), "2026-11-02")
        self.assertEqual(assignment.end.date().isoformat(), "2026-11-05")

    def test_only_staff_can_edit_or_delete_assignments(self):
        assignment = OnCallAssignment.objects.create(
            user=self.person,
            start=timezone.make_aware(datetime(2026, 10, 26)),
            end=timezone.make_aware(datetime(2026, 10, 27)),
            all_day=True,
            assigned_by=self.staff,
        )
        update_url = reverse("update_on_call_assignment", args=[assignment.pk])
        delete_url = reverse("delete_on_call_assignment", args=[assignment.pk])
        payload = {"all_day": "on", "start_date": "2026-11-02", "end_date": "2026-11-04"}
        self.client.force_login(self.person)
        self.assertNotEqual(self.client.post(update_url, payload).status_code, 200)
        self.assertNotEqual(self.client.post(delete_url).status_code, 200)
        self.assertTrue(OnCallAssignment.objects.filter(pk=assignment.pk).exists())

        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(delete_url).status_code, 405)
        self.assertEqual(self.client.post(delete_url).status_code, 200)
        self.assertFalse(OnCallAssignment.objects.filter(pk=assignment.pk).exists())

    def test_edit_and_delete_controls_are_staff_only(self):
        self.assertNotContains(self.client.get(reverse("on_call_calendar")), 'id="editOnCallButton"')
        self.assertNotContains(self.client.get(reverse("on_call_calendar")), 'id="deleteOnCallButton"')
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse("on_call_calendar")), 'id="editOnCallButton"')
        self.assertContains(self.client.get(reverse("on_call_calendar")), 'id="deleteOnCallButton"')


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


class MagicSecondFloorRequestTests(TestCase):
    def setUp(self):
        self.lst_user = User.objects.create_user(username="lst", password="password")
        self.normal_user = User.objects.create_user(username="normal", password="password")
        self.staff_user = User.objects.create_user(username="staff", password="password", is_staff=True)
        self.place = Places.objects.create(name="Remote")
        self.start = timezone.make_aware(datetime(2026, 7, 20, 10, 0))
        self.end = timezone.make_aware(datetime(2026, 7, 20, 12, 0))

    def _request_payload(self):
        return {
            "name": "Ada",
            "surname": "Lovelace",
            "institution": "LST",
            "email": "ada@example.com",
            "task": "Camera work",
            "start": "2026-07-20T10:00",
            "end": "2026-07-20T12:00",
            "comments": "Bring laptop",
        }

    def _create_magic_request(self, status=MagicSecondFloorRequest.PENDING):
        return MagicSecondFloorRequest.objects.create(
            name="Ada",
            surname="Lovelace",
            institution="LST",
            email="ada@example.com",
            task="Camera work",
            start=self.start,
            end=self.end,
            comments="Bring laptop",
            status=status,
            created_by=self.lst_user,
        )

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="lst-onsite@cta-observatory.org",
        MAGIC_REQUEST_NOTIFICATION_TO=["apenuela@ifae.es"],
        MAGIC_REQUEST_NOTIFICATION_CC=[],
    )
    def test_create_magic_request_stores_pending_request_and_sends_notification_email(self):
        self.client.force_login(self.lst_user)

        response = self.client.post(
            reverse("create_magic_second_floor_request"),
            self._request_payload(),
        )

        self.assertEqual(response.status_code, 200)
        request_obj = MagicSecondFloorRequest.objects.get()
        self.assertEqual(request_obj.status, MagicSecondFloorRequest.PENDING)
        self.assertEqual(request_obj.created_by, self.lst_user)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["apenuela@ifae.es"])
        self.assertEqual(mail.outbox[0].cc, [])
        self.assertEqual(mail.outbox[0].subject, "New Magic 2nd Floor Usage request")
        self.assertIn("Ada Lovelace", mail.outbox[0].body)
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        self.assertIn("<table", mail.outbox[0].alternatives[0][0])
        self.assertIn("Camera work", mail.outbox[0].alternatives[0][0])
        self.assertNotIn("Best regards", mail.outbox[0].body)
        self.assertNotIn("Best regards", mail.outbox[0].alternatives[0][0])

    def test_pending_magic_request_is_not_sent_to_calendar(self):
        self._create_magic_request(status=MagicSecondFloorRequest.PENDING)

        response = self.client.get(reverse("magic_second_floor_events"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_create_magic_request_returns_specific_validation_error(self):
        self.client.force_login(self.lst_user)
        payload = self._request_payload()
        payload["end"] = "2026-07-19T12:00"

        response = self.client.post(
            reverse("create_magic_second_floor_request"),
            payload,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "End must be later than start.")

    def test_approved_magic_request_is_sent_to_calendar(self):
        request_obj = self._create_magic_request(status=MagicSecondFloorRequest.APPROVED)

        response = self.client.get(reverse("magic_second_floor_events"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["id"], request_obj.id)
        self.assertEqual(response.json()[0]["title"], "Ada Lovelace - Camera work")

    def test_approved_magic_requests_use_different_event_colors(self):
        self._create_magic_request(status=MagicSecondFloorRequest.APPROVED)
        MagicSecondFloorRequest.objects.create(
            name="Grace",
            surname="Hopper",
            institution="LST",
            email="grace@example.com",
            task="PLC work",
            start=timezone.make_aware(datetime(2026, 7, 23, 10, 0)),
            end=timezone.make_aware(datetime(2026, 7, 23, 12, 0)),
            status=MagicSecondFloorRequest.APPROVED,
        )

        response = self.client.get(reverse("magic_second_floor_events"))

        self.assertEqual(response.status_code, 200)
        colors = {event["color"] for event in response.json()}
        self.assertEqual(len(colors), 2)

    def test_magic_request_details_include_submitted_fields(self):
        request_obj = self._create_magic_request(status=MagicSecondFloorRequest.APPROVED)

        response = self.client.get(reverse("magic_second_floor_request_details", args=[request_obj.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["institution"], "LST")
        self.assertEqual(response.json()["comments"], "Bring laptop")

    def test_magic_calendar_page_is_public(self):
        response = self.client.get(reverse("magic_second_floor"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Magic 2nd Floor Usage")
        self.assertNotContains(response, "Login to request")
        self.assertNotContains(response, "Request</button>")

    def test_staff_sees_pending_badge_on_magic_calendar_selector(self):
        self.client.force_login(self.staff_user)
        self._create_magic_request(status=MagicSecondFloorRequest.PENDING)

        response = self.client.get(reverse("calendar"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "pending Magic 2nd Floor requests")
        self.assertContains(response, "text-bg-danger")
        self.assertRegex(response.content.decode(), r">\s*1\s*<span class=\"visually-hidden\"")

    def test_magic_view_active_selector_does_not_show_selector_pending_badge(self):
        self.client.force_login(self.staff_user)
        self._create_magic_request(status=MagicSecondFloorRequest.PENDING)

        response = self.client.get(reverse("magic_second_floor"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "pending Magic 2nd Floor requests")
        self.assertContains(response, "Pending requests")

    def test_lst_user_cannot_create_availability_or_activity(self):
        self.client.force_login(self.lst_user)

        availability_response = self.client.post(reverse("add_event"), {
            "name_person": "Ada",
            "full_day": "on",
            "start_date": "2026-07-20",
            "end_date": "2026-07-21",
            "place": self.place.id,
        })
        activity_response = self.client.post(reverse("add_activity"), {
            "name_activity": "Test",
            "start": "2026-07-20",
            "end": "2026-07-20",
            "status": "OG",
            "telescope": "LST1",
        })

        self.assertEqual(availability_response.status_code, 403)
        self.assertEqual(activity_response.status_code, 403)
        self.assertFalse(Availability.objects.exists())
        self.assertFalse(Activity.objects.exists())

    def test_non_staff_user_cannot_access_pending_requests(self):
        self.client.force_login(self.normal_user)

        response = self.client.get(reverse("magic_second_floor_pending"))

        self.assertEqual(response.status_code, 302)

    def test_staff_user_can_access_pending_requests(self):
        self.client.force_login(self.staff_user)
        self._create_magic_request(status=MagicSecondFloorRequest.PENDING)

        response = self.client.get(reverse("magic_second_floor_pending"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ada Lovelace")

    def test_pending_admin_view_shows_overlapping_approved_request(self):
        self.client.force_login(self.staff_user)
        self._create_magic_request(status=MagicSecondFloorRequest.PENDING)
        MagicSecondFloorRequest.objects.create(
            name="Grace",
            surname="Hopper",
            institution="LST",
            email="grace@example.com",
            task="Overlapping work",
            start=timezone.make_aware(datetime(2026, 7, 20, 11, 0)),
            end=timezone.make_aware(datetime(2026, 7, 20, 13, 0)),
            status=MagicSecondFloorRequest.APPROVED,
            created_by=self.staff_user,
        )

        response = self.client.get(reverse("magic_second_floor_pending"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This request overlaps with approved or pending reservations")
        self.assertContains(response, "Grace Hopper")
        self.assertContains(response, "Overlapping work")

    def test_pending_admin_view_shows_overlapping_pending_request(self):
        self.client.force_login(self.staff_user)
        self._create_magic_request(status=MagicSecondFloorRequest.PENDING)
        MagicSecondFloorRequest.objects.create(
            name="Federico",
            surname="Mariscal",
            institution="IAC",
            email="fede@example.com",
            task="Device configuration",
            start=timezone.make_aware(datetime(2026, 7, 20, 11, 0)),
            end=timezone.make_aware(datetime(2026, 7, 20, 13, 0)),
            status=MagicSecondFloorRequest.PENDING,
            created_by=self.staff_user,
        )

        response = self.client.get(reverse("magic_second_floor_pending"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This request overlaps with approved or pending reservations")
        self.assertContains(response, "Federico Mariscal")
        self.assertContains(response, "Device configuration")
        self.assertContains(response, "overlap-dot")

        html = response.content.decode()
        first_color = html.split("background-color: ", 1)[1].split(";", 1)[0]
        self.assertGreaterEqual(html.count(f"background-color: {first_color};"), 2)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="lst-onsite@cta-observatory.org",
    )
    def test_staff_can_approve_request_and_email_is_sent(self):
        self.client.force_login(self.staff_user)
        request_obj = self._create_magic_request(status=MagicSecondFloorRequest.PENDING)

        response = self.client.post(
            reverse("approve_magic_second_floor_request", args=[request_obj.id]),
        )

        self.assertEqual(response.status_code, 302)
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, MagicSecondFloorRequest.APPROVED)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ada@example.com"])
        self.assertIn("approved", mail.outbox[0].subject)
        self.assertIn("LST onsite coordination", mail.outbox[0].body)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="lst-onsite@cta-observatory.org",
    )
    def test_staff_can_reject_request_with_reason_and_email_is_sent(self):
        self.client.force_login(self.staff_user)
        request_obj = self._create_magic_request(status=MagicSecondFloorRequest.PENDING)

        response = self.client.post(
            reverse("reject_magic_second_floor_request", args=[request_obj.id]),
            {"rejection_reason": "Room is already reserved."},
        )

        self.assertEqual(response.status_code, 302)
        request_obj.refresh_from_db()
        self.assertEqual(request_obj.status, MagicSecondFloorRequest.REJECTED)
        self.assertEqual(request_obj.rejection_reason, "Room is already reserved.")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ada@example.com"])
        self.assertIn("Room is already reserved.", mail.outbox[0].body)
        self.assertIn("LST onsite coordination", mail.outbox[0].body)
