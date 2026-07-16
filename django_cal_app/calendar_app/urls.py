from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.calendar_view, name='calendar'),
    path('login/', views.CustomLoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('first-login-change-password/', views.FirstLoginPasswordChangeView.as_view(), name='first_login_change_password'),
    path('all_events/', views.all_events, name='all_events'),
    path('add_event/', views.add_event, name='add_event'),
    path('event/<int:event_id>/', views.event_details, name='event_details'),
    path('remove_event/', views.remove_event, name='remove_event'),
    #path('update_event/', views.update_event, name='update_event'),
    #path('assign_users/', views.assign_users, name='assign_users'),
    path('all_activities/', views.all_activities, name='all_activities'),
    path('add_activity/', views.add_activity, name='add_activity'),
    path('activity/<int:activity_id>/', views.activity_details, name='activity_details'),
    path('remove_activity/', views.remove_activity, name='remove_activity'),
    path('activity/<int:activity_id>/assignees/', views.set_activity_assignees, name='set_activity_assignees'),
    path('users/search/', views.search_users, name='search_users'),
    path('magic-second-floor/', views.magic_second_floor_view, name='magic_second_floor'),
    path('magic-second-floor/events/', views.magic_second_floor_events, name='magic_second_floor_events'),
    path('magic-second-floor/request/', views.create_magic_second_floor_request, name='create_magic_second_floor_request'),
    path('magic-second-floor/request/<int:request_id>/', views.magic_second_floor_request_details, name='magic_second_floor_request_details'),
    path('magic-second-floor/pending/', views.magic_second_floor_pending_requests, name='magic_second_floor_pending'),
    path('magic-second-floor/request/<int:request_id>/approve/', views.approve_magic_second_floor_request, name='approve_magic_second_floor_request'),
    path('magic-second-floor/request/<int:request_id>/reject/', views.reject_magic_second_floor_request, name='reject_magic_second_floor_request'),
]
