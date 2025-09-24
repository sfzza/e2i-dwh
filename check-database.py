#!/usr/bin/env python3
"""
Database connection checker for Railway deployment
Run this script to diagnose database connection issues
"""

import os
import sys

def check_environment():
    """Check environment variables"""
    print("🔍 Checking Environment Variables...")
    
    # Check DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        print("✅ DATABASE_URL is set")
        print(f"   Database URL: {database_url[:20]}...")
    else:
        print("❌ DATABASE_URL is NOT set")
        print("   Solution: Add PostgreSQL addon to Railway")
    
    # Check other important variables
    django_secret = os.getenv("DJANGO_SECRET_KEY")
    if django_secret:
        print("✅ DJANGO_SECRET_KEY is set")
    else:
        print("❌ DJANGO_SECRET_KEY is NOT set")
        print("   Solution: Set DJANGO_SECRET_KEY environment variable")
    
    django_debug = os.getenv("DJANGO_DEBUG")
    if django_debug:
        print(f"✅ DJANGO_DEBUG is set to: {django_debug}")
    else:
        print("❌ DJANGO_DEBUG is NOT set")
        print("   Solution: Set DJANGO_DEBUG=False for production")
    
    django_hosts = os.getenv("DJANGO_ALLOWED_HOSTS")
    if django_hosts:
        print(f"✅ DJANGO_ALLOWED_HOSTS is set to: {django_hosts}")
    else:
        print("❌ DJANGO_ALLOWED_HOSTS is NOT set")
        print("   Solution: Set DJANGO_ALLOWED_HOSTS to your Railway domain")

def check_database_connection():
    """Check database connection"""
    print("\n🔍 Checking Database Connection...")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ Cannot check database connection - DATABASE_URL not set")
        return False
    
    try:
        import dj_database_url
        import psycopg2
        
        # Parse the database URL
        db_config = dj_database_url.parse(database_url)
        print(f"✅ Database URL parsed successfully")
        print(f"   Host: {db_config.get('HOST', 'unknown')}")
        print(f"   Database: {db_config.get('NAME', 'unknown')}")
        print(f"   User: {db_config.get('USER', 'unknown')}")
        
        # Try to connect
        print("   Attempting connection...")
        conn = psycopg2.connect(
            host=db_config['HOST'],
            database=db_config['NAME'],
            user=db_config['USER'],
            password=db_config['PASSWORD'],
            port=db_config.get('PORT', 5432)
        )
        conn.close()
        print("✅ Database connection successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Solution: pip install dj-database-url psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("   Solution: Check if PostgreSQL addon is properly configured")
        return False

def check_django_settings():
    """Check Django settings"""
    print("\n🔍 Checking Django Settings...")
    
    try:
        import os
        import sys
        
        # Add the Django project to Python path
        sys.path.insert(0, '/app/e2i/backend')
        
        # Set Django settings
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e2i_api.settings')
        
        import django
        django.setup()
        
        from django.conf import settings
        
        print("✅ Django settings loaded successfully")
        
        # Check database configuration
        db_config = settings.DATABASES['default']
        print(f"   Database Engine: {db_config['ENGINE']}")
        print(f"   Database Host: {db_config['HOST']}")
        print(f"   Database Name: {db_config['NAME']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Django settings error: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Railway Database Connection Checker")
    print("=" * 50)
    
    # Check environment variables
    check_environment()
    
    # Check database connection
    db_ok = check_database_connection()
    
    # Check Django settings
    django_ok = check_django_settings()
    
    print("\n" + "=" * 50)
    print("📋 Summary:")
    
    if db_ok and django_ok:
        print("✅ All checks passed! Your database should work correctly.")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("\n🔧 Quick Fixes:")
        print("1. Add PostgreSQL addon to Railway")
        print("2. Set environment variables in Railway dashboard")
        print("3. Redeploy your application")

if __name__ == "__main__":
    main()
