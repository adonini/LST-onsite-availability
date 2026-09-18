#!/bin/sh

set -eu

CONTAINER_NAME="${CONTAINER_NAME:-cal_app}"

docker exec "$CONTAINER_NAME" /bin/bash -lc 'cd /code && python manage.py send_orm_staff_email "$@"' bash "$@"
