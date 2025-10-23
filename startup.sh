#!/usr/bin/env bash
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

# sobe o servidor
gunicorn biblox.wsgi --bind=0.0.0.0 --timeout 600
