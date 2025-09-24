#!/usr/bin/env python3
"""
Debug script to test Railway connection
"""
import os
import sys
import time
import subprocess
import requests

def test_internal_connection():
    """Test if the app responds internally"""
    port = os.getenv('PORT', '3000')
    url = f"http://localhost:{port}/health/"
    
    print(f"🔍 Testing internal connection to {url}")
    
    try:
        response = requests.get(url, timeout=5)
        print(f"✅ Internal connection successful!")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Internal connection failed: {e}")
        return False

def check_environment():
    """Check Railway environment variables"""
    print("🔍 Railway Environment Variables:")
    print(f"   PORT: {os.getenv('PORT', 'NOT SET')}")
    print(f"   RAILWAY_PUBLIC_DOMAIN: {os.getenv('RAILWAY_PUBLIC_DOMAIN', 'NOT SET')}")
    print(f"   RAILWAY_STATIC_URL: {os.getenv('RAILWAY_STATIC_URL', 'NOT SET')}")
    print(f"   PWD: {os.getenv('PWD', 'NOT SET')}")

def check_processes():
    """Check if Gunicorn is running"""
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'gunicorn' in result.stdout:
            print("✅ Gunicorn process found")
            for line in result.stdout.split('\n'):
                if 'gunicorn' in line:
                    print(f"   {line}")
        else:
            print("❌ No Gunicorn process found")
    except Exception as e:
        print(f"❌ Error checking processes: {e}")

if __name__ == "__main__":
    print("🚀 Railway Connection Debug Tool")
    print("=" * 50)
    
    check_environment()
    print()
    
    check_processes()
    print()
    
    # Wait a bit for the app to start
    print("⏳ Waiting 5 seconds for app to start...")
    time.sleep(5)
    
    test_internal_connection()
