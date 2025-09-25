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
cd /app/e2i/backend
python manage.py migrate
cd /app

echo "🔧 Building and collecting static files..."

# Quick health check test
echo "🔍 Testing Django startup..."
cd /app/e2i/backend
python manage.py check --deploy || {
    echo "❌ Django check failed, but continuing with deployment"
}
cd /app

# Build React frontend if package.json exists
if [ -f "/app/e2i/frontend/package.json" ]; then
    echo "📦 Building React frontend..."
    cd /app/e2i/frontend
    
           # Always reinstall dependencies to ensure react-scripts is available
           echo "📥 Installing React dependencies..."
           npm install || {
               echo "❌ Failed to install React dependencies, trying clean install..."
               rm -rf node_modules package-lock.json
               npm install || {
                   echo "❌ Clean install also failed, trying global react-scripts..."
                   npm install -g react-scripts || echo "⚠️  Global install also failed, continuing without React build"
               }
           }
           
           # Verify react-scripts is available
           if ! command -v react-scripts &> /dev/null && [ ! -f "node_modules/.bin/react-scripts" ]; then
               echo "❌ react-scripts not found, installing globally..."
               npm install -g react-scripts || echo "⚠️  Global install failed"
           fi
           
           # Fix npm vulnerabilities
           echo "🔧 Fixing npm vulnerabilities..."
           npm audit fix --force || echo "⚠️  Some vulnerabilities remain, but continuing with build"
    
    # Build React app
    echo "🔨 Building React app..."
    
    # Try different ways to run react-scripts
    if [ -f "node_modules/.bin/react-scripts" ]; then
        echo "📦 Using local react-scripts..."
        ./node_modules/.bin/react-scripts build || {
            echo "❌ Local react-scripts build failed, trying npm run build..."
            npm run build || echo "❌ npm run build also failed"
        }
    elif command -v react-scripts &> /dev/null; then
        echo "📦 Using global react-scripts..."
        react-scripts build || echo "❌ Global react-scripts build failed"
    else
        echo "❌ No react-scripts found, trying npm run build..."
        npm run build || {
            echo "❌ React build failed, continuing without React frontend"
            echo "📝 Django will serve fallback template instead"
        }
    fi
    
    # Return to app root
    cd /app
    
    # Copy React build to Django static files (only if build directory exists)
    if [ -d "/app/e2i/frontend/build" ]; then
        echo "📋 Copying React build to Django static files..."
        mkdir -p /app/e2i/backend/e2i_api/staticfiles
        cp -r /app/e2i/frontend/build/* /app/e2i/backend/e2i_api/staticfiles/
        
        # Verify the copy worked
        echo "🔍 Verifying React files were copied..."
        if [ -f "/app/e2i/backend/e2i_api/staticfiles/index.html" ]; then
            echo "✅ React index.html found"
            ls -la /app/e2i/backend/e2i_api/staticfiles/ | head -10
            echo "✅ React frontend integrated with Django"
        else
            echo "❌ React index.html NOT found"
            echo "📁 Contents of staticfiles directory:"
            ls -la /app/e2i/backend/e2i_api/staticfiles/ || echo "Directory not found"
        fi
    else
        echo "⚠️  React build directory not found, skipping React frontend integration"
        echo "📝 Django will serve fallback template instead"
    fi
else
    echo "⚠️  React frontend package.json not found at /app/e2i/frontend/package.json"
    echo "📁 Available files in /app/e2i/:"
    ls -la /app/e2i/ || echo "e2i directory not found"
    echo "📁 Available files in /app/:"
    ls -la /app/ || echo "app directory not found"
fi

echo "🔧 Collecting Django static files..."
cd /app/e2i/backend
python manage.py collectstatic --noinput
cd /app

echo "🌐 Starting Django server..."
echo "📡 Using PORT: $PORT"

# Use production server for Railway
cd /app/e2i/backend
if command -v gunicorn &> /dev/null; then
    echo "🚀 Starting with Gunicorn (Production)"
    gunicorn e2i_api.wsgi:application \
        --bind 0.0.0.0:$PORT \
        --workers 2 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile -
else
    echo "🚀 Starting with Django development server"
    python manage.py runserver 0.0.0.0:$PORT
fi

echo "✅ E2I Data Warehouse started successfully!"
