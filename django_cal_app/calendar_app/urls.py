from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.calendar_view, name='calendar'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('all_events/', views.all_events, name='all_events'),
    path('add_event/', views.add_event, name='add_event'),
    path('event/<int:event_id>/', views.event_details, name='event_details'),
    #path('update_event/', views.update_event, name='update_event'),
    path('remove_event/', views.remove_event, name='remove_event'),
]
