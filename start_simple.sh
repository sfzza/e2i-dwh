#!/bin/bash

echo "🚀 Starting E2I Data Warehouse on Railway..."

# Use Railway's PORT
PORT=${PORT:-3000}
echo "📡 Using PORT: $PORT"

# Run migrations
echo "🗄️ Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "🔧 Collecting Django static files..."
python manage.py collectstatic --noinput --clear

# Start Gunicorn directly - no React build
echo "🚀 Starting Gunicorn server..."
exec gunicorn e2i.backend.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
