from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import logging
from .models import Availability, Places, Activity, ActivityAssignment
from django.contrib import messages
from datetime import datetime, timedelta
from django.contrib.auth import logout, get_user_model, login
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from urllib.parse import urlencode
from django.views import View
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import SetPasswordForm
from django.views.generic import FormView
import json
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Q

# Get an instance of a logger
logger = logging.getLogger('calendar_app')

def logout_user(request):
    logout(request)
    url = reverse('calendar')
    qs = urlencode({'toast': 'Logged out successfully', 'toast_type': 'success'})
    return redirect(f'{url}?{qs}')

class CustomLoginView(LoginView):
    def form_valid(self, form):
        user = form.get_user()
        logger.info(user)
        if not user.last_login:
            self.request.session["first_login_user_id"] = user.id
            return redirect('first_login_change_password')
        else:
            # Log in the user first
            response = super().form_valid(form)
            user = self.request.user
            return response

UserModel = get_user_model()

class FirstLoginPasswordChangeView(FormView):
    template_name = 'registration/first_login_password_change.html'
    form_class = SetPasswordForm
    success_url = reverse_lazy('calendar')

    def dispatch(self, request, *args, **kwargs):
        user_id = request.session.get("first_login_user_id")
        if not user_id:
            return redirect("login")

        self.user = UserModel.objects.filter(id=user_id).first()
        if not self.user:
            return redirect("login")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.user
        return kwargs

    def form_valid(self, form):
        form.save()
        login(self.request, self.user)  # Re-log user with new credentials
        del self.request.session["first_login_user_id"]
        return super().form_valid(form)

def calendar_view(request):
    all_events = Availability.objects.all()
    places = Places.objects.all().order_by('name')
    context = {
        "events": all_events,
        "places": places,
    }
    return render(request, 'calendar.html', context)

@csrf_exempt
@login_required
def add_event(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'fail', 'message': 'Invalid request method'}, status=405)

    try:
        logger.info(request.POST)

        name_person = request.POST.get('name_person')
        full_day = request.POST.get('full_day') == 'on'
        place = request.POST.get('place')
        notes = request.POST.get('notes')

        if full_day:
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end = datetime.strptime(end_date, '%Y-%m-%d').date() + timedelta(days=1)
            else:
                end = start + timedelta(days=1)
        else:
            start_date = request.POST.get('start_date')
            start_time = request.POST.get('start_time')
            end_date = request.POST.get('end_date')
            end_time = request.POST.get('end_time')

            start = datetime.combine(
                datetime.strptime(start_date, '%Y-%m-%d').date(),
                datetime.strptime(start_time, '%H:%M').time()
            )

            if end_date and end_time:
                end = datetime.combine(
                    datetime.strptime(end_date, '%Y-%m-%d').date(),
                    datetime.strptime(end_time, '%H:%M').time()
                )
            else:
                end = start

        is_update = bool(request.POST.get('id'))

        if not is_update:
            logger.info('Creating the event')
            event = Availability(
                name_person=name_person,
                start=start,
                end=end,
                all_day=full_day,
                place=Places.objects.get(pk=place),
                notes=notes,
                created_by=request.user
            )
        else:
            logger.info('Updating the event')
            event = Availability.objects.get(pk=request.POST.get('id'))
            if event.created_by_id != request.user.id:
             return JsonResponse(
                 {'status': 'forbidden', 'message': 'You can only edit your own availability'},
                 status=403
             )
            event.name_person = name_person
            event.start = start
            event.end = end
            event.all_day = full_day
            event.place = Places.objects.get(pk=place)
            event.notes = notes

        event.save()

        event_info = f'Availability ID: {event.id}, Name: {event.name_person}, Start: {event.start}, End: {event.end}, All day: {event.all_day}, Place: {event.place}, Notes: {event.notes}'

        if not is_update:
            logger.info(f'Availability added by {request.user}: {event_info}')
            return JsonResponse({'status': 'success', 'message': 'Availability added successfully!', 'id': event.id})
        else:
            logger.info(f'Availability updated by {request.user}: {event_info}')
            return JsonResponse({'status': 'success', 'message': 'Availability updated successfully!', 'id': event.id})

    except Exception as e:
        logger.error(f'Error adding/updating event: {e}')
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

