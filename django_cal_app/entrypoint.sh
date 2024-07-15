#!/bin/bash

# Collect static files
#echo "Collect static files"
#python manage.py collectstatic --noinput

# Apply database migrations
echo "Apply database migrations"
python manage.py migrate

# create superuser from env variables, if it doesn't exists
echo "Checking and creating superuser if not exists"
python manage.py create_superuser

# Start server
echo "Starting server"
#python manage.py runserver 0.0.0.0:8000 # dev server
# Start the Gunicorn server
exec gunicorn django_cal_app.wsgi:application --bind 0.0.0.0:8000 --workers 3