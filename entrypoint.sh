#!/bin/sh

# Exit on error
set -e

echo "Waiting for postgres..."
while ! nc -z $DATABASE_HOST $DATABASE_PORT; do
  sleep 0.1
done
echo "PostgreSQL started"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Initializing admin user..."
python manage.py init_admin

echo "Starting Gunicorn..."
exec gunicorn api.wsgi:application --bind 0.0.0.0:8081 --log-level debug --reload
