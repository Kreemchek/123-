#!/bin/sh

# Миграции
python manage.py migrate

# Сбор статики с повышенной детализацией
python manage.py collectstatic --noinput --verbosity 2

# Запуск сервера
exec "$@"