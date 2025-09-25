#!/bin/bash

echo "🚀 Starting E2I Data Warehouse on Railway..."

# Use Railway's PORT
PORT=${PORT:-3000}
echo "📡 Using PORT: $PORT"

# Add Python path
export PYTHONPATH=/app:$PYTHONPATH

# Change to the backend directory
cd /app/e2i/backend

# Run migrations
echo "🗄️ Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "🔧 Collecting Django static files..."
python manage.py collectstatic --noinput --clear

# Start Gunicorn from the correct directory
echo "🚀 Starting Gunicorn server..."
exec gunicorn e2i_api.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --chdir /app/e2i/backend