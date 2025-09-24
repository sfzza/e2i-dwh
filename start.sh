#!/bin/bash

# Railway start script for E2I Data Warehouse
# This script will start the main Django application as the primary service

set -e

echo "🚀 Starting E2I Data Warehouse on Railway..."

# Set environment variables for Railway
export DJANGO_SETTINGS_MODULE=e2i_api.settings
export PYTHONPATH=/app
export DJANGO_DEBUG=False

# Debug Railway environment
echo "🔍 Railway Environment Debug:"
echo "PORT: $PORT"
echo "RAILWAY_PUBLIC_DOMAIN: $RAILWAY_PUBLIC_DOMAIN"
echo "RAILWAY_STATIC_URL: $RAILWAY_STATIC_URL"

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p /app/exports
mkdir -p /app/logs
mkdir -p /app/e2i/backend/logs
mkdir -p /app/e2i/backend/static
mkdir -p /app/e2i/backend/staticfiles

# Navigate to the Django backend directory
cd /app/e2i/backend

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "🔍 Checking database configuration..."
python /app/check-database.py

echo "🗄️ Running database migrations..."
python manage.py migrate

echo "🔧 Building and collecting static files..."

# Build React frontend if package.json exists
if [ -f "e2i/frontend/package.json" ]; then
    echo "📦 Building React frontend..."
    cd e2i/frontend
    npm run build
    cd ../..
    
    # Copy React build to Django static files
    echo "📋 Copying React build to Django static files..."
    mkdir -p e2i/backend/e2i_api/staticfiles
    cp -r e2i/frontend/build/* e2i/backend/e2i_api/staticfiles/
    echo "✅ React frontend integrated with Django"
else
    echo "⚠️  React frontend package.json not found, skipping build"
fi

echo "🔧 Collecting Django static files..."
python manage.py collectstatic --noinput

echo "🌐 Starting Django server..."
echo "📡 Using PORT: $PORT"

# Use production server for Railway
if command -v gunicorn &> /dev/null; then
    echo "🚀 Starting with Gunicorn (Production)"
    gunicorn --bind 0.0.0.0:$PORT --workers 3 e2i_api.wsgi:application
else
    echo "🚀 Starting with Django development server"
    python manage.py runserver 0.0.0.0:$PORT
fi

echo "✅ E2I Data Warehouse started successfully!"
