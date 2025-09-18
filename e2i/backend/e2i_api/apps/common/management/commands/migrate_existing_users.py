# e2i_api/apps/common/management/commands/migrate_existing_users.py

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import connection, transaction
import uuid
import secrets

User = get_user_model()


class Command(BaseCommand):
    help = 'Migrate existing user data to the new authentication system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without making changes'
        )
        parser.add_argument(
            '--default-password',
            type=str,
            default='TempPassword123!',
            help='Default password for migrated users'
        )
        parser.add_argument(
            '--generate-api-keys',
            action='store_true',
            help='Generate API keys for migrated users'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        default_password = options['default_password']
        generate_api_keys = options['generate_api_keys']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        # Analyze existing data
        existing_users = self.analyze_existing_data()
        
        if not existing_users:
            self.stdout.write('No existing user data found to migrate.')
            return

        self.stdout.write(f'Found {len(existing_users)} users to migrate:')
        for user_data in existing_users:
            self.stdout.write(f"  - {user_data['user_id']}: {user_data.get('files', 0)} files")

        if not dry_run:
            confirm = input('\nProceed with migration? (y/N): ')
            if confirm.lower() != 'y':
                self.stdout.write('Migration cancelled.')
                return

        # Perform migration
        migrated_count = 0
        with transaction.atomic():
            for user_data in existing_users:
                try:
                    if dry_run:
                        self.stdout.write(f"Would migrate user {user_data['user_id']}")
                    else:
                        user = self.migrate_user(user_data, default_password, generate_api_keys)
                        self.stdout.write(f"Migrated user: {user.username}")
                        migrated_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to migrate user {user_data['user_id']}: {e}")
                    )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully migrated {migrated_count} users')
            )
            
            self.stdout.write('\nPost-migration steps:')
            self.stdout.write('1. Inform users of their new credentials')
            self.stdout.write('2. Encourage users to change their passwords')
            self.stdout.write('3. Update any existing integrations to use new auth system')

    def analyze_existing_data(self):
        """Analyze existing user data from uploads table."""
        existing_users = []
        
        try:
            with connection.cursor() as cursor:
                # Get unique user IDs from uploads table
                cursor.execute("""
                    SELECT 
                        user_id,
                        COUNT(*) as file_count,
                        MIN(created_at) as first_upload,
                        MAX(created_at) as last_upload
                    FROM uploads 
                    WHERE user_id IS NOT NULL 
                    GROUP BY user_id
                    ORDER BY file_count DESC
                """)
                
                for row in cursor.fetchall():
                    user_id, file_count, first_upload, last_upload = row
                    
                    # Skip null UUID (anonymous users)
                    if str(user_id) == '00000000-0000-0000-0000-000000000000':
                        continue
                        
                    existing_users.append({
                        'user_id': user_id,
                        'files': file_count,
                        'first_upload': first_upload,
                        'last_upload': last_upload
                    })
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error analyzing existing data: {e}")
            )
            
        return existing_users

    def migrate_user(self, user_data, default_password, generate_api_keys):
        """Migrate a single user to the new system."""
        user_id = user_data['user_id']
        
        # Generate username from user ID
        username = f"user_{str(user_id).replace('-', '')[:8]}"
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            # Try with full UUID
            username = f"user_{str(user_id).replace('-', '')}"
            
            if User.objects.filter(username=username).exists():
                raise ValueError(f"Username {username} already exists")

        # Determine role (you might want to customize this logic)
        role = self.determine_user_role(user_data)
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=f"{username}@migrated.local",  # Placeholder email
            password=default_password,
            role=role
        )
        
        # Generate API key if requested
        if generate_api_keys:
            user.generate_api_key()
        
        # Update uploads table to maintain consistency
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE uploads SET user_id = %s WHERE user_id = %s",
                [user.id, user_id]
            )
            
        return user

    def determine_user_role(self, user_data):
        """Determine user role based on usage patterns."""
        # This is a simple heuristic - customize based on your needs
        file_count = user_data.get('files', 0)
        
        # Users with many uploads might be power users/admins
        if file_count > 50:
            return 'admin'
        else:
            return 'user'


# e2i_api/apps/common/management/commands/validate_migration.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import connection

User = get_user_model()


