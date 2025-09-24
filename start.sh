#!/bin/bash

# Railway start script for E2I Data Warehouse
# This script will start the main Django application as the primary service

set -e

echo "🚀 Starting E2I Data Warehouse on Railway..."

# Set environment variables for Railway
export DJANGO_SETTINGS_MODULE=e2i_api.settings
export PYTHONPATH=/app
export DJANGO_DEBUG=False

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

echo "🔧 Collecting static files..."
python manage.py collectstatic --noinput

echo "🌐 Starting Django development server..."
python manage.py runserver 0.0.0.0:$PORT

echo "✅ E2I Data Warehouse started successfully!"
