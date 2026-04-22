import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone

from ...models import Availability


logger = logging.getLogger("calendar_app")

EMAIL_SUBJECT = "Personal en el ORM - LST Collaboration"
EMAIL_TEMPLATE = "emails/email.html"
EXCLUDED_JSON_TITLE_SUBSTRINGS = {
    "alice donini",
    "daniel mazin",
    "stefan horn",
}


def parse_json_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_availability_display_name(availability):
    if availability.created_by:
        full_name = (
            f"{availability.created_by.first_name} {availability.created_by.last_name}"
        ).strip()
        if full_name:
            return full_name
    return availability.name_person


def classify_availability_bucket(place_name):
    place_name_lower = (place_name or "").lower()
    if "night" in place_name_lower:
        return "night"
    return "day"


def classify_json_bucket(purpose):
    if "shift" in (purpose or "").lower():
        return "night"
    return "day"


def should_exclude_json_title(title):
    normalized_title = (title or "").casefold()
    return any(excluded in normalized_title for excluded in EXCLUDED_JSON_TITLE_SUBSTRINGS)


def get_today_availabilities(report_date):
    daytime_staff = []
    nighttime_staff = []

    availabilities = (
        Availability.objects.select_related("place", "created_by")
        .filter(
            start__date__lte=report_date,
            end__date__gte=report_date+timedelta(days=1),
            place__name__icontains="ORM",
        )
        .order_by("start", "name_person")
    )
    for availability in availabilities:
        display_name = get_availability_display_name(availability)
        bucket = classify_availability_bucket(availability.place.name)
        if bucket == "night":
            nighttime_staff.append(display_name)
        else:
            daytime_staff.append(display_name)

    return daytime_staff, nighttime_staff


def load_json_staff(report_date, json_paths):
    daytime_staff = []
    nighttime_staff = []

    for raw_path in json_paths:
        path = Path(raw_path)
        if not path.exists():
            logger.warning("Skipping missing onsite events JSON: %s", path)
            continue

        with path.open("r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)

        if not isinstance(payload, list):
            logger.warning("Skipping invalid onsite events JSON payload: %s", path)
            continue

        for item in payload:
            if not isinstance(item, dict):
                continue

            title = (item.get("title") or "").strip()
            start_raw = (item.get("start") or "").strip()
            end_raw = (item.get("end") or "").strip()

            if not title or not start_raw or not end_raw:
                continue

            if should_exclude_json_title(title):
                continue

            try:
                start_date = parse_json_date(start_raw)
                end_date = parse_json_date(end_raw)
            except ValueError:
                logger.warning("Skipping JSON entry with invalid dates in %s: %s", path, item)
                continue

            if not (start_date <= report_date <= end_date):
                continue

            bucket = classify_json_bucket(item.get("purpose"))
            if bucket == "night":
                nighttime_staff.append(title)
            else:
                daytime_staff.append(title)

    return daytime_staff, nighttime_staff


def build_context(report_date, json_paths):
    availability_daytime, availability_nighttime = get_today_availabilities(report_date)
    json_daytime, json_nighttime = load_json_staff(report_date, json_paths)

    daytime_staff = sorted(
        availability_daytime + json_daytime,
        key=lambda value: value.casefold(),
    )
    nighttime_staff = sorted(
        availability_nighttime + json_nighttime,
        key=lambda value: value.casefold(),
    )

    return {
        "subject": EMAIL_SUBJECT,
        "report_date": report_date,
        "daytime_staff": daytime_staff,
        "nighttime_staff": nighttime_staff,
        "count_daytime_staff": len(daytime_staff),
        "count_nighttime_staff": len(nighttime_staff),
        "json_paths": json_paths,
    }


def send_email(context):
    html_content = render_to_string(EMAIL_TEMPLATE, context)
    msg = EmailMultiAlternatives(
        subject=EMAIL_SUBJECT,
        body="This email requires an HTML-capable client.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=settings.ORM_STAFF_EMAIL_TO,
        cc=settings.ORM_STAFF_EMAIL_CC,
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()


class Command(BaseCommand):
    help = "Send the daily ORM staff email using availabilities and onsite JSON events."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Build the email context without sending the email.",
        )
        parser.add_argument(
            "--json-path",
            action="append",
            dest="json_paths",
            help="Override the configured JSON paths. Can be used multiple times.",
        )

    def handle(self, *args, **options):
        report_date = timezone.localdate()
        json_paths = options.get("json_paths") or settings.ONSITE_EVENTS_JSON_PATHS

        if not settings.ORM_STAFF_EMAIL_TO:
            self.stderr.write(self.style.ERROR("No recipients configured in ORM_STAFF_EMAIL_TO"))
            return

        context = build_context(report_date, json_paths)

        self.stdout.write(f"Report date: {report_date}")
        self.stdout.write(f"Recipients: {', '.join(settings.ORM_STAFF_EMAIL_TO)}")
        if settings.ORM_STAFF_EMAIL_CC:
            self.stdout.write(f"Cc: {', '.join(settings.ORM_STAFF_EMAIL_CC)}")
        self.stdout.write(f"JSON paths: {', '.join(json_paths)}")
        self.stdout.write(f"Daytime staff: {context['count_daytime_staff']}")
        self.stdout.write(f"Nighttime staff: {context['count_nighttime_staff']}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run enabled. Email was not sent."))
            return

        send_email(context)
        self.stdout.write(self.style.SUCCESS("ORM staff email sent successfully."))