def all_events(request):
    events = Availability.objects.all()
    events_list = []

    # color map for places
    color_map = {
        'Calp': '#002642',
        'ORM Day': '#840032',
        'ORM Night': '#45001a',
        'Remote': '#e59500',
        'Remote - Off the Island': '#8c5b00',
        'Holiday': '#7600d1',
        'Holiday - Off the Island': '#4f008c',
        'Mirca': '#008000'
    }

    for event in events:
        place_color = color_map.get(event.place.name, '#000000')
        events_list.append({
            'id': event.id,
            'title': f"{event.name_person} - {event.place}",
            'name_person': event.name_person,
            'start': event.start.isoformat(),
            'end': event.end.isoformat(),
            'allDay': event.all_day,
            'place': event.place.name,
            'notes': event.notes,
            'color': place_color,
        })
    return JsonResponse(events_list, safe=False)

def assign_users(request):
    events = Availability.objects.all()
    for event in events:
        if not event.created_by:
            try:
                event.created_by = User.objects.get(first_name=event.name_person)
                event.save()
            except User.DoesNotExist:
                logger.info(event.name_person)

def event_details(request, event_id):
    event = get_object_or_404(Availability, id=event_id)
    event_data = {}
    if event.all_day:
        event_data = {
            'id': event.pk,
            'title': event.name_person,
            'start': event.start.strftime("%Y-%m-%d"),
            'end': event.end.strftime("%Y-%m-%d"),
            'place': event.place.name,
            'notes': event.notes,
            'all_day': event.all_day,
            'creator': event.created_by.username if event.created_by else None,
        }
    else:
        event_data = {
            'id': event.pk,
            'title': event.name_person,
            'start': event.start.strftime("%Y-%m-%d %H:%M"),
            'end': event.end.strftime("%Y-%m-%d %H:%M"),
            'place': event.place.name,
            'notes': event.notes,
            'all_day': event.all_day,
            'creator': event.created_by.username if event.created_by else None,
        }
    return JsonResponse(event_data)

@csrf_exempt
@login_required
def remove_event(request):
    if request.method != 'POST':
        return JsonResponse(
            {'status': 'fail', 'message': 'Invalid request method'},
            status=405
        )

    event_id = request.POST.get('id')
    if not event_id:
        return JsonResponse(
            {'status': 'error', 'message': 'Missing event id'},
            status=400
        )

    try:
        event = get_object_or_404(Availability, id=event_id)
        if event.created_by_id != request.user.id:
            return JsonResponse(
                {'status': 'forbidden', 'message': 'You can only delete your own availability'},
                status=403
            )

        event_info = (
            f'Availability ID: {event.id}, Name: {event.name_person}, '
            f'Start: {event.start}, End: {event.end}, All day: {event.all_day}, '
            f'Place: {event.place}, Notes: {event.notes}'
        )

        event.delete()

        logger.info(f'Availability deleted by {request.user}: {event_info}')
        return JsonResponse(
            {'status': 'success', 'message': 'Availability deleted successfully!', 'id': event_id},
            status=200
        )

    except Exception as e:
        logger.error(f'Error deleting event with ID {event_id}: {e}')
        return JsonResponse(
            {'status': 'error', 'message': str(e)},
            status=400
        )

# -------------------------
# Activities endpoints
# -------------------------

def _parse_d_local(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return datetime.strptime(value, '%Y-%m-%d').date()

@csrf_exempt
@login_required
def add_activity(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'fail', 'message': 'Invalid request method'}, status=405)

    try:
        logger.info(request.POST)

        name_activity = request.POST.get('name_activity')
        start_raw = request.POST.get('start')
        end_raw = request.POST.get('end')
        status_val = request.POST.get('status')
        telescope = request.POST.get('telescope')
        comments = request.POST.get('comments')
        description = request.POST.get('description')

        start = _parse_d_local(start_raw)
        end = _parse_d_local(end_raw)

        if not start:
            raise ValueError("Start date is required")

        if end and end < start:
            raise ValueError("End must be greater than Start")

        is_update = bool(request.POST.get('id'))

        if not is_update:
            logger.info('Creating the activity')
            activity = Activity(
                name_activity=name_activity,
                start=start,
                end=end,
                status=status_val,
                telescope=telescope,
                comments=comments,
                description=description,
                created_by=request.user
            )
        else:
            logger.info('Updating the activity')
            activity = Activity.objects.get(pk=request.POST.get('id'))
            activity.name_activity = name_activity
            activity.start = start
            activity.end = end
            activity.status = status_val
            activity.telescope = telescope
            activity.comments = comments
            activity.description = description

        activity.save()

        activity_info = f'Activity ID: {activity.id}, Name: {activity.name_activity}, Start: {activity.start}, End: {activity.end}, Status: {activity.status}, Telescope: {activity.telescope}'

        if not is_update:
            logger.info(f'Activity added by {request.user}: {activity_info}')
            return JsonResponse({'status': 'success', 'message': 'Activity added successfully!', 'id': activity.id})
        else:
            logger.info(f'Activity updated by {request.user}: {activity_info}')
            return JsonResponse({'status': 'success', 'message': 'Activity updated successfully!', 'id': activity.id})

    except Exception as e:
        logger.error(f'Error adding/updating activity: {e}')
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

