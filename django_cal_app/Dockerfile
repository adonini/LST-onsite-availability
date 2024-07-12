FROM python:3.10

# set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# set work directory
WORKDIR /code

# install dependencies
COPY requierements-django.txt /code/
RUN pip install -r requierements-django.txt

# copy project
COPY . /code/

#EXPOSE 8000

#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]