class Command(BaseCommand):
    help = 'Validate the user migration and check data consistency'

    def handle(self, *args, **options):
        self.stdout.write('Validating user migration...')
        
        # Check 1: User count
        user_count = User.objects.count()
        self.stdout.write(f'Total users in new system: {user_count}')
        
        # Check 2: Upload data consistency
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) 
                FROM uploads 
                WHERE user_id IS NOT NULL 
                AND user_id != '00000000-0000-0000-0000-000000000000'
            """)
            unique_upload_users = cursor.fetchone()[0]
            
        self.stdout.write(f'Unique users in uploads table: {unique_upload_users}')
        
        # Check 3: Orphaned uploads
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM uploads u
                LEFT JOIN auth_users au ON u.user_id = au.id
                WHERE u.user_id IS NOT NULL 
                AND u.user_id != '00000000-0000-0000-0000-000000000000'
                AND au.id IS NULL
            """)
            orphaned_uploads = cursor.fetchone()[0]
            
        if orphaned_uploads > 0:
            self.stdout.write(
                self.style.WARNING(f'Found {orphaned_uploads} orphaned uploads')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('No orphaned uploads found')
            )
        
        # Check 4: API key coverage
        users_with_api_keys = User.objects.filter(api_key__isnull=False).count()
        self.stdout.write(f'Users with API keys: {users_with_api_keys}/{user_count}')
        
        # Check 5: Role distribution
        admin_count = User.objects.filter(role='admin').count()
        user_count_role = User.objects.filter(role='user').count()
        
        self.stdout.write(f'Role distribution:')
        self.stdout.write(f'  - Admins: {admin_count}')
        self.stdout.write(f'  - Users: {user_count_role}')
        
        self.stdout.write(self.style.SUCCESS('Migration validation complete'))


# e2i_api/apps/common/management/commands/export_user_credentials.py

import csv
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Export user credentials to CSV file for distribution'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='user_credentials.csv',
            help='Output CSV file path'
        )
        parser.add_argument(
            '--include-api-keys',
            action='store_true',
            help='Include API keys in export (security risk!)'
        )

    def handle(self, *args, **options):
        output_file = options['output']
        include_api_keys = options['include_api_keys']

        if include_api_keys:
            self.stdout.write(
                self.style.WARNING(
                    'WARNING: Including API keys in export. '
                    'Ensure the output file is handled securely!'
                )
            )

        users = User.objects.filter(is_active=True).order_by('username')
        
        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = ['username', 'email', 'role', 'created_at']
            if include_api_keys:
                fieldnames.append('api_key')
                
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for user in users:
                row = {
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'created_at': user.created_at.isoformat()
                }
                
                if include_api_keys and user.api_key:
                    row['api_key'] = user.api_key
                    
                writer.writerow(row)

        self.stdout.write(
            self.style.SUCCESS(f'Exported {users.count()} users to {output_file}')
        )
        
        if include_api_keys:
            self.stdout.write(
                self.style.WARNING(
                    f'SECURITY: {output_file} contains API keys. '
                    'Distribute securely and delete when no longer needed.'
                )
            )


# e2i_api/apps/common/management/commands/cleanup_old_sessions.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from ..models import UserSession


class Command(BaseCommand):
    help = 'Clean up expired user sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete sessions older than N days (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without making changes'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Find sessions to delete
        old_sessions = UserSession.objects.filter(
            created_at__lt=cutoff_date
        )
        
        expired_sessions = UserSession.objects.filter(
            expires_at__lt=timezone.now(),
            is_active=False
        )
        
        total_to_delete = old_sessions.count() + expired_sessions.count()
        
        if dry_run:
            self.stdout.write(f'Would delete {total_to_delete} sessions:')
            self.stdout.write(f'  - {old_sessions.count()} older than {days} days')
            self.stdout.write(f'  - {expired_sessions.count()} expired and inactive')
        else:
            deleted_old = old_sessions.delete()[0]
            deleted_expired = expired_sessions.delete()[0]
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Deleted {deleted_old + deleted_expired} sessions'
                )
            )


# Data migration script for Django migrations
def migrate_existing_user_data(apps, schema_editor):
    """
    Data migration function to be used in Django migrations.
    This can be included in a migration file if needed.
    """
    # Get model classes
    User = apps.get_model('common', 'User')
    
    # This would be customized based on your existing data structure
    # For now, it's just a placeholder
    
    print("Data migration placeholder - customize based on your existing data")


# e2i_api/apps/common/migrations/0002_migrate_data.py (example)
"""
Example data migration - uncomment and customize as needed

from django.db import migrations

def migrate_user_data(apps, schema_editor):
    # Custom migration logic here
    pass

def reverse_migrate_user_data(apps, schema_editor):
    # Reverse migration logic here
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            migrate_user_data,
            reverse_migrate_user_data
        ),
    ]
"""