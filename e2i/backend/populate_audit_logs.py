#!/usr/bin/env python3
"""
Script to populate sample audit logs for testing the Recent Activity functionality.
This script creates various types of audit log entries to demonstrate the activity feed.
"""

import os
import sys
import django
from datetime import datetime, timedelta
import random

# Add the Django project to the Python path
sys.path.append('/Users/dominicsu/Downloads/datawarehouse/e2i/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e2i_api.settings')
django.setup()

from e2i_api.apps.common.models import AuditLog, User
from django.utils import timezone

def create_sample_audit_logs():
    """Create sample audit log entries for testing."""
    
    # Get existing users
    users = User.objects.all()
    if not users.exists():
        print("No users found. Please create users first.")
        return
    
    # Sample activities to create
    activities = [
        {'action': 'login', 'resource': 'authentication', 'status': 'success'},
        {'action': 'logout', 'resource': 'authentication', 'status': 'success'},
        {'action': 'upload', 'resource': 'file: sample_data.csv', 'status': 'success'},
        {'action': 'upload', 'resource': 'file: user_data.xlsx', 'status': 'success'},
        {'action': 'template_create', 'resource': 'template: User Data Template', 'status': 'success'},
        {'action': 'template_edit', 'resource': 'template: Sales Data Template', 'status': 'success'},
        {'action': 'api_key_generate', 'resource': 'user_profile', 'status': 'success'},
        {'action': 'data_ingestion', 'resource': 'pipeline: ETL Process', 'status': 'success'},
        {'action': 'data_validation', 'resource': 'file: validation_report.csv', 'status': 'success'},
        {'action': 'system_access', 'resource': 'dashboard', 'status': 'success'},
        {'action': 'view', 'resource': 'upload_history', 'status': 'success'},
        {'action': 'export', 'resource': 'data_export.csv', 'status': 'success'},
    ]
    
    # Create audit logs for the last 7 days
    now = timezone.now()
    
    for i in range(50):  # Create 50 sample entries
        # Random time within the last 7 days
        random_hours = random.randint(0, 168)  # 7 days * 24 hours
        timestamp = now - timedelta(hours=random_hours)
        
        # Random user
        user = random.choice(users)
        
        # Random activity
        activity = random.choice(activities)
        
        # Create audit log entry
        AuditLog.objects.create(
            user=user,
            username=user.username,
            action=activity['action'],
            resource=activity['resource'],
            status=activity['status'],
            ip_address=f"192.168.1.{random.randint(1, 254)}",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            timestamp=timestamp,
            details={
                'sample_data': True,
                'created_by_script': True,
                'random_id': random.randint(1000, 9999)
            }
        )
    
    print(f"Created 50 sample audit log entries for {users.count()} users.")
    print("Recent Activity should now show data in the admin dashboard.")

if __name__ == "__main__":
    create_sample_audit_logs()
