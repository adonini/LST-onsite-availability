FROM python:3.10

# set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# set work directory
WORKDIR /code

# install dependencies
COPY requirements_django.txt /code/
RUN pip install -r requirements_django.txt

# create logs directory and log file
RUN mkdir -p /logs
RUN touch /logs/django_cal.log
RUN chmod -R 755 /logs

# copy project
COPY . /code/

RUN python manage.py collectstatic --noinput

# ensure the entrypoint script has execute permission
RUN chmod +x /code/entrypoint.sh

#EXPOSE 8000

#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]