def all_activities(request):
    activities = Activity.objects.all()
    activities_list = []

    status_color_map = {
        'C': '#2E7D32',
        'OG': '#1565C0',
        'OH': '#616161', 
    }

    status_label_map = {
        'C': 'Completed',
        'OG': 'On going',
        'OH': 'On hold',
    }

    for activity in activities:
        status_color = status_color_map.get(activity.status, '#000000')  # Default to black
        status_label = status_label_map.get(activity.status, activity.status)

        activities_list.append({
            "id": activity.id,
            "title": f"[{activity.telescope}] {activity.name_activity} - {status_label}",
            "start": activity.start.isoformat(),
            "end": (activity.end + timedelta(days=1)).isoformat() if activity.end else None,
            "color": status_color,
            "classNames": ["activity-event"],
        })

    return JsonResponse(activities_list, safe=False)

def activity_details(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)

    assignees = list(
        activity.assignees.all()
        .order_by("first_name", "last_name", "username")
        .values("id", "username", "first_name", "last_name")
    )

    def label(u):
        full = (f"{u['first_name']} {u['last_name']}").strip()
        return full or u["username"]

    return JsonResponse({
        "id": activity.id,
        "name_activity": activity.name_activity,
        "description": activity.description,
        "start": activity.start.strftime("%Y-%m-%d"),
        "end": activity.end.strftime("%Y-%m-%d") if activity.end else None,
        "status": activity.status,
        "status_display": activity.get_status_display(),
        "telescope": activity.telescope,
        "telescope_display": activity.get_telescope_display(),
        "comments": activity.comments,
        "assignees": [{"id": u["id"], "label": label(u), "username": u["username"]} for u in assignees],
    })

@csrf_exempt
@login_required
def remove_activity(request):
    if request.method != 'POST':
        return JsonResponse(
            {'status': 'fail', 'message': 'Invalid request method'},
            status=405
        )

    activity_id = request.POST.get('id')
    if not activity_id:
        return JsonResponse(
            {'status': 'error', 'message': 'Missing activity id'},
            status=400
        )

    try:
        activity = get_object_or_404(Activity, id=activity_id)

        activity_info = (
            f'Activity ID: {activity.id}, Name: {activity.name_activity}, '
            f'Start: {activity.start}, End: {activity.end}, '
            f'Status: {activity.status}, Telescope: {activity.telescope}'
        )

        activity.delete()

        logger.info(f'Activity deleted by {request.user}: {activity_info}')

        return JsonResponse(
            {'status': 'success', 'message': 'Activity deleted successfully!', 'id': activity_id},
            status=200
        )

    except Exception as e:
        logger.error(f'Error deleting activity with ID {activity_id}: {e}')
        return JsonResponse(
            {'status': 'error', 'message': str(e)},
            status=400
        )

@csrf_exempt
@login_required
@require_POST
def set_activity_assignees(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
        user_ids = payload.get("user_ids", [])
        desired_ids = {int(x) for x in user_ids}
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"Bad payload: {e}"}, status=400)

    existing_ids = set(activity.assignees.values_list("id", flat=True))
    to_add = desired_ids - existing_ids
    to_remove = existing_ids - desired_ids

    User = get_user_model()

    with transaction.atomic():
        if to_remove:
            ActivityAssignment.objects.filter(activity=activity, user_id__in=to_remove).delete()

        if to_add:
            valid_ids = set(User.objects.filter(id__in=to_add).values_list("id", flat=True))
            ActivityAssignment.objects.bulk_create(
                [
                    ActivityAssignment(activity=activity, user_id=uid, assigned_by=request.user)
                    for uid in valid_ids
                ],
                ignore_conflicts=True,
            )

    assignees = activity.assignees.all().order_by("first_name", "last_name", "username")
    return JsonResponse({
        "status": "success",
        "message": "Assignees updated",
        "assignees": [
            {"id": u.id, "name": (u.get_full_name() or u.username), "username": u.username}
            for u in assignees
        ]
    })

@login_required
def search_users(request):
    q = (request.GET.get("q") or "").strip()
    User = get_user_model()

    qs = User.objects.all()
    if q:
        qs = qs.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        )

    qs = qs.order_by("first_name", "last_name")[:20]

    return JsonResponse([{
        "id": u.id,
        "label": (u.get_full_name() or u.username),
        "username": u.username
    } for u in qs], safe=False)
