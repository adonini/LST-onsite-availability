#!/bin/sh

set -eu

CONTAINER_NAME="${CONTAINER_NAME:-lst-calendar-prod-app-1}"

docker exec "$CONTAINER_NAME" /bin/bash -lc 'cd /code && python manage.py send_orm_staff_email "$@"' bash "$@"
