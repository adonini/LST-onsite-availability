from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import logging
from .models import Event, Places
from django.contrib import messages
from datetime import datetime, timedelta
from django.contrib.auth import logout, get_user_model, login
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.views import View
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import SetPasswordForm
from django.views.generic import FormView


# Get an instance of a logger
logger = logging.getLogger('calendar_app')


def logout_user(request):
    logout(request)
    messages.success(request, "You Have Been Logged Out!")
    return redirect('calendar')

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
    all_events = Event.objects.all()
    places = Places.objects.all().order_by('name')
    context = {
        "events": all_events,
        "places": places,
    }
    return render(request, 'calendar.html', context)


@csrf_exempt
@login_required
def add_event(request):
    if request.method == 'POST':
        try:
            logger.info(request.POST)
            name_person = request.POST.get('name_person')
            full_day = request.POST.get('full_day') == 'on'  # Checkbox value
            place = request.POST.get('place')
            notes = request.POST.get('notes')

            if full_day:
                start_date = request.POST.get('start_date')
                end_date = request.POST.get('end_date')
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                if end_date:
                    end = datetime.strptime(end_date, '%Y-%m-%d').date() + timedelta(days=1)  # Full calendar has exclusive end date
                else:
                    end = start + timedelta(days=1)  # Default to next day if end date not specified

            else:
                start_date = request.POST.get('start_date')
                start_time = request.POST.get('start_time')
                end_date = request.POST.get('end_date')
                end_time = request.POST.get('end_time')
                start = datetime.combine(datetime.strptime(start_date, '%Y-%m-%d').date(), datetime.strptime(start_time, '%H:%M').time())
                if end_date and end_time:
                    end = datetime.combine(datetime.strptime(end_date, '%Y-%m-%d').date(), datetime.strptime(end_time, '%H:%M').time())
                else:
                    # Handle case where end_date or end_time is not provided
                    end = datetime.combine(datetime.strptime(start_date, '%Y-%m-%d').date(), datetime.strptime(start_time, '%H:%M').time())

            if not request.POST.get('id'):
                # Create an Event object
                logger.info('Creating the event')
                event = Event(
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
                event = Event.objects.get(pk=request.POST.get('id'))
                event.name_person=name_person
                event.start=start
                event.end=end
                event.all_day=full_day
                event.place=Places.objects.get(pk=place)
                event.notes=notes

            # Save the event to the database
            event.save()
            data = {}
            event_info = f'Event ID: {event.id}, Name: {event.name_person}, Start: {event.start}, End: {event.end}, All day: {event.all_day}, Place: {event.place}, Notes: {event.notes}'
            if not request.POST.get('id'):
                messages.success(request, "Event added successfully!")
                logger.info(f'Event added by {request.user}: {event_info}')
            else:
                messages.success(request, "Event updated successfully!")
                logger.info(f'Event updated by {request.user}: {event_info}')
            return JsonResponse(data)
        except Exception as e:
            messages.error(request, f"There was an error adding the event: {e}")
            logger.error(f'Error adding event: {e}')
            return JsonResponse({'status': 'error'})
    return JsonResponse({'status': 'fail'})


def all_events(request):
    events = Event.objects.all()
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
        place_color = color_map.get(event.place.name, '#000000')  # Default to black if place not found
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
    events= Event.objects.all()
    for event in events:
        if not event.created_by:
            try:
                event.created_by = User.objects.get(first_name=event.name_person)
                event.save()
            except User.DoesNotExist:
                logger.info(event.name_person)

def event_details(request, event_id):
    event = get_object_or_404(Event, id=event_id)
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


# @csrf_exempt
# @login_required
# def update_event(request):
#     if request.method == 'POST':
#         try:
#             event_id = request.POST.get('id')
#             event = get_object_or_404(Event, id=event_id)
#             name_person = request.POST.get('name_person')
#             full_day = request.POST.get('full_day') == 'on'
#             place = request.POST.get('place')
#             notes = request.POST.get('notes')

#             if full_day:
#                 start_date = request.POST.get('start_date')
#                 end_date = request.POST.get('end_date')
#                 start = datetime.strptime(start_date, '%Y-%m-%d').date()
#                 end = datetime.strptime(end_date, '%Y-%m-%d').date()
#                 end += timedelta(days=1)
#             else:
#                 start_date = request.POST.get('start_date')
#                 start_time = request.POST.get('start_time')
#                 end_date = request.POST.get('end_date')
#                 end_time = request.POST.get('end_time')
#                 start = datetime.combine(datetime.strptime(start_date, '%Y-%m-%d').date(), datetime.strptime(start_time, '%H:%M').time())
#                 end = datetime.combine(datetime.strptime(end_date, '%Y-%m-%d').date(), datetime.strptime(end_time, '%H:%M').time())

#             event.name_person = name_person
#             event.start = start
#             event.end = end
#             event.all_day = full_day
#             event.place = place
#             event.notes = notes

#             event.save()
#             messages.success(request, "Event updated successfully!")
#             #data = {}
#             #return JsonResponse(data)
#             messages.success(request, "Event updated successfully!")
#             return JsonResponse({'status': 'success'})
#         except Exception as e:
#             messages.error(request, f"There was an error updating the event: {e}")
#             return JsonResponse({'status': 'error'})
#     return JsonResponse({'status': 'fail'})


@csrf_exempt
@login_required
def remove_event(request):
    if request.method == 'POST':
        try:
            event_id = request.POST.get('id')
            # Log the event ID for debugging
            print(f"Attempting to delete event with ID: {event_id}")
            event = get_object_or_404(Event, id=event_id)
            event_info = f'Event ID: {event.id}, Name: {event.name_person}, Start: {event.start}, End: {event.end}, All day: {event.all_day}, Place: {event.place}, Notes: {event.notes}'
            event.delete()
            messages.success(request, "Event deleted successfully!")
            logger.info(f'Event deleted by {request.user}: {event_info}')
            #data = {}
            #return JsonResponse(data)
            return JsonResponse({'status': 'success'})
        except Exception as e:
            messages.error(request, f"There was an error deleting the event: {e}")
            logger.error(f'Error deleting event with ID {event_id}: {e}')
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'fail', 'message': 'Invalid request method'})
