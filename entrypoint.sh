#!/bin/sh

echo "Collect static files"
python manage.py collectstatic --noinput --clear

echo "Apply database migrations"
python manage.py migrate

echo "Starting server"
exec "$@"
